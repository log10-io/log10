import json
import logging

import click
import httpx
from dotenv import load_dotenv

from log10.llm import Log10Config


load_dotenv()

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

    def _post_request(self, url: str, json_payload: dict) -> httpx.Response:
        headers = {
            "x-log10-token": self._log10_config.token,
            "x-log10-organization-id": self._log10_config.org_id,
            "Content-Type": "application/json",
        }
        json_payload["organization_id"] = self._log10_config.org_id
        try:
            res = self._http_client.post(self._log10_config.url + url, headers=headers, json=json_payload)
            res.raise_for_status()
            return res
        except Exception as e:
            logger.error(e)
            logger.error(e.response.json()["error"])
            raise

    def create(
        self, task_id: str, values: dict, completion_tags_selector: list[str], comment: str = None
    ) -> httpx.Response:
        json_payload = {
            "task_id": task_id,
            "json_values": values,
            "completion_tags_selector": completion_tags_selector,
            "comment": comment,
        }
        res = self._post_request(self.feedback_create_url, json_payload)
        return res


@click.command()
@click.option("--task_id", prompt="Enter task id", help="Task ID")
@click.option("--values", prompt="Enter task values", help="Feedback in JSON format")
@click.option("--completion_tags_selector", prompt="Enter completion tags selector", help="Completion tags selector")
@click.option("--comment", help="Comment", default="")
def create_feedback(task_id, values, completion_tags_selector, comment):
    click.echo("Creating feedback")
    tags = completion_tags_selector.split(",")
    values = json.loads(values)
    feedback = Feedback().create(task_id=task_id, values=values, completion_tags_selector=tags, comment=comment)
    click.echo(feedback.json())
