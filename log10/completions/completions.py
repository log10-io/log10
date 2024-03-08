import json

import click
import httpx
import rich
import tqdm
from rich.console import Console
from rich.table import Table

from log10._httpx_utils import _get_time_diff, _try_get
from log10.llm import Log10Config


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
    for tag in tags.split(","):
        tag_id = _get_tag_id(tag)
        if tag_id:
            tag_ids.append(tag_id)
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
