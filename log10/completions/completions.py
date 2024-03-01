from datetime import datetime, timezone

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


@click.command()
@click.option("--limit", default=25, help="Number of completions to fetch")
@click.option("--offset", default=0, help="Offset for the completions")
@click.option("--ids", default="", help="Comma separated list of completion ids")
@click.option("--timeout", default=10, help="Timeout for the http request")
# def list_completions(ids=None, tagFilter=None, createdFilter=None, sort=None, desc=None, limit=25, offset=None):
def list_completions(limit, offset, ids, timeout):
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
        url = f"{base_url}/api/completions?organization_id={org_id}&offset={offset}&limit={limit}&tagFilter=&createdFilter=%7B%7D&sort=created_at&desc=true&ids="
        httpx_timeout = httpx.Timeout(timeout)
        try:
            res = client.get(url=url, timeout=httpx_timeout)
            res.raise_for_status()
        except Exception as e:
            click.echo(f"Error: {e}")
            if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
                click.echo(e.response.json()["error"])
            return

    completions = res.json()
    total_completions = completions["total"]
    completions = completions["data"]

    # create a list of items, each item is a dictionary with the completion id, created_at, status, prompt, response, and tags
    data_for_table = []
    for completion in completions:
        # loop thru completion['request']['messages'] and return the first message with 'role' == 'user'
        # prompt =
        prompt = completion["request"]["messages"][0]["content"]
        response = completion["response"]["choices"][0]["message"]["content"]
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
