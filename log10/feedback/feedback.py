import logging

import httpx

from log10._httpx_utils import _try_get, _try_post_graphql_request
from log10.llm import Log10Config
from log10.utils import safe_get


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

    def list(self, offset: int = 0, limit: int = 50, task_id: str = "", filter: str = "") -> httpx.Response:
        if filter:
            return self.list_v2(page=round(offset / limit) + 1, limit=limit, task_id=task_id, filter=filter)

        base_url = self._log10_config.url
        api_url = "/api/v1/feedback"
        url = f"{base_url}{api_url}?organization_id={self._log10_config.org_id}&offset={offset}&limit={limit}&task_id={task_id}"
        logger.debug(f"Fetching feedback from url: {url}")

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

    def list_v2(
        self, page: int = 1, limit: int = 50, task_id: str | None = None, filter: str | None = None
    ) -> httpx.Response:
        query = """
        query OrganizationFeedback($id: String!, $filter: String, $taskId: String, $page: Int, $limit: Int) {
            organization(id: $id) {
                id
                feedbackV2(filter: $filter, taskId: $taskId, page: $page, limit: $limit) {
                    pageInfo{
                        totalCount
                        currentPage
                    }
                    nodes {
                        id
                        jsonValues
                        task {
                            id
                            name
                        }
                        completions {
                            id
                        }
                    }
                }
            }
        }
        """

        variables = {
            "id": self._log10_config.org_id,
            "taskId": task_id,
            "filter": filter,
            "page": page,
            "limit": limit,
        }
        logger.debug(f"Fetching feedback with variables: {variables}")

        response = _try_post_graphql_request(query, variables)

        if response is None:
            logger.error("Failed to get feedback")
            return None

        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

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


def _format_graphql_node(node):
    return {
        "id": node["id"],
        "json_values": node["jsonValues"],
        "task_id": node["task"]["id"],
        "task_name": node["task"]["name"],
        "matched_completion_ids": [c["id"] for c in node["completions"]],
    }


def _get_feedback_list_graphql(task_id, filter, page=1, limit=50):
    feedback_data = []
    current_page = page
    limit = int(limit)

    try:
        while True:
            res = Feedback().list_v2(page=current_page, limit=limit, task_id=task_id, filter=filter)
            new_data = safe_get(res, ["data", "organization", "feedbackV2", "nodes"])

            if new_data is None:
                logger.warning("Warning: Expected data structure not found in API response.")
                break

            feedback_data.extend(new_data)

            current_fetched = len(new_data)
            current_page += 1

            if current_fetched <= limit:
                break
    except Exception as e:
        logger.error(f"Error fetching feedback {e}")
        if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
            logger.error(e.response.json()["error"])
        return []

    return [_format_graphql_node(item) for item in feedback_data]
