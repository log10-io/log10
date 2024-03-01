import json
import logging

import click
import httpx
import rich
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

    def list(self, limit: int = 10, offset: int = 0) -> httpx.Response:
        url = f"{self._log10_config.url}/api/v1/feedback_task?organization_id={self._log10_config.org_id}&offset={offset}&limit={limit}"
        try:
            res = self._http_client.get(url=url)
            res.raise_for_status()
            return res
        except Exception as e:
            logger.error(e)
            logger.error(e.response.json()["error"])
            raise


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


@click.command()
@click.option("--limit", default=50, help="Number of feedback tasks to fetch")
@click.option("--offset", default=0, help="Offset for the feedback tasks")
def list_feedback_task(limit, offset):
    res = FeedbackTask().list(limit=limit, offset=offset)
    feedback_tasks = res.json()
    rich.print(feedback_tasks)
# def list():
#     # http://localhost:3000/api/v1/feedback_task?organization_id=4ffbada7-a483-49f6-83c0-987d07c779ed&offset=0&limit=50
