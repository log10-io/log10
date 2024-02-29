import click
import os
import requests

# TODO: Support data filters
# TODO: Support ranges
# TODO: Support tag filters
# TODO: Support jsonl output
url = os.environ.get("LOG10_URL", "https://localhost:3000")

from rich.console import Console
from rich.table import Table

console = Console()

@click.command()
def list_completions(ids=None, tagFilter=None, createdFilter=None, sort=None, desc=None, limit=None, offset=None):
    print(os.environ.get("LOG10_URL"))
    print(os.environ.get("LOG10_ORG_ID"))
    print(os.environ.get("LOG10_TOKEN"))

    # Fetch completions
    # TODO: Move to a helper function
    response = requests.get(
        f"{url}/api/completions?organization_id={os.environ.get('LOG10_ORG_ID')}&offset=0&limit=50&tagFilter=&createdFilter=%7B%7D&sort=created_at&desc=true&ids=",
        headers={
            "x-log10-token": os.environ.get("LOG10_TOKEN"),
            "x-log10-organization-id": os.environ.get("LOG10_ORG_ID"),
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    completions = response.json()

    # TODO: Render completions

    click.echo(completions)
    click.echo("List completions")

# curl 'http://localhost:3000/api/completions?organization_id=4ffbada7-a483-49f6-83c0-987d07c779ed&offset=0&limit=50&tagFilter=&createdFilter=%7B%7D&sort=created_at&desc=true&ids='