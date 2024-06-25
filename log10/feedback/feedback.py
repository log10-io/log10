import logging

import httpx

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
        logger.error(f"Error fetching feedback {e}")
        if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
            logger.error(e.response.json()["error"])
        return []

    return feedback_data
