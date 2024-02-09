import click
import logging

import httpx
from dotenv import load_dotenv

from log10.llm import Log10Config


# def create(name: str, task_schema: dict) -> httpx.Response:
#     """
#     Example:
#     >>> from log10.feedback import feedback, feedback_task
#     >>> task = feedback_task.create(name="summarization", task_schema={...})
#     >>> task_id = task.id
#     >>> fb = feedback.create(task_id=task_id, rate={...})
#     """

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

    def create(self, task_id: str, rate: dict) -> httpx.Response:
        """
        Example:
        >>> from log10.feedback import Feedback
        >>> fb = Feedback()
        >>> fb.create(task_id="task_id", rate={...})
        """
        json_payload = {"task_id": task_id, "rate": rate}
        res = self._post_request(self.feedback_create_url, json_payload)
        return res

@click.command()
@click.option("--task_id", help="Task ID")
@click.option("--rate", help="Rate in JSON format")
def create_feedback(task_id, rate):
    fb = Feedback()
    feedback = fb.create(task_id=task_id, rate=rate)
    print(feedback)
