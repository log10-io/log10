import logging

import httpx
from dotenv import load_dotenv

from log10._httpx_utils import _try_get
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
