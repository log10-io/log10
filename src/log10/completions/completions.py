import json
import logging
import time
from typing import List, Optional
from uuid import uuid4

import click
import httpx
import openai
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage

from log10._httpx_utils import _try_get
from log10.llm import Log10Config
from log10.load import log10_tags, tags_var, with_log10_tags


logging.basicConfig(
    format="[%(asctime)s - %(name)s - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger("LOG10")
logger.setLevel(logging.INFO)


_log10_config = Log10Config()


def _get_completion(id: str) -> httpx.Response:
    url = f"{_log10_config.url}/api/completions/{id}?organization_id={_log10_config.org_id}"
    return _try_get(url)


def _get_tag_id(tag: str) -> str:
    url = f"{_log10_config.url}/api/tags/search?organization_id={_log10_config.org_id}&query={tag}"
    res = _try_get(url)
    data = res.json()["data"]
    if not data:
        return []

    if len(data) == 1:
        return data[0]["id"]
    else:
        for item in data:
            if item["name"] == tag:
                return item["id"]
        return []


def _get_tag_ids(tags):
    tag_ids = []
    for tag in [t for t in tags.split(",") if t]:
        tag_id = _get_tag_id(tag)
        if tag_id:
            tag_ids.append(tag_id)
        else:
            raise SystemExit(f"Cannot found tag: {tag}.")

    tag_ids_str = ",".join(tag_ids)
    return tag_ids_str


def _get_completions_url(limit, offset, tags, from_date, to_date, base_url, org_id, printout=True):
    tag_ids_str = _get_tag_ids(tags) if tags else ""
    if tag_ids_str and printout:
        print(f"Filter with tags: {tags}")

    date_range = _get_valid_date_range(from_date, to_date)
    if date_range and printout:
        print(f"Filter with created date: {date_range['from'][:10]} to {date_range['to'][:10]}")

    url = f"{base_url}/api/completions?organization_id={org_id}&offset={offset}&limit={limit}&tagFilter={tag_ids_str}&createdFilter={json.dumps(date_range)}&sort=created_at&desc=true&ids="
    return url


def _get_valid_date_range(from_date, to_date):
    if not from_date and not to_date:
        return {}

    if from_date is None or to_date is None:
        raise click.UsageError("Both --from and --to must be set together.")

    if from_date >= to_date:
        raise click.UsageError(f"from_date {from_date} must be earlier than to_date {to_date}")

    parsed_from_date = from_date.replace(hour=8).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    parsed_to_date = to_date.replace(hour=8).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    date_range = {"from": parsed_from_date, "to": parsed_to_date}
    return date_range


def _get_llm_repsone(
    model: str,
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 512,
    top_p: float = 1.0,
):
    ret = {"content": "", "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "duration": 0.0}

    start_time = time.perf_counter()
    if "gpt-4" in model or "gpt-3.5" in model:
        from log10.load import OpenAI

        client = OpenAI()
        response = client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p
        )
        ret["content"] = response.choices[0].message.content
        ret["usage"] = response.usage.model_dump()
    elif "claude-3" in model:
        from log10.load import Anthropic

        system_messages = [m["content"] for m in messages if m["role"] == "system"]
        other_messages = [m for m in messages if m["role"] != "system"]
        system_prompt = ("\n").join(system_messages)

        client = Anthropic()
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=other_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        ret["content"] = response.content[0].text
        ret["usage"]["prompt_tokens"] = response.usage.input_tokens
        ret["usage"]["completion_tokens"] = response.usage.output_tokens
        ret["usage"]["total_tokens"] = response.usage.input_tokens + response.usage.output_tokens
    elif "mistral" in model:
        import mistralai
        from mistralai.client import MistralClient

        from log10.load import log10

        log10(mistralai)

        client = MistralClient()
        response = client.chat(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p
        )
        ret["content"] = response.choices[0].message.content
        ret["usage"] = response.usage.model_dump()
    else:
        raise ValueError(f"Model {model} not supported.")
    ret["duration"] = int((time.perf_counter() - start_time) * 1000)

    return ret


def _compare(models: list[str], messages: dict, temperature: float = 0.2, max_tokens: float = 256, top_p: float = 1.0):
    ret = {}
    if models:
        for model in models:
            print(f"Running {model}")
            response = _get_llm_repsone(
                model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )

            ret[model] = response
    return ret


_OPENAI_SUPPORTED_MODELS = [
    "gpt-4o",
    "gpt-4o-2024-05-13",
    "gpt-4o-2024-08-06",
    "gpt-4o-mini",
    "gpt-4o-mini-2024-07-18",
    "gpt-4-turbo",
    "gpt-4-turbo-2024-04-09",
    "gpt-4-0125-preview",
    "gpt-4-turbo-preview",
    "gpt-4-1106-preview",
    "gpt-4",
    "gpt-4-0314",
    "gpt-4-0613",
    "gpt-4-32k",
    "gpt-4-32k-0314",
    "gpt-4-32k-0613",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-0301",
    "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-16k-0613",
]


_ANTHROPIC_SUPPORTED_MODELS = [
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]

_MISTRAL_SUPPORTED_MODELS = [
    "mistral-large-latest",
    "open-mistral-nemo",
]

_SUPPORTED_MODELS = _OPENAI_SUPPORTED_MODELS + _ANTHROPIC_SUPPORTED_MODELS + _MISTRAL_SUPPORTED_MODELS


def _check_model_support(model: str) -> bool:
    # check openai fine-tuned models
    # e.g. ft:gpt-3.5-turbo-0125:log10::9Q1qGLY2
    if model.startswith("ft:"):
        base_model = model.split(":")[1]
        if base_model in _OPENAI_SUPPORTED_MODELS:
            ft_models = [m.id for m in openai.models.list().data if m.id.startswith("ft:")]
            return model in ft_models

    # TODO check other fine-tuned models

    return model in _SUPPORTED_MODELS


def _get_current_unix_timestamp() -> int:
    return int(time.time())


class Completions:
    completions_path = "/api/completions"
    v1_completions_path = "/api/v1/completions"

    def __init__(self, log10_config: Log10Config = None):
        self._log10_config = log10_config or Log10Config()
        self._http_client = httpx.Client()
        self._http_client.headers = {
            "x-log10-token": self._log10_config.token,
            "x-log10-organization-id": self._log10_config.org_id,
            "Content-Type": "application/json",
        }

        self.org_id = self._log10_config.org_id
        self.base_url = self._log10_config.url
        self.url = f"{self.base_url}{self.completions_path}?organization_id={self.org_id}"

    def _get_completions(
        self,
        offset: int,
        limit: int,
        timeout: int,
        tag_names: Optional[List[str]] = None,
        from_date: click.DateTime = None,
        to_date: click.DateTime = None,
        printout: bool = True,
    ) -> List[dict]:
        url = _get_completions_url(limit, offset, tag_names, from_date, to_date, self.base_url, self.org_id)
        # Fetch completions
        response = _try_get(url, timeout)

        if response.status_code != 200:
            logger.error(f"Error: {response.json()}")
            return

        completions = response.json()
        return completions["data"]

    @with_log10_tags(["MOCK_CHAT_COMPLETIONS"])
    def mock_chat_completions(
        self, model: str, messages: list[dict], response_content: str, tags: list[str] = None
    ) -> ChatCompletion:
        """
        Mock a chat completion and log it with Log10.

        Args:
            model (str): The name of the model to mock (e.g., "gpt-3.5-turbo").
            messages (list[dict]): A list of message dictionaries, each containing 'role' and 'content'.
            response_content (str): The content of the simulated assistant's response.
            tags (list[str], optional): Additional tags to include with the log entry.

        Returns:
            ChatCompletion: openai chat completion object

        Raises:
            httpx.HTTPError: If there's an error communicating with the Log10 API.
            Exception: For any other unexpected errors during the process.

        Example:
            >>> from log10.completions import Completions
            >>> completions = Completions()
            >>> model = "gpt-4o"
            >>> messages = [
            ...     {"role": "system", "content": "You are a helpful assistant."},
            ...     {"role": "user", "content": "What's the capital of France?"}
            ... ]
            >>> response_content = "The capital of France is Paris."
            >>> result = completions.mock_chat_completions(
            ...     model=model,
            ...     messages=messages,
            ...     response_content=response_content,
            ...     tags=["geography", "xdoctest"]
            ... )
            >>> print(f"Assistant's response: {result.choices[0].message.content}")
            Assistant's response: The capital of France is Paris.
            >>> print(f"Model used: {result.model}")
            Model used: gpt-4o

        Note:
            This method adds the tag "MOCK_CHAT_COMPLETIONS" automatically to distinguish
            mocked completions from real ones in your logs.
        """
        completion_id = str(uuid4())
        v1_completions_post_url = f"{self.base_url}{self.v1_completions_path}/{completion_id}"

        # current_tags = tags_var.get()
        # if tags:
        #     current_tags.extend(tags)

        # todo(wenzhe): support tool_calls, json schema etc in request
        response = ChatCompletion(
            id="chatcmpl-" + completion_id,
            object="chat.completion",
            created=_get_current_unix_timestamp(),
            model=model,
            system_fingerprint="log10_mock_chat_completion",
            choices=[
                Choice(
                    index=0,
                    message=ChatCompletionMessage(role="assistant", content=response_content),
                    finish_reason="stop",
                )
            ],
            usage=CompletionUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )

        # exclude None vals in message, otherwise 400 error
        # cannot exclude none for the full response_dict, found 'logprobs' key is required but would be removed it's None.
        response_dict = response.model_dump()
        response_dict["choices"][0]["message"] = response.choices[0].message.model_dump(exclude_none=True)

        with log10_tags(tags):
            data = {
                "duration": 0,
                "id": completion_id,
                "kind": "chat",
                "organization_id": self.org_id,
                "stack_trace": [],
                "status": "finished",
                "tags": tags_var.get(),
                "request": {
                    "messages": messages,
                    "model": model,
                },
                "response": response_dict,
            }

        try:
            res = self._http_client.post(v1_completions_post_url, json=data)
            res.raise_for_status()
            return response
        except httpx.HTTPError as http_err:
            if "401" in str(http_err):
                logger.error(
                    "Failed anthorization. Please verify that LOG10_TOKEN and LOG10_ORG_ID are set correctly and try again."
                    + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
                )
            else:
                logger.error(f"Failed with error: {http_err}")
        except Exception as err:
            logger.error(f"Failed to insert in log10: {data} with error {err}.", exc_info=True)
