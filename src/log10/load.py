import asyncio
import contextvars
import functools
import inspect
import json
import logging
import os
import queue
import threading
import time
import traceback
import uuid
from contextlib import contextmanager
from copy import deepcopy
from importlib.metadata import version

import backoff
import requests
from dotenv import load_dotenv
from packaging.version import parse


load_dotenv()

logging.basicConfig(
    format="[%(asctime)s - %(name)s - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger("LOG10")

url = os.environ.get("LOG10_URL")
token = os.environ.get("LOG10_TOKEN")
org_id = os.environ.get("LOG10_ORG_ID")


# log10, bigquery
target_service = os.environ.get("LOG10_DATA_STORE", "log10")

if target_service == "bigquery":
    from log10.bigquery import initialize_bigquery

    bigquery_client, bigquery_table = initialize_bigquery()
    from datetime import datetime, timezone
elif target_service is None:
    target_service = "log10"  # default to log10


def is_openai_v1() -> bool:
    """Return whether OpenAI API is v1 or more."""
    _version = parse(version("openai"))
    return _version.major >= 1


def func_with_backoff(func, *args, **kwargs):
    if func.__module__ != "openai" or is_openai_v1():
        return func(*args, **kwargs)

    import openai

    retry_errors = (
        openai.error.APIConnectionError,
        openai.error.APIError,
        openai.error.RateLimitError,
        openai.error.ServiceUnavailableError,
        openai.error.Timeout,
    )

    @backoff.on_exception(backoff.expo, retry_errors)
    def _func_with_backoff(func, *args, **kwargs):
        return func(*args, **kwargs)

    return _func_with_backoff(func, *args, **kwargs)


# todo: should we do backoff as well?
def post_request(url: str, json_payload: dict = {}) -> requests.Response:
    headers = {"x-log10-token": token, "Content-Type": "application/json"}
    json_payload["organization_id"] = org_id
    try:
        timeout = int(os.environ.get("LOG10_REQUESTS_TIMEOUT", 10))
        assert isinstance(timeout, int)
        res = requests.post(url, headers=headers, json=json_payload, timeout=timeout)
        # raise_for_status() will raise an exception if the status is 4xx, 5xxx
        res.raise_for_status()

        logger.debug(f"HTTP request: POST {url} {res.status_code}\n{json.dumps(json_payload, indent=4)}")
        return res
    except requests.Timeout:
        logger.error("HTTP request: POST Timeout")
        raise
    except requests.ConnectionError:
        logger.error("HTTP request: POST Connection Error")
        raise
    except requests.HTTPError as e:
        logger.error(f"HTTP request: POST HTTP Error - {e}")
        raise
    except requests.RequestException as e:
        logger.error(f"HTTP request: POST Request Exception - {e}")
        raise


post_session_request = functools.partial(post_request, url + "/api/sessions", {})


def get_session_id():
    id = str(uuid.uuid4())
    logger.debug(f"Session ID: {id}")
    return id


#
# Context variables
#
session_id_var = contextvars.ContextVar("session_id", default=get_session_id())
last_completion_response_var = contextvars.ContextVar("last_completion_response", default=None)
tags_var = contextvars.ContextVar("tags", default=[])


def get_log10_session_tags():
    return tags_var.get()


class TagsManager:
    def __init__(self, tags: list[str] = None):
        self.tags = self._validate_tags(tags) or []

    @staticmethod
    def _validate_tags(tags: list[str] | None) -> list[str]:
        if tags is None:
            return None

        if not isinstance(tags, list):
            logger.warning(
                f"Invalid tags format: expected list, got {type(tags).__name__}. Tags will be omitted from the log."
            )
            return None

        validated_tags = []
        for tag in tags:
            if not isinstance(tag, str):
                logger.warning(
                    f"Invalid tag type: expected str, got {type(tag).__name__}. This tag will be omitted: {repr(tag)}"
                )
                continue
            validated_tags.append(tag)
        return validated_tags

    def _enter(self):
        current_tags = tags_var.get()
        new_tags = current_tags + self.tags

        self.tags_token = tags_var.set(new_tags)
        return self.tags_token

    def _exit(self, exc_type, exc_value, traceback):
        tags_var.reset(self.tags_token)

    def __enter__(self):
        return self._enter()

    def __exit__(self, exc_type, exc_value, traceback):
        self._exit(exc_type, exc_value, traceback)

    async def __aenter__(self):
        return self._enter()

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._exit(exc_type, exc_value, traceback)


class log10_session:
    def __init__(self, tags=None):
        self.tags_manager = TagsManager(tags)

    def _enter(self):
        self.session_id_token = session_id_var.set(get_session_id())
        self.last_completion_response_token = last_completion_response_var.set(None)
        self.tags_manager._enter()

        return self

    def _exit(self, exc_type, exc_value, traceback):
        session_id_var.reset(self.session_id_token)
        last_completion_response_var.reset(self.last_completion_response_token)
        self.tags_manager._exit(exc_type, exc_value, traceback)

    def __enter__(self):
        return self._enter()

    def __exit__(self, exc_type, exc_value, traceback):
        self._exit(exc_type, exc_value, traceback)
        return

    async def __aenter__(self):
        return self._enter()

    async def __aexit__(self, exc_type, exc_value, traceback):
        self._exit(exc_type, exc_value, traceback)
        return

    def last_completion_url(self):
        if last_completion_response_var.get() is None:
            return None
        response = last_completion_response_var.get()

        # organizationSlug will not be returned from httpx hook
        if not response.get("organizationSlug", ""):
            return None
        return f'{url}/app/{response["organizationSlug"]}/completions/{response["completionID"]}'

    def last_completion_id(self):
        if last_completion_response_var.get() is None:
            return None
        response = last_completion_response_var.get()
        return response["completionID"]


@contextmanager
def log10_tags(tags: list[str]):
    """
    A context manager that adds tags to the current session.
    This could be used with log10_session to add extra tags to the session.
    Example:
    >>> from log10.load import log10_tags
    >>> with log10_tags(["tag1", "tag2"]):
    >>>     completion = client.chat.completions.create(
    >>>         model="gpt-4o",
    >>>         messages=[
    >>>             {
    >>>                 "role": "user",
    >>>                 "content": "Hello?",
    >>>             },
    >>>         ],
    >>>     )
    >>>     print(completion.choices[0].message)
    """
    tags_manager = TagsManager(tags)
    with tags_manager:
        yield


def with_log10_tags(tags: list[str]):
    """
    A decorator that adds tags to a function call.
    Example:
    >>> from log10.load import with_log10_tags
    >>> @with_log10_tags(["decorator-tags", "decorator-tags-2"])
    >>> def completion_with_tags():
    >>>     completion = client.chat.completions.create(
    >>>         model="gpt-4o",
    >>>         messages=[
    >>>             {
    >>>                 "role": "user",
    >>>                 "content": "Hello?",
    >>>             },
    >>>         ],
    >>>     )
    >>>     print(completion.choices[0].message)
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with log10_tags(tags):
                return func(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def timed_block(block_name):
    if DEBUG:
        start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed_time = time.perf_counter() - start_time
            logger.debug(f"TIMED BLOCK - {block_name} took {elapsed_time:.6f} seconds to execute.")
    else:
        yield


def log_url(res, completionID):
    output = res.json()
    organizationSlug = output["organizationSlug"]
    full_url = url + "/app/" + organizationSlug + "/completions/" + completionID
    logger.debug(f"Completion URL: {full_url}")


async def log_async(completion_url, log_row):
    res = None
    try:
        res = post_request(completion_url)
        completionID = res.json().get("completionID", None)
        organizationSlug = res.json().get("organizationSlug", None)

        if completionID is None:
            logger.warning("LOG10: failed to get completionID from log10. Skipping log.")
            return None

        if DEBUG:
            log_url(res, completionID)

        if target_service == "log10":
            try:
                _url = f"{completion_url}/{completionID}"
                res = post_request(_url, log_row)
            except Exception as e:
                logger.warning(f"LOG10: failed to log: {e}. Skipping")
                return None

        elif target_service == "bigquery":
            pass
            # NOTE: We only save on request finalization.

    except Exception as e:
        logger.warning(f"LOG10: failed to log: {e}. Skipping")
        return None

    return {"completionID": completionID, "organizationSlug": organizationSlug}


def run_async_in_thread(completion_url, log_row, result_queue):
    result = asyncio.run(log_async(completion_url=completion_url, log_row=log_row))
    result_queue.put(result)


def log_sync(completion_url, log_row):
    completionID = None

    try:
        res = post_request(completion_url)
        last_completion_response_var.set(res.json())
        completionID = res.json().get("completionID", None)

        if completionID is None:
            logger.warning("LOG10: failed to get completionID from log10. Skipping log.")
            return None

        if DEBUG:
            log_url(res, completionID)
        _url = f"{completion_url}/{completionID}"
        res = post_request(_url, log_row)
    except Exception as e:
        logger.warning(f"LOG10: failed to get completionID from log10: {e}")
        return None

    return completionID


class StreamingResponseWrapper:
    """
    Wraps a streaming response object to log the final result and duration to log10.

    Openai V1 example:
    Example:
        >>> from log10.load import OpenAI
        >>> client = OpenAI()
        >>> response = client.chat.completions.create(
        >>>     model="gpt-3.5-turbo",
        >>>     messages=[{"role": "user", "content": "Count to 200"}],
        >>>     temperature=0,
        >>>     stream=True,
        >>> )
        >>> for chunk in response:
        >>>     content = chunk.choices[0].delta.content
        >>>     if content:
        >>>         print(content, end="", flush=True)
        >>> print("")
    """

    def __init__(self, completion_url, completionID, response, partial_log_row):
        self.completionID = completionID
        self.completion_url = completion_url
        self.partial_log_row = partial_log_row
        self.response = response
        self.final_result = ""  # Store the final result
        self.function_name = ""
        self.function_arguments = ""
        self.start_time = time.perf_counter()
        self.gpt_id = None
        self.model = None
        self.finish_reason = None
        self.usage = None
        self.tool_calls = []

    def __iter__(self):
        return self

    def __next__(self):
        try:
            chunk = next(self.response)
            if hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
                # Here you can intercept and modify content if needed
                content = chunk.choices[0].delta.content
                self.final_result += content  # Save the content
                # Yield the original or modified content

                self.model = chunk.model
                self.gpt_id = chunk.id

                # for mistral stream
                if chunk.choices[0].finish_reason:
                    self.finish_reason = chunk.choices[0].finish_reason

                # for mistral stream
                if getattr(chunk, "usage", None):
                    self.usage = chunk.usage
            elif chunk.choices[0].delta.function_call:
                arguments = chunk.choices[0].delta.function_call.arguments
                self.function_arguments += arguments
                if not self.function_name and chunk.choices[0].delta.function_call.name:
                    self.function_name = chunk.choices[0].delta.function_call.name
            elif tc := chunk.choices[0].delta.tool_calls:
                # self.tool_calls is a list
                if tc[0].id:
                    self.tool_calls.append(tc[0].dict())
                elif tc[0].function.arguments:
                    self.tool_calls[tc[0].index]["function"]["arguments"] += tc[0].function.arguments
            elif chunk.choices[0].finish_reason:
                self.finish_reason = chunk.choices[0].finish_reason

                # in Magentic stream, this is reached instead of StopIteration
                if self.finish_reason == "stop":
                    raise StopIteration

            return chunk
        except StopIteration as se:
            # Log the final result
            # Create fake response for openai format.
            if self.final_result:
                response = {
                    "id": self.gpt_id,
                    "object": "completion",
                    "model": self.model,
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": self.finish_reason,
                            "message": {
                                "role": "assistant",
                                "content": self.final_result,
                            },
                        }
                    ],
                }
            elif self.function_arguments:
                response = {
                    "id": self.gpt_id,
                    "object": "completion",
                    "model": self.model,
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": self.finish_reason,
                            "function_call": {
                                "name": self.function_name,
                                "arguments": self.function_arguments,
                            },
                        }
                    ],
                }
            elif self.tool_calls:
                response = {
                    "id": self.gpt_id,
                    "object": "completion",
                    "model": self.model,
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": self.finish_reason,
                            "message": {
                                "content": "",
                                "role": "assistant",
                                "tool_calls": self.tool_calls,
                            },
                        }
                    ],
                }
            if self.usage:
                response["usage"] = self.usage.dict()
            self.partial_log_row["response"] = json.dumps(response)
            self.partial_log_row["duration"] = int((time.perf_counter() - self.start_time) * 1000)

            try:
                _url = f"{self.completion_url}/{self.completionID}"
                res = post_request(_url, self.partial_log_row)
                if res.status_code != 200:
                    logger.error(f"LOG10: failed to insert in log10: {self.partial_log_row} with error {res.text}")
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                logger.warning(f"LOG10: failed to log: {e}. Skipping")

            raise se


# Filter large images from messages, and replace with a text message saying "Image too large to display"
def filter_large_images(messages):
    for message in messages:
        # Content may be an array of fragments, of text and images.
        # If not, it's a single fragment.
        if isinstance(message.get("content"), list):
            new_content = []
            for fragment in message.get("content", ""):
                if fragment.get("type") == "image_url":
                    # If image is more than 4MB, replace with a text message
                    url = fragment.get("image_url", {}).get("url", "")
                    if url.startswith("data:image"):
                        if len(url) > 4e6:
                            new_content.append(
                                {
                                    "type": "text",
                                    "text": "Image too large to capture",
                                }
                            )
                        else:
                            new_content.append(fragment)
                    else:
                        new_content.append(fragment)
                else:
                    new_content.append(fragment)
            message["content"] = new_content

    return messages


def flatten_messages(messages):
    flat_messages = []
    for message in messages:
        if isinstance(message, dict):
            flat_messages.append(message)
        else:
            flat_messages.append(message.model_dump())
    return flat_messages


def flatten_response(response):
    if "choices" in response:
        # May have to flatten, if not a dictionary
        if not isinstance(response.choices[0].message, dict):
            response.choices[0].message = response.choices[0].message.model_dump()

    return response


def _get_stack_trace():
    current_stack_frame = traceback.extract_stack()
    return [
        {
            "file": frame.filename,
            "line": frame.line,
            "lineno": frame.lineno,
            "name": frame.name,
        }
        for frame in current_stack_frame
    ]


def _init_log_row(func, *args, **kwargs):
    kwargs_copy = deepcopy(kwargs)

    log_row = {
        "status": "started",
        "orig_module": func.__module__,
        "orig_qualname": func.__qualname__,
        "stacktrace": json.dumps(_get_stack_trace()),
        "session_id": session_id_var.get(),
        "tags": tags_var.get(),
    }

    # in case the usage of load(openai) and langchain.ChatOpenAI
    if "api_key" in kwargs_copy:
        kwargs_copy.pop("api_key")

    # We may have to flatten messages from their ChatCompletionMessage with nested ChatCompletionMessageToolCall to json serializable format
    # Rewrite in-place
    if "messages" in kwargs_copy:
        kwargs_copy["messages"] = filter_large_images(flatten_messages(kwargs_copy["messages"]))

    # kind and request are set based on the module and qualname
    # request is based on openai schema
    if "anthropic" in func.__module__:
        logger.debug("Anthropic calls are patched via httpx client, should not reach here.")
    elif "vertexai" in func.__module__:
        if func.__name__ == "_send_message":
            # get model name save in ChatSession instance
            log_row["kind"] = "chat"
            chat_session_instance = inspect.currentframe().f_back.f_back.f_locals["self"]
            model_name = chat_session_instance._model._model_name.split("/")[-1]

            # TODO how to handle chat history
            # chat_history = chat_session_instance.history
            kwargs_copy.update(
                {
                    "model": model_name,
                    "messages": [{"role": "user", "content": kwargs_copy["content"]}],
                }
            )
            if kwargs_copy.get("generation_config"):
                for key, value in kwargs_copy["generation_config"].to_dict().items():
                    if key == "max_output_tokens":
                        kwargs_copy["max_tokens"] = value
                    else:
                        kwargs_copy[key] = value
                kwargs_copy.pop("generation_config")
    elif "lamini" in func.__module__:
        log_row["kind"] = "chat"
        kwargs_copy.update(
            {
                "model": args[1]["model_name"],
                "messages": [{"role": "user", "content": args[1]["prompt"]}],
            }
        )
    elif "mistralai" in func.__module__:
        log_row["kind"] = "chat"
    elif "openai" in func.__module__:
        from openai._utils._utils import strip_not_given

        kwargs_copy = strip_not_given(kwargs_copy)
        kind = "chat" if "chat" in func.__module__ else "completion"
        log_row["kind"] = kind
    elif "google.generativeai" in func.__module__:
        if func.__name__ == "send_message":
            log_row["kind"] = "chat"
            history_messages = []
            if system_instruction := args[0].model._system_instruction:
                history_messages.append({"role": "system", "content": system_instruction.parts[0].text})
            if history := args[0].history:
                for m in history:
                    role = "assistant" if m.role == "model" else "user"
                    content = m.parts[0].text
                    history_messages.append({"role": role, "content": content})

            history_messages.append({"role": "user", "content": args[1]})
            kwargs_copy.update(
                {
                    "model": args[0].model.model_name.split("/")[-1],
                    "messages": history_messages,
                }
            )
            if kwargs_copy.get("generation_config") and hasattr(kwargs_copy["generation_config"], "__dict__"):
                for key, value in kwargs_copy["generation_config"].__dict__.items():
                    if not value:
                        continue
                    if key == "max_output_tokens":
                        kwargs_copy["max_tokens"] = value
                    elif key == "stop_sequences":
                        kwargs_copy["stop"] = value
                    elif key in ["temperature", "top_p", "top_k"]:
                        kwargs_copy[key] = value
                kwargs_copy.pop("generation_config")

    log_row["request"] = json.dumps(kwargs_copy)

    return log_row


def intercepting_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        completion_url = url + "/api/completions"
        output = None
        result_queue = queue.Queue()

        try:
            log_row = _init_log_row(func, *args, **kwargs)

            with timed_block(sync_log_text + " call duration"):
                if USE_ASYNC:
                    threading.Thread(
                        target=run_async_in_thread,
                        kwargs={
                            "completion_url": completion_url,
                            "log_row": log_row,
                            "result_queue": result_queue,
                        },
                    ).start()
                else:
                    completionID = log_sync(completion_url=completion_url, log_row=log_row)

                    if completionID is None:
                        logger.warning("LOG10: failed to get completionID from log10. Skipping log.")
                        func_with_backoff(func, *args, **kwargs)
                        return

            start_time = time.perf_counter()
            output = func_with_backoff(func, *args, **kwargs)
            duration = time.perf_counter() - start_time
            logger.debug(f"TIMED BLOCK - LLM call duration: {duration}")
        except Exception as e:
            if USE_ASYNC:
                with timed_block("extra time spent waiting for log10 call"):
                    while result_queue.empty():
                        pass
                    result = result_queue.get()
                    completionID = result["completionID"]
                    last_completion_response_var.set(result)

            if completionID is None:
                logger.warning(f"LOG10: failed to get completionID from log10: {e}. Skipping log.")
                return

            logger.debug(f"LOG10: failed - {e}")
            # todo: change with openai v1 update
            if type(e).__name__ == "InvalidRequestError" and "This model's maximum context length" in str(e):
                failure_kind = "ContextWindowExceedError"
            else:
                failure_kind = type(e).__name__
            failure_reason = str(e)
            log_row["status"] = "failed"
            log_row["failure_kind"] = failure_kind
            log_row["failure_reason"] = failure_reason
            try:
                res = post_request(completion_url + "/" + completionID, log_row)
            except Exception as le:
                logger.warning(f"LOG10: failed to log: {le}. Skipping, but raising LLM error.")
            raise e
        else:
            # finished with no exceptions
            if USE_ASYNC:
                with timed_block("extra time spent waiting for log10 call"):
                    while result_queue.empty():
                        pass
                    result = result_queue.get()

                    if result is None:
                        return output

                    completionID = result.get("completionID")
                    last_completion_response_var.set(result)

            with timed_block("result call duration (sync)"):
                response = output
                # Adjust the Anthropic output to match OAI completion output
                if "anthropic" in func.__module__:
                    logger.debug("Anthropic calls are patched via httpx client, should not reach here.")

                elif "vertexai" in func.__module__:
                    response = output
                    reason = response.candidates[0].finish_reason.name
                    ret_response = {
                        "id": str(uuid.uuid4()),
                        "object": "chat.completion",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": str(reason).lower(),
                                "message": {
                                    "role": "assistant",
                                    "content": response.text,
                                },
                            }
                        ],
                    }
                    response_dict = response.to_dict()
                    tokens_usage = {
                        "prompt_tokens": response_dict["usage_metadata"]["prompt_token_count"],
                        "completion_tokens": response_dict["usage_metadata"]["candidates_token_count"],
                        "total_tokens": response_dict["usage_metadata"]["total_token_count"],
                    }
                    ret_response["usage"] = tokens_usage
                    response = ret_response
                elif "google.generativeai" in func.__module__:
                    ret_response = {
                        "id": str(uuid.uuid4()),
                        "object": "chat.completion",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": str(output.candidates[0].finish_reason.name).lower(),
                                "message": {
                                    "role": "assistant",
                                    "content": output.text,
                                },
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                        },
                    }
                    response = ret_response
                elif "openai" in func.__module__:
                    if type(output).__name__ == "Stream":
                        log_row["response"] = response
                        log_row["status"] = "finished"
                        return StreamingResponseWrapper(
                            completion_url=completion_url,
                            completionID=completionID,
                            response=response,
                            partial_log_row=log_row,
                        )
                    if type(output).__name__ == "LegacyAPIResponse":
                        response = json.loads(output.content)
                    else:
                        response = output.copy()
                        if "choices" in response:
                            response = flatten_response(response)
                elif "lamini" in func.__module__:
                    response = {
                        "id": str(uuid.uuid4()),
                        "object": "chat.completion",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": "stop",
                                "message": {
                                    "role": "assistant",
                                    "content": output["output"],
                                },
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 0,
                            "completion_tokens": 0,
                            "total_tokens": 0,
                        },
                    }
                elif "mistralai" in func.__module__:
                    if "stream" in func.__qualname__:
                        log_row["response"] = response
                        log_row["status"] = "finished"
                        return StreamingResponseWrapper(
                            completion_url=completion_url,
                            completionID=completionID,
                            response=response,
                            partial_log_row=log_row,
                        )
                    response = output.copy()

                if hasattr(response, "model_dump_json"):
                    response = response.model_dump_json()
                else:
                    response = json.dumps(response)

                log_row["status"] = "finished"
                log_row["duration"] = int(duration * 1000)
                log_row["response"] = response

                if target_service == "log10":
                    try:
                        _url = f"{completion_url}/{completionID}"
                        res = post_request(_url, log_row)
                        if res.status_code != 200:
                            logger.error(f"LOG10: failed to insert in log10: {log_row} with error {res.text}")
                    except Exception as e:
                        logger.warning(f"LOG10: failed to log: {e}. Skipping")

                elif target_service == "bigquery":
                    try:
                        log_row["id"] = str(uuid.uuid4())
                        log_row["created_at"] = datetime.now(timezone.utc).isoformat()
                        log_row["request"] = json.dumps(kwargs)

                        if func.__qualname__ == "Completion.create":
                            log_row["kind"] = "completion"
                        elif func.__qualname__ == "ChatCompletion.create":
                            log_row["kind"] = "chat"

                        log_row["orig_module"] = func.__module__
                        log_row["orig_qualname"] = func.__qualname__
                        log_row["session_id"] = session_id_var.get()

                        bigquery_client.insert_rows_json(bigquery_table, [log_row])

                    except Exception as e:
                        logging.error(f"LOG10: failed to insert in Bigquery: {log_row} with error {e}")

        return output

    return wrapper


def set_sync_log_text(USE_ASYNC=True):
    return "async" if USE_ASYNC else "sync"


def log10(module, DEBUG_=False, USE_ASYNC_=True):
    """Intercept and overload module for logging purposes
    support both openai V0 and V1, anthropic, vertexai, and mistralai

    Keyword arguments:
    module -- the module to be intercepted (e.g. openai)
    DEBUG_ -- whether to show log10 related debug statements via python logging (default False)
    USE_ASYNC_ -- whether to run in async mode (default True)

    Openai V0 example:
    Example:
        >>> # xdoctest: +SKIP
        >>> from log10.load import log10
        >>> import openai
        >>> log10(openai)
        >>> completion = openai.Completion.create(
        >>>     model="gpt-3.5-turbo-instruct",
        >>>     prompt="Once upon a time",
        >>>     max_tokens=32,
        >>> )
        >>> print(completion)

    Example:
        >>> # xdoctest: +SKIP
        >>> from log10.load import log10
        >>> import openai
        >>> log10(openai)
        >>> completion = openai.ChatCompletion.create(
        >>>     model="gpt-3.5-turbo",
        >>>     messages=[{"role": "user", "content": "Hello world"}],
        >>>     max_tokens=8,
        >>> )
        >>> print(completion)

    Example:
        >>> from log10.load import log10
        >>> from langchain.chat_models import ChatOpenAI
        >>> from langchain.schema import HumanMessage, SystemMessage
        >>> import openai
        >>> log10(openai)
        >>> llm = ChatOpenAI(
        >>>     model_name="gpt-3.5-turbo",
        >>>     temperature=0.5,
        >>> )
        >>> messages = [
        >>>     SystemMessage(content="You are a ping pong machine"),
        >>>     HumanMessage(content="Ping?")
        >>> ]
        >>> completion = llm.predict_messages(messages)
        >>> print(completion)

    Example:
        >>> from log10.load import log10
        >>> import anthropic
        >>> log10(anthropic)
        >>> from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
        >>> anthropic = Anthropic()
        >>> completion = anthropic.completions.create(
        >>>     model="claude-1",
        >>>     max_tokens_to_sample=32,
        >>>     prompt=f"{HUMAN_PROMPT} Hi, how are you? {AI_PROMPT}",
        >>> )
        >>> print(completion.completion)

    Example:
        >>> from log10.load import log10
        >>> import anthropic
        >>> from langchain.chat_models import ChatAnthropic
        >>> from langchain.schema import HumanMessage, SystemMessage
        >>> log10(anthropic)
        >>> llm = ChatAnthropic(model="claude-1", temperature=0.7)
        >>> messages = [
        >>>     SystemMessage(content="You are a ping pong machine"),
        >>>     HumanMessage(content="Ping?")
        >>> ]
        >>> completion = llm.predict_messages(messages)
        >>> print(completion)
    """
    global DEBUG, USE_ASYNC, sync_log_text
    DEBUG = DEBUG_ or os.environ.get("LOG10_DEBUG", False)
    logger.setLevel(logging.DEBUG if DEBUG else logging.WARNING)
    USE_ASYNC = USE_ASYNC_
    sync_log_text = set_sync_log_text(USE_ASYNC=USE_ASYNC)
    if DEBUG:
        httpx_logger = logging.getLogger("httpx")
        httpx_logger.setLevel(logging.DEBUG)

    # def intercept_nested_functions(obj):
    #     for name, attr in vars(obj).items():
    #         if callable(attr) and isinstance(attr, types.FunctionType):
    #             setattr(obj, name, intercepting_decorator(attr))
    #         elif inspect.isclass(attr):
    #             intercept_class_methods(attr)

    # def intercept_class_methods(cls):
    #     for method_name, method in vars(cls).items():
    #         if isinstance(method, classmethod):
    #             original_method = method.__func__
    #             decorated_method = intercepting_decorator(original_method)
    #             setattr(cls, method_name, classmethod(decorated_method))
    #         elif isinstance(method, (types.FunctionType, types.MethodType)):
    #             print(f"method:{method}")
    #             setattr(cls, method_name, intercepting_decorator(method))
    #         elif inspect.isclass(method):  # Handle nested classes
    #             intercept_class_methods(method)

    if getattr(module, "_log10_patched", False):
        logger.warning(f"{module.__name__} already patched. Skipping.")
        return

    if module.__name__ == "anthropic":
        from log10._httpx_utils import InitPatcher

        # Patch the AsyncAnthropic and Anthropic class
        InitPatcher(module, ["AsyncAnthropic", "Anthropic"])
    elif module.__name__ == "lamini":
        attr = module.api.utils.completion.Completion
        method = getattr(attr, "generate")
        setattr(attr, "generate", intercepting_decorator(method))
    elif module.__name__ == "mistralai" and getattr(module, "_log10_patched", False) is False:
        attr = module.client.MistralClient
        method = getattr(attr, "chat")
        setattr(attr, "chat", intercepting_decorator(method))

        method = getattr(attr, "chat_stream")
        setattr(attr, "chat_stream", intercepting_decorator(method))
    elif module.__name__ == "openai":
        openai_version = parse(version("openai"))
        global OPENAI_V1
        OPENAI_V1 = openai_version >= parse("1.0.0")

        # support for sync completions
        if OPENAI_V1:
            attr = module.resources.completions.Completions
            method = getattr(attr, "create")
            setattr(attr, "create", intercepting_decorator(method))

            attr = module.resources.chat.completions.Completions
            method = getattr(attr, "create")
            setattr(attr, "create", intercepting_decorator(method))

            # support for async completions
            from log10._httpx_utils import InitPatcher

            # Patch the AsyncOpenAI class
            InitPatcher(module, ["AsyncOpenAI"])
        else:
            attr = module.api_resources.completion.Completion
            method = getattr(attr, "create")
            setattr(attr, "create", intercepting_decorator(method))

            attr = module.api_resources.chat_completion.ChatCompletion
            mothod = getattr(attr, "create")
            setattr(attr, "create", intercepting_decorator(mothod))
    elif module.__name__ == "vertexai":
        # patch chat _send_message function
        attr = module.generative_models._generative_models.ChatSession
        method = getattr(attr, "_send_message")
        setattr(attr, "_send_message", intercepting_decorator(method))
    elif module.__name__ == "google.generativeai":
        # patch ChatSession send_message function
        attr = module.ChatSession
        method = getattr(attr, "send_message")
        setattr(attr, "send_message", intercepting_decorator(method))
    else:
        logger.warning(f"Unsupported module: {module.__name__}. Please contact us for support at support@log10.io.")

        # For future reference:
        # if callable(attr) and isinstance(attr, types.FunctionType):
        #     print(f"attr:{attr}")
        #     setattr(module, name, intercepting_decorator(attr))
        # elif inspect.isclass(attr):  # Check if attribute is a class
        #     intercept_class_methods(attr)
        # # else: # uncomment if we want to include nested function support
        # #     intercept_nested_functions(attr)

    module._log10_patched = True


if is_openai_v1():
    import openai
    from openai import OpenAI

    class OpenAI(OpenAI):
        """
        Example:
            >>> from log10.load import OpenAI
            >>> client = OpenAI(tags=["load_v1_test"])
            >>> completion = client.completions.create(model='gpt-3.5-turbo-instruct', prompt="Twice upon a time", max_tokens=32)
            >>> print(completion)

        Example:
            >>> from log10.load import OpenAI
            >>> client = OpenAI(tags=["load_v1_test"])
            >>> completion = client.chat.completions.create(
            >>>     model="gpt-3.5-turbo",
            >>>     messages=[{"role": "user", "content": "Hello world"}],
            >>> )
            >>> print(completion)
        """

        def __init__(self, *args, **kwargs):
            # check if tags is passed in
            if "tags" in kwargs:
                tags_var.set(kwargs.pop("tags"))
            super().__init__(*args, **kwargs)

            if not getattr(openai, "_log10_patched", False):
                log10(openai)
                openai._log10_patched = True


try:
    import anthropic
except ImportError:
    logger.debug("Anthropic not found. Skipping defining log10.load.Anthropic client.")
else:
    from anthropic import Anthropic, AsyncAnthropic

    class _Log10Anthropic:
        def __init__(self, *args, **kwargs):
            if "tags" in kwargs:
                tags_var.set(kwargs.pop("tags"))

            if not getattr(anthropic, "_log10_patched", False):
                log10(anthropic)
                anthropic._log10_patched = True

            super().__init__(*args, **kwargs)

    class Anthropic(_Log10Anthropic, Anthropic):
        """
        Example:
            >>> from log10.load import Anthropic
            >>> client = Anthropic(tags=["test", "load_anthropic"])
            >>> message = client.messages.create(
            ...     model="claude-3-haiku-20240307",
            ...     max_tokens=100,
            ...     temperature=0.9,
            ...     system="Respond only in Yoda-speak.",
            ...     messages=[{"role": "user", "content": "How are you today?"}],
            ... )
            >>> print(message.content[0].text)
        """

        pass

    class AsyncAnthropic(_Log10Anthropic, AsyncAnthropic):
        """
        Example:
            >>> import asyncio
            >>> from log10._httpx_utils import finalize
            >>> from log10.load import AsyncAnthropic
            >>> client = AsyncAnthropic(tags=["test", "async_anthropic"])
            >>> async def main() -> None:
            >>>     message = await client.messages.create(
            ...         model="claude-3-haiku-20240307",
            ...         max_tokens=100,
            ...         temperature=0.9,
            ...         system="Respond only in Yoda-speak.",
            ...         messages=[{"role": "user", "content": "How are you today?"}],
            ...     )
            >>>     print(message.content[0].text)
            >>>     await finalize()
            >>> asyncio.run(main())
        """

        pass
