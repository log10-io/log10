import json
import logging

import click
import httpx
import rich
from rich.console import Console
from rich.table import Table

from log10.llm import Log10Config


logging.basicConfig(
    format="[%(asctime)s - %(name)s - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger("LOG10")
logger.setLevel(logging.INFO)


class Feedback:
    feedback_create_url = "/api/v1/feedback"

    def __init__(self, log10_config: Log10Config = None):
        self._log10_config = log10_config or Log10Config()
        self._http_client = httpx.Client()
        self._http_client.headers = {
            "x-log10-token": self._log10_config.token,
            "x-log10-organization-id": self._log10_config.org_id,
            "Content-Type": "application/json",
        }

    def _post_request(self, url: str, json_payload: dict) -> httpx.Response:
        json_payload["organization_id"] = self._log10_config.org_id
        try:
            res = self._http_client.post(self._log10_config.url + url, json=json_payload)
            res.raise_for_status()
            return res
        except Exception as e:
            logger.error(e)
            if hasattr(e, 'response') and hasattr(e.response, 'json') and 'error' in e.response.json():
                logger.error(e.response.json()["error"])
            raise

    def create(
        self,
        task_id: str,
        values: dict,
        completion_tags_selector: list[str],
        comment: str = None,
    ) -> httpx.Response:
        json_payload = {
            "task_id": task_id,
            "json_values": values,
            "completion_tags_selector": completion_tags_selector,
            "comment": comment,
        }
        res = self._post_request(self.feedback_create_url, json_payload)
        return res

    def list(self, offset: int = 0, limit: int = 25, task_id: str = None) -> httpx.Response:
        base_url = self._log10_config.url
        api_url = "/api/v1/feedback"
        url = f"{base_url}{api_url}?organization_id={self._log10_config.org_id}&offset={offset}&limit={limit}"

        # GET feedback
        try:
            res = self._http_client.get(url=url)
            res.raise_for_status()
            return res
        except Exception as e:
            logger.error(e)
            if hasattr(e, 'response') and hasattr(e.response, 'json') and 'error' in e.response.json():
                logger.error(e.response.json()["error"])
            raise


@click.command()
@click.option("--task_id", prompt="Enter task id", help="Task ID")
@click.option("--values", prompt="Enter task values", help="Feedback in JSON format")
@click.option(
    "--completion_tags_selector",
    prompt="Enter completion tags selector",
    help="Completion tags selector",
)
@click.option("--comment", help="Comment", default="")
def create_feedback(task_id, values, completion_tags_selector, comment):
    """
    Add feedback to a group of completions associated with a task
    """
    click.echo("Creating feedback")
    tags = completion_tags_selector.split(",")
    values = json.loads(values)
    feedback = Feedback().create(task_id=task_id, values=values, completion_tags_selector=tags, comment=comment)
    click.echo(feedback.json())

@click.command()
@click.option("--offset", default=0, help="Offset for the feedback")
@click.option("--limit", default=25, help="Number of feedback to fetch")
def list_feedback(offset, limit):
    """
    List feedback
    """
    try:
        res = Feedback().list(offset=offset, limit=limit)
    except Exception as e:
        click.echo(f"Error fetching feedback {e}")
        if hasattr(e, 'response') and hasattr(e.response, 'json') and 'error' in e.response.json():
            click.echo(e.response.json()["error"])
        return

    rich.print(res.json())
    # save res.json() to a file all_feedback.txt
    with open("all_feedback.txt", "w") as f:
        f.write(json.dumps(res.json(), indent=4))


    # http://localhost:3000/api/v1/feedback?organization_id=4ffbada7-a483-49f6-83c0-987d07c779ed&offset=0&limit=50
    # click.echo("List feedback")
