import json
import logging
import random
from types import FunctionType

import httpx

from log10._httpx_utils import _try_post_graphql_request
from log10.completions.completions import _get_completion
from log10.feedback.feedback import _get_feedback_list
from log10.llm import Log10Config
from log10.load import log10_session


try:
    from log10.feedback._summary_feedback_utils import flatten_messages, summary_feedback_llm_call

    Magentic_imported = True
except ImportError:
    Magentic_imported = False


logger = logging.getLogger("LOG10")
logger.setLevel(logging.INFO)

_log10_config = Log10Config()


class AutoFeedbackICL:
    """
    Generate feedback with in context learning (ICL) based on existing feedback.
    """

    _examples: list[dict] = []
    _predict_func: FunctionType = None

    def __init__(
        self,
        task_id: str,
        num_samples: int = 5,
        predict_func: FunctionType = summary_feedback_llm_call if Magentic_imported else None,
    ):
        if not Magentic_imported:
            raise ImportError(
                "Log10 feedback predict requires magentic package. Please install using 'pip install log10-io[autofeedback_icl]'"
            )
        self.num_samples = num_samples
        self.task_id = task_id
        self._predict_func = predict_func

    def _get_examples(self):
        logger.info(f"Getting {self.num_samples} feedback for task {self.task_id}")
        feedback_data = _get_feedback_list(offset=0, limit="", task_id=self.task_id)
        assert feedback_data, f"No feedback found for task {self.task_id}."
        assert (
            len(feedback_data) >= self.num_samples
        ), f"Insufficient feedback for task {self.task_id}, found {len(feedback_data)} feedback. Sample size {self.num_samples}."
        sampled_feedback = random.sample(feedback_data, self.num_samples)
        few_shot_examples = []
        for fb in sampled_feedback:
            feedback_values = fb["json_values"]
            completion_id = fb["matched_completion_ids"][0]
            try:
                res = _get_completion(completion_id)
            except Exception as e:
                print(e)
                continue
            completion = res.json()["data"]
            fm = flatten_messages(completion)

            few_shot_examples.append(
                {
                    "completion_id": completion_id,
                    "prompt": fm["prompt"],
                    "response": fm["response"],
                    "feedback": json.dumps(feedback_values),
                }
            )
        logger.info(f"Sampled completion ids: {[d['completion_id'] for d in few_shot_examples]}")
        return few_shot_examples

    def predict(self, text: str = None, completion_id: str = None) -> str:
        if not self._examples:
            self._examples = self._get_examples()

        # Here assumps the completion is summary, prompt is article, response is summary
        if completion_id and not text:
            completion = _get_completion(completion_id)
            pr = flatten_messages(completion.json()["data"])
            text = json.dumps(pr)

        logger.info(f"{text=}")

        predict_func_name = self._predict_func.__name__
        logger.info(f"Using predict llm_call: {predict_func_name}")
        with log10_session(tags=["autofeedback_icl", predict_func_name]):
            ret = self._predict_func(examples="\n".join([str(d) for d in self._examples]), prompt=text)
        return ret


def get_autofeedback(completion_id: str) -> httpx.Response:
    query = """
    query OrganizationCompletion($orgId: String!, $id: String!) {
        organization(id: $orgId) {
            completion(id: $id) {
                id
                autoFeedback {
                    id
                    status
                    jsonValues
                    comment
                }
            }
        }
    }
    """

    variables = {"orgId": _log10_config.org_id, "id": completion_id}

    response = _try_post_graphql_request(query, variables)

    if response is None:
        logger.error(f"Failed to get auto feedback for completion {completion_id}")
        return None

    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()
