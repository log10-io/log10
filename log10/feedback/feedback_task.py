import json
import logging

import click
import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from log10._httpx_utils import _get_time_diff, _try_get
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

    def create(
        self, task_schema: dict, name: str, completion_tags_selector: list[str] = None, instruction: str = None
    ) -> httpx.Response:
        json_payload = {"json_schema": task_schema, "name": name, "completion_tags_selector": completion_tags_selector}
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

    def get(self, id: str) -> httpx.Response:
        based_url = self._log10_config.url
        api_url = "/api/v1/feedback_task"
        get_url = f"{based_url}{api_url}/{id}?organization_id={self._log10_config.org_id}"
        res = _try_get(get_url)
        res.raise_for_status()
        if res.status_code != 200:
            raise Exception(f"Error fetching feedback task {res.json()}")
        return res


# create a cli interface for FeebackTask.create function
@click.command()
@click.option("--name", prompt="Enter feedback task name", help="Name of the task")
@click.option("--task_schema", prompt="Enter feedback task schema", help="Task schema")
@click.option("--instruction", help="Task instruction", default="")
@click.option(
    "--completion_tags_selector",
    help="Completion tags selector",
)
def create_feedback_task(name, task_schema, instruction, completion_tags_selector=None):
    click.echo("Creating feedback task")
    tags = []

    if completion_tags_selector:
        tags = completion_tags_selector.split(",")

    task_schema = json.loads(task_schema)
    task = FeedbackTask().create(
        name=name, task_schema=task_schema, completion_tags_selector=tags, instruction=instruction
    )
    click.echo(f"Use this task_id to add feedback: {task.json()['id']}")


@click.command()
@click.option("--limit", default=25, help="Number of feedback tasks to fetch")
@click.option("--offset", default=0, help="Offset for the feedback tasks")
def list_feedback_task(limit, offset):
    res = FeedbackTask().list(limit=limit, offset=offset)
    feedback_tasks = res.json()

    data_for_table = []

    for task in feedback_tasks["data"]:
        data_for_table.append(
            {
                "id": task["id"],
                "created_at": _get_time_diff(task["created_at"]),
                "name": task["name"],
                "required": task["json_schema"]["required"],
                "instruction": task["instruction"],
            }
        )

    table = Table(title="Feedback Tasks")
    table.add_column("ID", style="dim")
    table.add_column("Created At")
    table.add_column("Name")
    table.add_column("Required")
    table.add_column("Instruction")
    for item in data_for_table:
        required = ", ".join(item["required"]) if item["required"] else ""
        table.add_row(item["id"], item["created_at"], item["name"], required, item["instruction"])

    console = Console()
    console.print(table)


@click.command()
@click.option("--id", help="Get feedback task by ID")
def get_feedback_task(id):
    try:
        res = FeedbackTask().get(id)
    except Exception as e:
        click.echo(f"Error fetching feedback task {e}")
        if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
            click.echo(e.response.json()["error"])
        return
    task = json.dumps(res.json())
    console = Console()
    console.print_json(task)
