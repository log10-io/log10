import json
from datetime import datetime, timezone

import tqdm
import click
import httpx
import rich
from rich.console import Console
from rich.table import Table

from log10.llm import Log10Config


# TODO: Support data filters
# TODO: Support ranges
# TODO: Support tag filters
# TODO: Support jsonl output
_log10_config = Log10Config()


def _get_time_diff(created_at):
    time = datetime.fromisoformat(created_at)
    now = datetime.now(timezone.utc)
    diff = now - time
    # convert the time difference to human readable format
    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds//3600} hours ago"
    elif diff.seconds > 60:
        return f"{diff.seconds//60} minutes ago"


def _get_completion(id: str) -> httpx.Response:
    with httpx.Client() as client:
        client.headers = {
            "x-log10-token": _log10_config.token,
            "x-log10-organization-id": _log10_config.org_id,
            "Content-Type": "application/json",
        }
        url = f"{_log10_config.url}/api/completions/{id}?organization_id={_log10_config.org_id}"
        try:
            res = client.get(url=url)
            res.raise_for_status()
            return res
        except Exception as e:
            click.echo(f"Error: {e}")
            if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
                click.echo(e.response.json()["error"])
            return


def _get_tag_id(tag: str) -> str:
    with httpx.Client() as client:
        client.headers = {
            "x-log10-token": _log10_config.token,
            "x-log10-organization-id": _log10_config.org_id,
            "Content-Type": "application/json",
        }
        url = f"{_log10_config.url}/api/tags/search?organization_id={_log10_config.org_id}&query={tag}"
        try:
            res = client.get(url=url)
            res.raise_for_status()
        except Exception as e:
            click.echo(f"Error: {e}")
            if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
                click.echo(e.response.json()["error"])
            return

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


@click.command()
@click.option("--limit", default=25, help="Number of completions to fetch")
@click.option("--offset", default=0, help="Offset for the completions")
@click.option("--timeout", default=10, help="Timeout for the http request")
@click.option("--tags", default="", help="Filter completions by tag")
@click.option(
    "--from", "from_date", type=click.DateTime(), help="Start date of the range (inclusive). Format: YYYY-MM-DD"
)
@click.option("--to", "to_date", type=click.DateTime(), help="End date of the range (inclusive). Format: YYYY-MM-DD")
def list_completions(limit, offset, timeout, tags, from_date, to_date):
    """
    List completions
    """
    base_url = _log10_config.url
    token = _log10_config.token
    org_id = _log10_config.org_id

    # Fetch completions
    with httpx.Client() as client:
        client.headers = {
            "x-log10-token": token,
            "x-log10-organization-id": org_id,
            "Content-Type": "application/json",
        }

        tag_ids_str = ""
        if tags:
            tag_ids = []
            for tag in tags.split(","):
                tag_id = _get_tag_id(tag)
                if tag_id:
                    tag_ids.append(tag_id)
            tag_ids_str = ",".join(tag_ids)
            rich.print(f"Filter with tags: {tags}")

        if (from_date is None) != (to_date is None):  # Check if only one date is provided
            raise click.UsageError("Both --from and --to must be set together.")

        if from_date and to_date:
            if from_date >= to_date:
                raise click.UsageError(f"from_date {from_date} must be earlier than to_date {to_date}")

            parsed_from_date = from_date.replace(hour=8).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            parsed_to_date = to_date.replace(hour=8).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

            date_range = {"from": parsed_from_date, "to": parsed_to_date}
            rich.print(f"Filter with created date: {date_range['from'][:10]} to {date_range['to'][:10]}")
        else:
            date_range = {}

        url = f"{base_url}/api/completions?organization_id={org_id}&offset={offset}&limit={limit}&tagFilter={tag_ids_str}&createdFilter={json.dumps(date_range)}&sort=created_at&desc=true&ids="

        httpx_timeout = httpx.Timeout(timeout)
        try:
            res = client.get(url=url, timeout=httpx_timeout)
            res.raise_for_status()
        except Exception as e:
            rich.print(f"Error: {e}")
            if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
                rich.print(e.response.json()["error"])
            return

    completions = res.json()
    total_completions = completions["total"]
    completions = completions["data"]

    # create a list of items, each item is a dictionary with the completion id, created_at, status, prompt, response, and tags
    data_for_table = []
    for completion in completions:
        if completion["response"]["object"] == "text_completion":
            prompt = completion["request"]["prompt"]
            response = completion["response"]["choices"][0]["text"]
        elif "function_call" in completion["response"]["choices"][0]:
            prompt = completion["request"]["messages"][0]["content"]
            response = json.dumps(completion["response"]["choices"][0]["function_call"])
        else:
            prompt = completion["request"]["messages"][0]["content"]
            response = completion["response"]["choices"][0]["message"]["content"]
        # import ipdb; ipdb.set_trace()
        data_for_table.append(
            {
                "id": completion["id"],
                "status": "success" if completion["status"] == "finished" else completion["status"],
                "created_at": _get_time_diff(completion["created_at"]),
                "prompt": prompt,
                "completion": response,
                "tags": completion["tags"],
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
@click.option("--id", prompt="Enter completion id", help="Completion ID")
def get_completion(id):
    """
    Get a completion by id
    """
    res = _get_completion(id)
    rich.print(res.json())


@click.command()
@click.option("--limit", default="", help="Number of completions to fetch")
@click.option("--offset", default="", help="Offset for the completions")
@click.option("--timeout", default=10, help="Timeout for the http request")
@click.option("--tags", default="", help="Filter completions by tag")
@click.option(
    "--from", "from_date", type=click.DateTime(), help="Start date of the range (inclusive). Format: YYYY-MM-DD"
)
@click.option("--to", "to_date", type=click.DateTime(), help="End date of the range (inclusive). Format: YYYY-MM-DD")
@click.option("--compact", is_flag=True, help="Download the compact output only")
@click.option("--output", default="completions.jsonl", help="Output file")
def download_completions(limit, offset, timeout, tags, from_date, to_date, output, compact):
    """
    Download completions to a jsonl file
    """
    base_url = _log10_config.url
    token = _log10_config.token
    org_id = _log10_config.org_id
    completion_url_prefix = f"{base_url}/api/completions?organization_id={org_id}&sort=created_at&desc=true&ids="

    # Fetch completions
    with httpx.Client() as client:
        client.headers = {
            "x-log10-token": token,
            "x-log10-organization-id": org_id,
            "Content-Type": "application/json",
        }

        tag_ids_str = ""
        if tags:
            tag_ids = []
            for tag in tags.split(","):
                tag_id = _get_tag_id(tag)
                if tag_id:
                    tag_ids.append(tag_id)
            tag_ids_str = ",".join(tag_ids)
            rich.print(f"Filter with tags: {tags}")

        if (from_date is None) != (to_date is None):  # Check if only one date is provided
            raise click.UsageError("Both --from and --to must be set together.")

        if from_date and to_date:
            if from_date >= to_date:
                raise click.UsageError(f"from_date {from_date} must be earlier than to_date {to_date}")

            parsed_from_date = from_date.replace(hour=8).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            parsed_to_date = to_date.replace(hour=8).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

            date_range = {"from": parsed_from_date, "to": parsed_to_date}
            rich.print(f"Filter with created date: {date_range['from'][:10]} to {date_range['to'][:10]}")
        else:
            date_range = {}

        init_url = (
            f"{completion_url_prefix}&offset=&limit=1&tagFilter={tag_ids_str}&createdFilter={json.dumps(date_range)}"
        )
        try:
            res = client.get(url=init_url, timeout=timeout)
            res.raise_for_status()
        except Exception as e:
            rich.print(f"Error: {e}")
            if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
                rich.print(e.response.json()["error"])
            return
        else:
            total_completions = res.json()["total"]
            rich.print(f"Download total completions: {total_completions}")
            # prompt the user to confirm the download, only [y]es will continue
            if not click.confirm("Do you want to continue?"):
                return

        # if offset + limit > total_completions:
        if not offset:
            offset = 0
        if not limit:
            limit = total_completions

        # dowlnoad completions
        batch_size = 10

        # tqdm progress bar
        with tqdm.tqdm(total=limit // batch_size) as pbar:
            for batch in tqdm.tqdm(range(offset, limit, batch_size)):
                download_url = f"{completion_url_prefix}&offset={batch}&limit={batch_size}&tagFilter={tag_ids_str}&createdFilter={json.dumps(date_range)}"
                # rich.print(f"Downloading completions from {batch} to {batch + batch_size}")
                # rich.print(f"URL: {download_url}")
                # continue

                try:
                    res = client.get(url=download_url, timeout=timeout)
                    res.raise_for_status()
                except Exception as e:
                    rich.print(f"Error: {e}")
                    if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
                        rich.print(e.response.json()["error"])
                    return

                if compact:
                    res = res.json()["data"]
                    with open(output, "a") as f:
                        for completion in res:
                            f.write(json.dumps(completion) + "\n")
                else:
                    completions_id_list = [completion["id"] for completion in res.json()["data"]]
                    for id in completions_id_list:
                        completion = _get_completion(id)
                        with open(output, "a") as f:
                            f.write(json.dumps(completion.json()) + "\n")
