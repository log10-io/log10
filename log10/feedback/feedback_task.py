import click
import logging

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
        headers = {"x-log10-token": self._log10_config.token, "Content-Type": "application/json"}
        json_payload["organization_id"] = self._log10_config.org_id
        try:
            res = self._http_client.post(
                self._log10_config.url + url, headers=headers, json=json_payload
            )
            res.raise_for_status()
            return res
        except Exception as e:
            logger.error(e)
            raise

    def create(self, name: str, task_schema: dict) -> httpx.Response:
        """
        Example:
        >>> from log10.feedback.feedback_task import FeedbackTask
        >>> feedback_task = FeedbackTask()
        >>> task = feedback_task.create(name="summarization", task_schema={...})
        """
        json_payload = {"name": name, "task_schema": task_schema}
        res = self._post_request(self.feedback_task_create_url, json_payload)
        return res

# create a cli interface for FeebackTask.create function
@click.command()
@click.option("--name", help="Name of the task")
@click.option("--task_schema", help="Task schema")
def create_feedback_task(name, task_schema):
    fb_task = FeedbackTask()
    task = fb_task.create(name=name, task_schema=task_schema)
    print(task)
