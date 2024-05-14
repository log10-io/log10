import json
import time

import click
import httpx
import pandas as pd
import rich
import tqdm
from rich.console import Console
from rich.table import Table

from log10._httpx_utils import _get_time_diff, _try_get
from log10.cli_utils import generate_markdown_report, generate_results_table
from log10.llm import Log10Config
from log10.prompt_analyzer import PromptAnalyzer, convert_suggestion_to_markdown, display_prompt_analyzer_suggestions


_log10_config = Log10Config()


def _get_completion(id: str) -> httpx.Response:
    url = f"{_log10_config.url}/api/completions/{id}?organization_id={_log10_config.org_id}"
    return _try_get(url)


def _get_tag_id(tag: str) -> str:
    url = f"{_log10_config.url}/api/tags/search?organization_id={_log10_config.org_id}&query={tag}"
    res = _try_get(url)
    data = res.json()["data"]
    if not data:
        return []

    if len(data) == 1:
        return data[0]["id"]
    else:
        for item in data:
            if item["name"] == tag:
                return item["id"]
        return []


def _get_tag_ids(tags):
    tag_ids = []
    for tag in [t for t in tags.split(",") if t]:
        tag_id = _get_tag_id(tag)
        if tag_id:
            tag_ids.append(tag_id)
        else:
            raise SystemExit(f"Cannot found tag: {tag}.")

    tag_ids_str = ",".join(tag_ids)
    return tag_ids_str


def _get_completions_url(limit, offset, tags, from_date, to_date, base_url, org_id, printout=True):
    tag_ids_str = _get_tag_ids(tags) if tags else ""
    if tag_ids_str and printout:
        rich.print(f"Filter with tags: {tags}")

    date_range = _get_valid_date_range(from_date, to_date)
    if date_range and printout:
        rich.print(f"Filter with created date: {date_range['from'][:10]} to {date_range['to'][:10]}")

    url = f"{base_url}/api/completions?organization_id={org_id}&offset={offset}&limit={limit}&tagFilter={tag_ids_str}&createdFilter={json.dumps(date_range)}&sort=created_at&desc=true&ids="
    return url


def _get_valid_date_range(from_date, to_date):
    if not from_date and not to_date:
        return {}

    if from_date is None or to_date is None:
        raise click.UsageError("Both --from and --to must be set together.")

    if from_date >= to_date:
        raise click.UsageError(f"from_date {from_date} must be earlier than to_date {to_date}")

    parsed_from_date = from_date.replace(hour=8).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    parsed_to_date = to_date.replace(hour=8).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    date_range = {"from": parsed_from_date, "to": parsed_to_date}
    return date_range


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
                    response = first_choice["message"].get("content", "")
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
        short_completion = (
            item["completion"][:max_len] + "..." if len(item["completion"]) > max_len else item["completion"]
        )
        table.add_row(item["id"], item["status"], item["created_at"], short_prompt, short_completion, tags)

    console = Console()
    console.print(table)
    console.print(f"{total_completions=}")


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


def _write_completions(res, output_file, compact_mode):
    """Processes completions and appends them to the output file."""
    with open(output_file, "a") as file:
        data = res.json()["data"]
        if compact_mode:
            for completion in data:
                file.write(json.dumps(completion) + "\n")
        else:
            for completion_id in (completion["id"] for completion in data):
                completion = _get_completion(completion_id).json()["data"]
                file.write(json.dumps(completion) + "\n")


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


def _get_llm_repsone(
    model: str,
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 512,
    top_p: float = 1.0,
):
    ret = {"content": "", "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "duration": 0.0}

    start_time = time.perf_counter()
    if "gpt-4" in model or "gpt-3.5" in model:
        from log10.load import OpenAI

        client = OpenAI()
        response = client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p
        )
        ret["content"] = response.choices[0].message.content
        ret["usage"] = response.usage.dict()
    elif "claude-3" in model:
        from log10.load import Anthropic

        system_messages = [m["content"] for m in messages if m["role"] == "system"]
        other_messages = [m for m in messages if m["role"] != "system"]
        system_prompt = ("\n").join(system_messages)

        client = Anthropic()
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=other_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        ret["content"] = response.content[0].text
        ret["usage"]["prompt_tokens"] = response.usage.input_tokens
        ret["usage"]["completion_tokens"] = response.usage.output_tokens
        ret["usage"]["total_tokens"] = response.usage.input_tokens + response.usage.output_tokens
    elif "mistral" in model:
        import mistralai
        from mistralai.client import MistralClient

        from log10.load import log10

        log10(mistralai)

        client = MistralClient()
        response = client.chat(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p
        )
        ret["content"] = response.choices[0].message.content
        ret["usage"] = response.usage.model_dump()
    else:
        raise ValueError(f"Model {model} not supported.")
    ret["duration"] = int((time.perf_counter() - start_time) * 1000)

    return ret


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
            "Completion ID",
            "Prompt Messages",
            "Model",
            "Content",
            "Prompt Tokens",
            "Completion Tokens",
            "Total Tokens",
            "Duration (ms)",
        ],
    )

    return df


def _compare(models: list[str], messages: dict, temperature: float = 0.2, max_tokens: float = 256, top_p: float = 1.0):
    ret = {}
    if models:
        for model in models:
            rich.print(f"Running {model}")
            response = _get_llm_repsone(
                model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )

            ret[model] = response
    return ret


_SUPPORTED_MODELS = [
    # openai chat models
    "gpt-4o",
    "gpt-4o-2024-05-13",
    "gpt-4-turbo",
    "gpt-4-turbo-2024-04-09",
    "gpt-4-0125-preview",
    "gpt-4-turbo-preview",
    "gpt-4-1106-preview",
    "gpt-4-vision-preview",
    "gpt-4",
    "gpt-4-0314",
    "gpt-4-0613",
    "gpt-4-32k",
    "gpt-4-32k-0314",
    "gpt-4-32k-0613",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-0301",
    "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-16k-0613",
    # anthropic claude
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    # mistral
    "mistral-small-latest",
    "mistral-medium-latest",
    "mistral-large-latest",
]


def _check_model_support(model: str) -> bool:
    return model in _SUPPORTED_MODELS


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
@click.option("--file", "-f", help="Specify the filename for the report in markdown format.")
def benchmark_models(ids, tags, limit, offset, models, temperature, max_tokens, top_p, file, analyze_prompt):
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
            "Completion ID",
            "Prompt Messages",
            "Model",
            "Content",
            "Prompt Tokens",
            "Completion Tokens",
            "Total Tokens",
            "Duration (ms)",
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
        pivot_df = all_df.pivot(index="Completion ID", columns="Model", values="Content")
        pivot_df["Prompt Messages"] = all_df.groupby("Completion ID")["Prompt Messages"].first()
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
                prompt_messages = all_df[all_df["Completion ID"] == completion_id]["Prompt Messages"].values[0]
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
            file, [pivot_table, prompt_analysis_markdown, all_results_table, skipped_completion_markdown]
        )
        rich.print(f"Report saved to {file}")
