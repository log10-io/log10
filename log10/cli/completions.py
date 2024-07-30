import json
from pathlib import Path

import click
import pandas as pd
import rich
import tqdm
from rich.console import Console
from rich.table import Table

from log10._httpx_utils import _get_time_diff, _try_get
from log10.cli_utils import generate_markdown_report, generate_results_table
from log10.completions.completions import (
    _check_model_support,
    _compare,
    _get_completion,
    _get_completions_url,
    _write_completions,
)
from log10.llm import Log10Config
from log10.prompt_analyzer import PromptAnalyzer, convert_suggestion_to_markdown, display_prompt_analyzer_suggestions


_log10_config = Log10Config()


def _render_completions_table(completions_data, total_completions):
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
                        or message.get("tool_calls", [])[-1].get("function", {}).get("arguments", "")
                        if message.get("tool_calls")
                        else ""
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
    console.print(f"{total_completions=}")


def _render_comparison_table(model_response_raw_data):
    rich.print(f"completion_id: {model_response_raw_data['completion_id']}")
    rich.print("original_request:")
    rich.print_json(json.dumps(model_response_raw_data["original_request"], indent=4))

    table = rich.table.Table(show_header=True, header_style="bold magenta", box=rich.box.ROUNDED, show_lines=True)
    table.add_column("Model")
    table.add_column("Content")
    table.add_column("Total Token Usage (Input/Output)")
    table.add_column("Duration (ms)")

    for model, data in model_response_raw_data.items():
        # only display model data
        if model not in ["completion_id", "original_request"]:
            usage = data["usage"]
            formatted_usage = f"{usage['total_tokens']} ({usage['prompt_tokens']}/{usage['completion_tokens']})"
            table.add_row(model, data["content"], formatted_usage, str(data["duration"]))
    rich.print(table)


def _create_dataframe_from_comparison_data(model_response_raw_data):
    completion_id = model_response_raw_data["completion_id"]
    original_request = model_response_raw_data["original_request"]
    rows = []
    for model, model_data in model_response_raw_data.items():
        # only display model data
        if model not in ["completion_id", "original_request"]:
            content = model_data["content"]
            usage = model_data["usage"]
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
            total_tokens = usage["total_tokens"]
            duration = model_data["duration"]
            prompt_messages = json.dumps(original_request["messages"])
            rows.append(
                [
                    completion_id,
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

    completions = res.json()
    total_completions = completions["total"]
    completions = completions["data"]

    _render_completions_table(completions, total_completions)


@click.command()
@click.option("--id", prompt="Enter completion id", help="Completion ID")
def get_completion(id):
    """
    Get a completion by id
    """
    res = _get_completion(id)
    rich.print_json(json.dumps(res.json()["data"], indent=4))


@click.command()
@click.option("--limit", default="", help="Specify the maximum number of completions to retrieve.")
@click.option("--offset", default="", help="Set the starting point (offset) from where to begin fetching completions.")
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
@click.option("--compact", is_flag=True, help="Enable to download only the compact version of the output.")
@click.option("--file", "-f", default="completions.jsonl", help="Specify the filename and path for the output file.")
def download_completions(limit, offset, timeout, tags, from_date, to_date, compact, file):
    """
    Download completions to a jsonl file
    """
    base_url = _log10_config.url
    org_id = _log10_config.org_id

    init_url = _get_completions_url(1, 0, tags, from_date, to_date, base_url, org_id)
    res = _try_get(init_url)
    if res.status_code != 200:
        rich.print(f"Error: {res.json()}")
        return

    total_completions = res.json()["total"]
    offset = int(offset) if offset else 0
    limit = int(limit) if limit else total_completions
    rich.print(f"Download total completions: {limit}/{total_completions}")
    if not click.confirm("Do you want to continue?"):
        return

    # dowlnoad completions
    pbar = tqdm.tqdm(total=limit)
    batch_size = 10
    end = offset + limit if offset + limit < total_completions else total_completions
    for batch in range(offset, end, batch_size):
        current_batch_size = batch_size if batch + batch_size < end else end - batch
        download_url = _get_completions_url(
            current_batch_size, batch, tags, from_date, to_date, base_url, org_id, printout=False
        )
        res = _try_get(download_url, timeout)
        _write_completions(res, file, compact)
        pbar.update(current_batch_size)


@click.command()
@click.option("--ids", default="", help="Completion IDs. Separate multiple ids with commas.")
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
        completion_ids = [id for id in ids.split(",") if id]
    elif tags:
        base_url = _log10_config.url
        org_id = _log10_config.org_id
        url = _get_completions_url(limit, offset, tags, None, None, base_url, org_id)
        res = _try_get(url)
        completions = res.json()["data"]
        completion_ids = [completion["id"] for completion in completions]
        if not completion_ids:
            SystemExit(f"No completions found for tags: {tags}")

    compare_models = [m for m in models.split(",") if m]

    data = []
    skipped_completion_ids = []
    for id in completion_ids:
        rich.print(f"Processing completion {id}")
        # get message from id
        completion_data = _get_completion(id).json()["data"]

        # skip completion if status is not finished or kind is not chat
        if completion_data["status"] != "finished" or completion_data["kind"] != "chat":
            rich.print(f"Skip completion {id}. Status is not finished or kind is not chat.")
            skipped_completion_ids.append(id)
            continue

        original_model_request = completion_data["request"]
        original_model_response = completion_data["response"]
        original_model = original_model_response["model"]
        benchmark_data = {
            "completion_id": id,
            "original_request": original_model_request,
            f"{original_model} (original model)": {
                "content": original_model_response["choices"][0]["message"]["content"],
                "usage": original_model_response["usage"],
                "duration": completion_data["duration"],
            },
        }
        messages = original_model_request["messages"]
        compare_models_data = _compare(compare_models, messages, temperature, max_tokens, top_p)
        benchmark_data.update(compare_models_data)
        data.append(benchmark_data)

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
