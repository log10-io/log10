import json
import logging

import click
import httpx
from rich.console import Console
from rich.table import Table
from tqdm import tqdm

from log10._httpx_utils import _try_get
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
            if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
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

    def list(self, offset: int = 0, limit: int = 50, task_id: str = "") -> httpx.Response:
        base_url = self._log10_config.url
        api_url = "/api/v1/feedback"
        url = f"{base_url}{api_url}?organization_id={self._log10_config.org_id}&offset={offset}&limit={limit}&task_id={task_id}"

        # GET feedback
        try:
            res = self._http_client.get(url=url)
            res.raise_for_status()
            return res
        except Exception as e:
            logger.error(e)
            if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
                logger.error(e.response.json()["error"])
            raise

    def get(self, id: str) -> httpx.Response:
        base_url = self._log10_config.url
        api_url = "/api/v1/feedback"
        get_url = f"{base_url}{api_url}/{id}?organization_id={self._log10_config.org_id}"
        res = _try_get(get_url)
        res.raise_for_status()
        if res.status_code != 200:
            raise Exception(f"Error fetching feedback: {res.json()}")
        return res


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


def _get_feedback_list(offset, limit, task_id):
    total_fetched = 0
    feedback_data = []
    total_feedback = 0
    if limit:
        limit = int(limit)

    try:
        while True:
            fetch_limit = limit - total_fetched if limit else 50
            res = Feedback().list(offset=offset, limit=fetch_limit, task_id=task_id)
            new_data = res.json().get("data", [])
            if total_feedback == 0:
                total_feedback = res.json().get("total", 0)
            if not limit:
                limit = total_feedback
            feedback_data.extend(new_data)

            current_fetched = len(new_data)
            total_fetched += current_fetched
            offset += current_fetched
            if total_fetched >= limit or total_fetched >= total_feedback:
                break
    except Exception as e:
        click.echo(f"Error fetching feedback {e}")
        if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
            click.echo(e.response.json()["error"])
        return []

    return feedback_data


@click.command()
@click.option(
    "--offset", default=0, type=int, help="The starting index from which to begin the feedback fetch. Defaults to 0."
)
@click.option(
    "--limit", default=25, type=int, help="The maximum number of feedback items to retrieve. Defaults to 25."
)
@click.option(
    "--task_id",
    default="",
    type=str,
    help="The specific Task ID to filter feedback. If not provided, feedback for all tasks will be fetched.",
)
def list_feedback(offset, limit, task_id):
    """
    List feedback based on the provided criteria. This command allows fetching feedback for a specific task or across all tasks,
    with control over the starting point and the number of items to retrieve.
    """
    feedback_data = _get_feedback_list(offset, limit, task_id)
    data_for_table = []
    for feedback in feedback_data:
        data_for_table.append(
            {
                "id": feedback["id"],
                "task_name": feedback["task_name"],
                "feedback": json.dumps(feedback["json_values"], ensure_ascii=False),
                "matched_completion_ids": ",".join(feedback["matched_completion_ids"]),
            }
        )
    table = Table(title="Feedback")
    table.add_column("ID")
    table.add_column("Task Name")
    table.add_column("Feedback")
    table.add_column("Completion ID")

    for item in data_for_table:
        table.add_row(item["id"], item["task_name"], item["feedback"], item["matched_completion_ids"])
    console = Console()
    console.print(table)
    console.print(f"Total feedback: {len(feedback_data)}")


@click.command()
@click.option("--id", required=True, help="Get feedback by ID")
def get_feedback(id):
    """
    Get feedback based on provided ID.
    """
    try:
        res = Feedback().get(id)
    except Exception as e:
        click.echo(f"Error fetching feedback {e}")
        if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
            click.echo(e.response.json()["error"])
        return
    console = Console()
    feedback = json.dumps(res.json(), indent=4)
    console.print_json(feedback)


@click.command()
@click.option(
    "--offset",
    default=0,
    help="The starting index from which to begin the feedback fetch. Leave empty to start from the beginning.",
)
@click.option(
    "--limit", default="", help="The maximum number of feedback items to retrieve. Leave empty to retrieve all."
)
@click.option(
    "--task_id",
    default="",
    type=str,
    help="The specific Task ID to filter feedback. If not provided, feedback for all tasks will be fetched.",
)
@click.option(
    "--file",
    "-f",
    type=str,
    required=False,
    help="Path to the file where the feedback will be saved. The feedback data is saved in JSON Lines (jsonl) format. If not specified, feedback will be printed to stdout.",
)
def download_feedback(offset, limit, task_id, file):
    """
    Download feedback based on the provided criteria. This command allows fetching feedback for a specific task or across all tasks,
    with control over the starting point and the number of items to retrieve.
    """
    feedback_data = _get_feedback_list(offset, limit, task_id)

    console = Console()
    if not file:
        for feedback in feedback_data:
            console.print_json(json.dumps(feedback, indent=4))
        return

    with open(file, "w") as f:
        console.print(f"Saving feedback to {file}")
        for feedback in tqdm(feedback_data):
            f.write(json.dumps(feedback) + "\n")
