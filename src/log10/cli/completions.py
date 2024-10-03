import json
import time
from pathlib import Path

import click
import pandas as pd
import rich
from rich.console import Console
from rich.table import Table

from log10._httpx_utils import _get_time_diff, _try_get
from log10.cli_utils import generate_markdown_report, generate_results_table
from log10.completions.completions import (
    Completions,
    _check_model_support,
    _compare,
    _get_completion,
    _get_completions_url,
)
from log10.llm import Log10Config
from log10.prompt_analyzer import PromptAnalyzer, convert_suggestion_to_markdown, display_prompt_analyzer_suggestions


_log10_config = Log10Config()


def _render_completions_table(completions_data):
    data_for_table = []
    for completion in completions_data:
        prompt, response = "", ""
        if completion.get("kind") == "completion":
            prompt = completion.get("request", {}).get("prompt", "")
            response_choices = completion.get("response", {}).get("choices", [])
            if response_choices:
                response = response_choices[0].get("text", "")
        elif completion.get("kind") == "chat":
            request_messages = completion.get("request", {}).get("messages", [])
            prompt = request_messages[0].get("content", "") if request_messages else ""

            response_choices = completion.get("response", {}).get("choices", [])
            if response_choices:
                # Handle 'message' and 'function_call' within the first choice safely
                first_choice = response_choices[0]
                if "message" in first_choice:
                    message = first_choice["message"]
                    response = (
                        message.get("content")
                        or (
                            message.get("tool_calls")[-1].get("function", {}).get("arguments", "")
                            if message.get("tool_calls")
                            else ""
                        )
                        or ""
                    )
                elif "function_call" in first_choice:
                    response = json.dumps(first_choice.get("function_call", {}))
        else:
            rich.print(f"Unknown completion kind: {completion['kind']} for id: {completion['id']}")

        data_for_table.append(
            {
                "id": completion["id"],
                "status": "success" if completion["status"] == "finished" else completion["status"],
                "created_at": _get_time_diff(completion["created_at"]),
                "prompt": prompt,
                "completion": response,
                "tags": [t["name"] for t in completion["tagResolved"]],
            }
        )
    # render data_for_table with rich table
    table = Table(show_header=True, header_style="bold magenta")

    table.add_column("ID", style="dim")
    table.add_column("Status")
    table.add_column("Created At")
    table.add_column("Prompt", overflow="fold")
    table.add_column("Completion", overflow="fold")
    table.add_column("Tags", justify="right")

    max_len = 40
    for item in data_for_table:
        tags = ", ".join(item["tags"]) if item["tags"] else ""
        if isinstance(item["prompt"], list):
            item["prompt"] = " ".join(item["prompt"])
        short_prompt = item["prompt"][:max_len] + "..." if len(item["prompt"]) > max_len else item["prompt"]
        completion = item.get("completion", "")
        short_completion = completion[:max_len] + "..." if len(completion) > max_len else completion
        table.add_row(item["id"], item["status"], item["created_at"], short_prompt, short_completion, tags)

    console = Console()
    console.print(table)


def _render_comparison_table(model_response_raw_data):
    rich.print(f"completion_id: {model_response_raw_data['completion_id']}")
    rich.print(f"tags: {model_response_raw_data['tags']}")
    rich.print("original_request:")
    rich.print_json(json.dumps(model_response_raw_data["original_request"], indent=4))

    table = rich.table.Table(show_header=True, header_style="bold magenta", box=rich.box.ROUNDED, show_lines=True)
    table.add_column("Model")
    table.add_column("Content")
    table.add_column("Total Token Usage (Input/Output)")
    table.add_column("Duration (ms)")

    for model, data in model_response_raw_data.items():
        # only display model data
        if model not in ["completion_id", "original_request", "tags"]:
            usage = data.get("usage", {})
            formatted_usage = (
                f"{usage['total_tokens']} ({usage['prompt_tokens']}/{usage['completion_tokens']})" if usage else "N/A"
            )
            table.add_row(model, data["content"], formatted_usage, str(data["duration"]))
    rich.print(table)


def _create_dataframe_from_comparison_data(model_response_raw_data):
    completion_id = model_response_raw_data["completion_id"]
    tags = model_response_raw_data["tags"]
    original_request = model_response_raw_data["original_request"]
    rows = []
    for model, model_data in model_response_raw_data.items():
        # only display model data
        if model not in ["completion_id", "original_request", "tags"]:
            content = model_data.get("content", "")
            usage = model_data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            duration = model_data.get("duration", 0)
            prompt_messages = json.dumps(original_request.get("messages", []))
            rows.append(
                [
                    completion_id,
                    tags,
                    prompt_messages,
                    model,
                    content,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    duration,
                ]
            )

    df = pd.DataFrame(
        rows,
        columns=[
            "completion_id",
            "tags",
            "prompt_messages",
            "model",
            "content",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "duration_ms",
        ],
    )

    return df


@click.command()
@click.option("--limit", default=25, help="Specify the maximum number of completions to retrieve.")
@click.option("--offset", default=0, help="Set the starting point (offset) from where to begin fetching completions.")
@click.option(
    "--timeout", default=10, help="Set the maximum time (in seconds) allowed for the HTTP request to complete."
)
@click.option("--tags", default="", help="Filter completions by specific tags. Separate multiple tags with commas.")
@click.option(
    "--from",
    "from_date",
    type=click.DateTime(),
    help="Define the start date for fetching completions (inclusive). Use the format: YYYY-MM-DD.",
)
@click.option(
    "--to",
    "to_date",
    type=click.DateTime(),
    help="Set the end date for fetching completions (inclusive). Use the format: YYYY-MM-DD.",
)
def list_completions(limit, offset, timeout, tags, from_date, to_date):
    """
    List completions
    """
    base_url = _log10_config.url
    org_id = _log10_config.org_id

    url = _get_completions_url(limit, offset, tags, from_date, to_date, base_url, org_id)
    # Fetch completions
    res = _try_get(url, timeout)

    completions = res.json().get("data", [])

    _render_completions_table(completions)


@click.command()
@click.option("--id", prompt="Enter completion id", help="Completion ID")
def get_completion(id):
    """
    Get a completion by id
    """
    res = _get_completion(id)
    rich.print_json(json.dumps(res.json()["data"], indent=4))


@click.command()
@click.option("--limit", default=50, help="Specify the maximum number of completions to retrieve.")
@click.option("--offset", default=0, help="Set the starting point (offset) from where to begin fetching completions.")
@click.option(
    "--timeout", default=10, help="Set the maximum time (in seconds) allowed for the HTTP request to complete."
)
@click.option("--tags", default="", help="Filter completions by specific tags. Separate multiple tags with commas.")
@click.option(
    "--from",
    "from_date",
    type=click.DateTime(),
    help="Define the start date for fetching completions (inclusive). Use the format: YYYY-MM-DD.",
)
@click.option(
    "--to",
    "to_date",
    type=click.DateTime(),
    help="Set the end date for fetching completions (inclusive). Use the format: YYYY-MM-DD.",
)
@click.option(
    "--file",
    "-f",
    type=click.Path(dir_okay=False),
    default="completions.jsonl",
    help="Specify the filename and path for the output file. Only .jsonl extension is supported.",
)
def download_completions(limit, offset, timeout, tags, from_date, to_date, file):
    """
    Download completions to a jsonl file
    """
    input_offset = int(offset)
    input_limit = int(limit)
    fetched_total = 0
    batch_size = 10

    if file:
        path = Path(file)
        if path.exists():
            rich.print(f'Warning: The file "{file}" already exists and will be overwritten.')

        ext_name = path.suffix.lower()
        if ext_name not in [".jsonl"]:
            raise click.UsageError(f"Only .jsonl extension is supported for the output file. Got: {ext_name}")

    console = Console()
    track_limit = input_limit if input_limit < batch_size else batch_size
    track_offset = input_offset
    try:
        with console.status("[bold green]Downloading completions...", spinner="bouncingBar") as status:
            with open(file, "w") as output_file:
                start_time = time.time()
                while True and track_limit > 0:
                    new_data = Completions()._get_completions(
                        offset=track_offset,
                        limit=track_limit,
                        timeout=timeout,
                        tag_names=tags,
                        from_date=from_date,
                        to_date=to_date,
                    )

                    new_data_size = len(new_data)
                    fetched_total += new_data_size

                    for completion in new_data:
                        res = _get_completion(completion["id"])
                        if res.status_code != 200:
                            rich.print(f"Error fetching completion {completion['id']}")
                            continue
                        if not res.json().get("data", {}):
                            rich.print(f"Completion {completion['id']} is empty")
                            continue
                        full_completion_data = res.json()["data"]
                        output_file.write(json.dumps(full_completion_data) + "\n")

                    elapsed_time = time.time() - start_time
                    rate = fetched_total / elapsed_time if elapsed_time > 0 else 0
                    status.update(
                        f"[bold green]Downloading completions...\n"
                        f"📥 Downloaded {fetched_total} | "
                        f"⏱️ {elapsed_time:.1f}s | "
                        f"⚡ {rate:.1f}/s"
                    )

                    if new_data_size == 0 or new_data_size < track_limit:
                        break

                    track_offset += new_data_size
                    track_limit = (
                        input_limit - fetched_total if input_limit - fetched_total < batch_size else batch_size
                    )
    except Exception as e:
        rich.print(f"Error fetching completions {e}")
        if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
            rich.print(e.response.json()["error"])
        return

    rich.print(
        f"[bold green]📥 Downloaded {fetched_total} | "
        f"⏱️ {elapsed_time:.1f}s. | "
        f"⚡ {rate:.2f}/s\n"
        f"💾 Saved to {file}"
    )


@click.command()
@click.option(
    "--ids",
    default="",
    help="Log10 completion IDs. Provide a comma-separated list of completion IDs or a "
    "path to a JSON file containing the list of IDs.",
)
@click.option("--tags", default="", help="Filter completions by specific tags. Separate multiple tags with commas.")
@click.option("--limit", help="Specify the maximum number of completions to retrieve filtered by tags.")
@click.option(
    "--offset", help="Set the starting point (offset) from where to begin fetching completions filtered by tags."
)
@click.option("--models", default="", help="Comma separated list of models to compare")
@click.option("--temperature", default=0.2, help="Temperature")
@click.option("--max_tokens", default=512, help="Max tokens")
@click.option("--top_p", default=1.0, help="Top p")
@click.option("--analyze_prompt", is_flag=True, help="Run prompt analyzer on the messages.")
@click.option(
    "--file",
    "-f",
    type=click.Path(dir_okay=False),
    help="Specify the filename to save the results. Specify the output file using `.md` for a markdown report, "
    "`.csv` for comma-separated values, or `.jsonl` for JSON Lines format. Only .md, .csv, and .jsonl extensions "
    "are supported.",
)
def benchmark_models(
    ids,
    tags,
    limit,
    offset,
    models,
    temperature,
    max_tokens,
    top_p,
    file,
    analyze_prompt,
):
    """
    Compare completions using different models and generate report
    """
    if ids and tags:
        raise click.UsageError("--ids and --tags cannot be set together.")
    if (limit or offset) and not tags:
        raise click.UsageError("--limit and --offset can only be used with --tags.")
    if tags:
        if not limit:
            limit = 5
        if not offset:
            offset = 0

    if not models:
        raise click.UsageError("--models must be set to compare.")
    else:
        for model in [m for m in models.split(",") if m]:
            if not _check_model_support(model):
                raise click.UsageError(f"Model {model} is not supported.")

    if file:
        path = Path(file)
        ext_name = path.suffix.lower()
        if ext_name not in [".md", ".csv", ".jsonl"]:
            raise click.UsageError(
                f"Only .md, .csv, and .jsonl extensions are supported for the output file. Got: {ext_name}"
            )

    # get completions ids
    completion_ids = []
    if ids:
        ids_path = Path(ids)
        if ids_path.is_file():
            if ids_path.suffix.lower() != ".json":
                raise click.UsageError(
                    f"Only json format is supported for the IDs file. Got {ids_path.suffix.lower()}"
                )
            with open(ids_path, "r") as f:
                completion_ids = json.load(f)
        else:
            completion_ids = [id for id in ids.split(",") if id]
    elif tags:
        base_url = _log10_config.url
        org_id = _log10_config.org_id
        url = _get_completions_url(limit, offset, tags, None, None, base_url, org_id)
        res = _try_get(url)
        completions = res.json().get("data", [])
        completion_ids = [completion.get("id") for completion in completions if completion.get("id") is not None]
        if not completion_ids:
            SystemExit(f"No completions found for tags: {tags}")

    compare_models = [m for m in models.split(",") if m]

    data = []
    skipped_completion_ids = []
    for id in completion_ids:
        rich.print(f"Processing completion {id}")
        try:
            # get completion from id
            res = _get_completion(id)
            if res.status_code != 200:
                rich.print(f"Error fetching completion {id}")
                skipped_completion_ids.append(id)
                continue

            completion_data = res.json().get("data", {})

            # skip completion if status is not finished or kind is not chat
            if completion_data.get("status") != "finished" or completion_data.get("kind") != "chat":
                rich.print(f"Skip completion {id}. Status is not finished or kind is not chat.")
                skipped_completion_ids.append(id)
                continue

            # get tags
            tags = [t.get("name") for t in completion_data.get("tagResolved", [])]

            original_model_request = completion_data.get("request", {})
            original_model_response = completion_data.get("response", {})
            original_model = original_model_response.get("model", "")
            benchmark_data = {
                "completion_id": id,
                "original_request": original_model_request,
                f"{original_model} (original model)": {
                    "content": original_model_response.get("choices", [{}])[0].get("message", {}).get("content", ""),
                    "usage": original_model_response.get("usage", {}),
                    "duration": completion_data.get("duration", 0),
                },
                "tags": tags,
            }
            if messages := original_model_request.get("messages", []):
                compare_models_data = _compare(compare_models, messages, temperature, max_tokens, top_p)
                benchmark_data.update(compare_models_data)
                data.append(benchmark_data)
            else:
                rich.print(f"Skip completion {id}. No messages found in the request.")
                skipped_completion_ids.append(id)
        except Exception as e:
            rich.print(f"Error processing completion {id}. {str(e)}")
            rich.print(f"Completion {completion_data}")
            skipped_completion_ids.append(id)

    prompt_analysis_data = {}
    if analyze_prompt:
        rich.print("Analyzing prompts")
        for item in data:
            completion_id = item["completion_id"]
            prompt_messages = item["original_request"]["messages"]
            all_messages = "\n\n".join([m["content"] for m in prompt_messages])
            analyzer = PromptAnalyzer()
            suggestions = analyzer.analyze(all_messages)
            prompt_analysis_data[completion_id] = suggestions

    # create an empty dataframe
    all_df = pd.DataFrame(
        columns=[
            "completion_id",
            "tags",
            "prompt_messages",
            "model",
            "content",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "duration_ms",
        ]
    )

    #
    # Display or save the results
    #
    if not file:
        # display in terminal using rich
        for ret in data:
            _render_comparison_table(ret)
            if analyze_prompt:
                completion_id = ret["completion_id"]
                suggestions = prompt_analysis_data[completion_id]
                rich.print(f"Prompt Analysis for completion_id: {completion_id}")
                display_prompt_analyzer_suggestions(suggestions)
    else:
        # generate markdown report and save to file
        for ret in data:
            df = _create_dataframe_from_comparison_data(ret)
            all_df = pd.concat([all_df, df])

        if ext_name == ".csv":
            # save the dataframe to a csv file
            all_df.to_csv(path, index=False)
            rich.print(f"Dataframe saved to csv file: {path}")
        elif ext_name == ".jsonl":
            # save the dataframe to a jsonl file
            all_df.to_json(path, orient="records", lines=True)
            rich.print(f"Dataframe saved to jsonl file: {path}")
        elif ext_name == ".md":
            # generate markdown report
            pivot_df = all_df.pivot(index="completion_id", columns="model", values="content")
            pivot_df["prompt_messages"] = all_df.groupby("completion_id")["prompt_messages"].first()
            # Reorder the columns
            cols = pivot_df.columns.tolist()
            cols = [cols[-1]] + cols[:-1]
            pivot_df = pivot_df[cols]

            pivot_table = generate_results_table(pivot_df, section_name="model comparison")
            all_results_table = generate_results_table(all_df, section_name="All Results")

            prompt_analysis_markdown = ""
            if analyze_prompt:
                prompt_analysis_markdown = "## Prompt Analysis\n\n"
                for completion_id, suggestions in prompt_analysis_data.items():
                    prompt_messages = all_df[all_df["completion_id"] == completion_id]["prompt_messages"].values[0]
                    prompt_analysis_markdown += (
                        f"### Prompt Analysis for completion_id: {completion_id}\n\n{prompt_messages}\n\n"
                    )
                    prompt_analysis_markdown += convert_suggestion_to_markdown(suggestions)

            # generate the list of skipped completions ids
            skipped_completion_markdown = ""
            if skipped_completion_ids:
                skipped_completion_ids_str = ", ".join(skipped_completion_ids)
                skipped_completion_markdown += "## Skipped Completion IDs\n\n"
                skipped_completion_markdown += f"Skipped completions: {skipped_completion_ids_str}\n\n"

            generate_markdown_report(
                path, [pivot_table, prompt_analysis_markdown, all_results_table, skipped_completion_markdown]
            )
            rich.print(f"Report saved to markdown file: {path}")
