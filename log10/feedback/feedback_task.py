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


class FeedbackTask:
    feedback_task_create_url = "/api/v1/feedback_task"

    def __init__(self, log10_config: Log10Config = None):
        self._log10_config = log10_config or Log10Config()
        self._http_client = httpx.Client()

    def _post_request(self, url: str, json_payload: dict) -> httpx.Response:
        headers = {
            "x-log10-token": self._log10_config.token,
            "Content-Type": "application/json",
            "x-log10-organization-id": self._log10_config.org_id,
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

    def create(self, task_schema: dict, name: str = None, instruction: str = None) -> httpx.Response:
        json_payload = {"json_schema": task_schema}
        if name:
            json_payload["name"] = name
        if instruction:
            json_payload["instruction"] = instruction

        res = self._post_request(self.feedback_task_create_url, json_payload)
        return res


# create a cli interface for FeebackTask.create function
@click.command()
@click.option("--name", prompt="Enter feedback task name", help="Name of the task")
@click.option("--task_schema", prompt="Enter feedback task schema", help="Task schema")
@click.option("--instruction", help="Task instruction", default="")
def create_feedback_task(name, task_schema, instruction):
    click.echo("Creating feedback task")
    task_schema = json.loads(task_schema)
    task = FeedbackTask().create(name=name, task_schema=task_schema, instruction=instruction)
    click.echo(f"Use this task_id to add feedback: {task.json()['id']}")
