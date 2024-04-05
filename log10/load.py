import asyncio
import functools
import inspect
import json
import logging
import os
import queue
import threading
import time
import traceback
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
    import uuid
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
    if target_service == "bigquery":
        return str(uuid.uuid4())

    session_id = None
    try:
        res = post_session_request()
        session_id = res.json()["sessionID"]
    except requests.HTTPError as http_err:
        if "401" in str(http_err):
            logging.warn(
                "Failed anthorization. Please verify that LOG10_TOKEN and LOG10_ORG_ID are set correctly and try again."
                + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
            )
        else:
            logging.warn(f"Failed to create LOG10 session. Error: {http_err}")
    except requests.ConnectionError:
        logging.warn(
            "Invalid LOG10_URL. Please verify that LOG10_URL is set correctly and try again."
            + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
        )
    except Exception as e:
        logging.warn(
            "Failed to create LOG10 session: "
            + str(e)
            + "\nLikely cause: LOG10 env vars missing or not picked up correctly!"
            + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
        )

    return session_id


# Global variable to store the current sessionID.
sessionID = get_session_id()
last_completion_response = None
global_tags = []


def get_log10_session_tags():
    return global_tags


class log10_session:
    def __init__(self, tags=None):
        self.tags = tags

        if tags is not None:
            global global_tags
            global_tags = tags

    def __enter__(self):
        global sessionID
        global last_completion_response
        sessionID = get_session_id()
        last_completion_response = None
        return self

    def last_completion_url(self):
        if last_completion_response is None:
            return None

        return (
            url
            + "/app/"
            + last_completion_response["organizationSlug"]
            + "/completions/"
            + last_completion_response["completionID"]
        )

    def __exit__(self, exc_type, exc_value, traceback):
        if self.tags is not None:
            global global_tags
            global_tags = None
        return


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
    global last_completion_response

    res = None
    try:
        res = post_request(completion_url)
        last_completion_response = res.json()
        completionID = res.json()["completionID"]

        if DEBUG:
            log_url(res, completionID)

        if target_service == "log10":
            try:
                res = post_request(completion_url + "/" + completionID, log_row)
            except Exception as e:
                logging.warn(f"LOG10: failed to log: {e}. Skipping")
                return None

        elif target_service == "bigquery":
            pass
            # NOTE: We only save on request finalization.

    except Exception as e:
        logging.warn(f"LOG10: failed to log: {e}. Skipping")
        return None

    return completionID


def run_async_in_thread(completion_url, log_row, result_queue):
    result = asyncio.run(log_async(completion_url=completion_url, log_row=log_row))
    result_queue.put(result)


def log_sync(completion_url, log_row):
    global last_completion_response
    completionID = None

    try:
        res = post_request(completion_url)
        last_completion_response = res.json()
        completionID = res.json()["completionID"]
        if DEBUG:
            log_url(res, completionID)
        res = post_request(completion_url + "/" + completionID, log_row)
    except Exception as e:
        logging.warn(f"LOG10: failed to get completionID from log10: {e}")
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
            else:
                self.finish_reason = chunk.choices[0].finish_reason

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
            if self.usage:
                response["usage"] = self.usage.dict()
            self.partial_log_row["response"] = json.dumps(response)
            self.partial_log_row["duration"] = int((time.perf_counter() - self.start_time) * 1000)

            try:
                res = post_request(self.completion_url + "/" + self.completionID, self.partial_log_row)
                if res.status_code != 200:
                    logger.error(f"LOG10: failed to insert in log10: {self.partial_log_row} with error {res.text}")
            except Exception as e:
                traceback.print_tb(e.__traceback__)
                logging.warn(f"LOG10: failed to log: {e}. Skipping")

            raise se


class AnthropicStreamingResponseWrapper:
    """
    Wraps a streaming response object to log the final result and duration to log10.
    """

    def __init__(self, completion_url, completionID, response, partial_log_row):
        self.completionID = completionID
        self.completion_url = completion_url
        self.partial_log_row = partial_log_row
        self.response = response
        self.final_result = ""
        self.start_time = time.perf_counter()
        self.message_id = None
        self.model = None
        self.finish_reason = None
        self.input_tokens = 0
        self.output_tokens = 0

    def __iter__(self):
        return self

    def __next__(self):
        chunk = next(self.response)
        if chunk.type == "message_start":
            self.model = chunk.message.model
            self.message_id = chunk.message.id
            self.input_tokens = chunk.message.usage.input_tokens
        elif chunk.type == "message_delta":
            self.finish_reason = chunk.delta.stop_reason
            self.output_tokens = chunk.usage.output_tokens
        elif chunk.type == "content_block_delta":
            self.final_result += chunk.delta.text
        elif chunk.type == "message_stop":
            response = {
                "id": self.message_id,
                "object": "chat",
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
                "usage": {
                    "prompt_tokens": self.input_tokens,
                    "completion_tokens": self.output_tokens,
                    "total_tokens": self.input_tokens + self.output_tokens,
                },
            }
            self.partial_log_row["response"] = json.dumps(response)
            self.partial_log_row["duration"] = int((time.perf_counter() - self.start_time) * 1000)

            res = post_request(self.completion_url + "/" + self.completionID, self.partial_log_row)
            if res.status_code != 200:
                logger.error(f"Failed to insert in log10: {self.partial_log_row} with error {res.text}. Skipping")

        return chunk


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


def _init_log_row(func, **kwargs):
    kwargs_copy = deepcopy(kwargs)

    log_row = {
        "status": "started",
        "orig_module": func.__module__,
        "orig_qualname": func.__qualname__,
        "stacktrace": json.dumps(_get_stack_trace()),
        "session_id": sessionID,
        "tags": global_tags,
    }

    # in case the usage of load(openai) and langchain.ChatOpenAI
    if "api_key" in kwargs_copy:
        kwargs_copy.pop("api_key")

    # We may have to flatten messages from their ChatCompletionMessage with nested ChatCompletionMessageToolCall to json serializable format
    # Rewrite in-place
    if "messages" in kwargs_copy:
        kwargs_copy["messages"] = flatten_messages(kwargs_copy["messages"])

    # kind and request are set based on the module and qualname
    # request is based on openai schema
    if "anthropic" in func.__module__:
        log_row["kind"] = "chat" if "message" in func.__module__ else "completion"
        # set system message
        if "system" in kwargs_copy:
            kwargs_copy["messages"].insert(0, {"role": "system", "content": kwargs_copy["system"]})
        if "messages" in kwargs_copy:
            for m in kwargs_copy["messages"]:
                if isinstance(m.get("content"), list):
                    new_content = []
                    for c in m.get("content", ""):
                        if c.get("type") == "image":
                            image_type = c.get("source", {}).get("media_type", "")
                            image_data = c.get("source", {}).get("data", "")
                            new_content.append(
                                {"type": "image_url", "image_url": {"url": f"data:{image_type};base64,{image_data}"}}
                            )
                        else:
                            new_content.append(c)
                    m["content"] = new_content
    elif "vertexai" in func.__module__:
        if func.__name__ == "_send_message":
            # get model name save in ChatSession instance
            log_row["kind"] = "chat"
            chat_session_instance = inspect.currentframe().f_back.f_back.f_locals["self"]
            model_name = chat_session_instance._model._model_name.split("/")[-1]

            # TODO how to handle chat history
            # chat_history = chat_session_instance.history
            kwargs_copy.update(
                {"model": model_name, "messages": [{"role": "user", "content": kwargs_copy["content"]}]}
            )
            if kwargs_copy.get("generation_config"):
                for key, value in kwargs_copy["generation_config"].to_dict().items():
                    if key == "max_output_tokens":
                        kwargs_copy["max_tokens"] = value
                    else:
                        kwargs_copy[key] = value
                kwargs_copy.pop("generation_config")
    elif "mistralai" in func.__module__:
        log_row["kind"] = "chat"
    elif "openai" in func.__module__:
        kind = "chat" if "chat" in func.__module__ else "completion"
        log_row["kind"] = kind

    log_row["request"] = json.dumps(kwargs_copy)

    return log_row


def intercepting_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        completion_url = url + "/api/completions"
        output = None
        result_queue = queue.Queue()

        try:
            log_row = _init_log_row(func, **kwargs)

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
                        logging.warn("LOG10: failed to get completionID from log10. Skipping log.")
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
                    completionID = result_queue.get()

            if completionID is None:
                logging.warn(f"LOG10: failed to get completionID from log10: {e}. Skipping log.")
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
                logging.warn(f"LOG10: failed to log: {le}. Skipping, but raising LLM error.")
            raise e
        else:
            # finished with no exceptions
            if USE_ASYNC:
                with timed_block("extra time spent waiting for log10 call"):
                    while result_queue.empty():
                        pass
                    completionID = result_queue.get()

            with timed_block("result call duration (sync)"):
                response = output
                # Adjust the Anthropic output to match OAI completion output
                if "anthropic" in func.__module__:
                    if type(output).__name__ == "Stream":
                        log_row["response"] = response
                        log_row["status"] = "finished"
                        return AnthropicStreamingResponseWrapper(
                            completion_url=completion_url,
                            completionID=completionID,
                            response=response,
                            partial_log_row=log_row,
                        )
                    from log10.anthropic import Anthropic

                    response = Anthropic.prepare_response(output, input_prompt=kwargs.get("prompt", ""))
                elif "vertexai" in func.__module__:
                    response = output
                    reason = response.candidates[0].finish_reason.name
                    import uuid

                    ret_response = {
                        "id": str(uuid.uuid4()),
                        "object": "completion",
                        "choices": [
                            {
                                "index": 0,
                                "finish_reason": str(reason).lower(),
                                "message": {"role": "assistant", "content": response.text},
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
                    response = output.copy()

                    if "choices" in response:
                        response = flatten_response(response)
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
                        res = post_request(completion_url + "/" + completionID, log_row)
                        if res.status_code != 200:
                            logger.error(f"LOG10: failed to insert in log10: {log_row} with error {res.text}")
                    except Exception as e:
                        logging.warn(f"LOG10: failed to log: {e}. Skipping")

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
                        log_row["session_id"] = sessionID

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

    if module.__name__ == "anthropic":
        attr = module.resources.completions.Completions
        method = getattr(attr, "create")
        setattr(attr, "create", intercepting_decorator(method))

        # anthropic Messages completion
        attr = module.resources.messages.Messages
        method = getattr(attr, "create")
        setattr(attr, "create", intercepting_decorator(method))
    if module.__name__ == "mistralai":
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
            # patch module.AsyncOpenAI.__init__ to new_init
            origin_init = module.AsyncOpenAI.__init__

            def new_init(self, *args, **kwargs):
                logger.debug("LOG10: patching AsyncOpenAI.__init__")
                import httpx

                from log10._httpx_utils import (
                    _LogTransport,
                    get_completion_id,
                    log_request,
                )

                event_hooks = {
                    "request": [get_completion_id, log_request],
                }
                async_httpx_client = httpx.AsyncClient(
                    event_hooks=event_hooks,
                    transport=_LogTransport(httpx.AsyncHTTPTransport()),
                )
                kwargs["http_client"] = async_httpx_client
                origin_init(self, *args, **kwargs)

            module.AsyncOpenAI.__init__ = new_init

        else:
            attr = module.api_resources.completion.Completion
            method = getattr(attr, "create")
            setattr(attr, "create", intercepting_decorator(method))

            attr = module.api_resources.chat_completion.ChatCompletion
            mothod = getattr(attr, "create")
            setattr(attr, "create", intercepting_decorator(mothod))
    elif module.__name__ == "vertexai":
        # patch chat send_message function
        attr = module.generative_models._generative_models.ChatSession
        method = getattr(attr, "_send_message")
        setattr(attr, "_send_message", intercepting_decorator(method))

        # For future reference:
        # if callable(attr) and isinstance(attr, types.FunctionType):
        #     print(f"attr:{attr}")
        #     setattr(module, name, intercepting_decorator(attr))
        # elif inspect.isclass(attr):  # Check if attribute is a class
        #     intercept_class_methods(attr)
        # # else: # uncomment if we want to include nested function support
        # #     intercept_nested_functions(attr)


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
                global global_tags
                global_tags = kwargs.pop("tags")
            super().__init__(*args, **kwargs)

            if not getattr(openai, "_log10_patched", False):
                log10(openai)
                openai._log10_patched = True


try:
    import anthropic
except ImportError:
    logger.warning("Anthropic not found. Skipping defining log10.load.Anthropic client.")
else:
    from anthropic import Anthropic

    class Anthropic(Anthropic):
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

        def __init__(self, *args, **kwargs):
            if "tags" in kwargs:
                global global_tags
                global_tags = kwargs.pop("tags")
            super().__init__(*args, **kwargs)

            if not getattr(anthropic, "_log10_patched", False):
                log10(anthropic)
                anthropic._log10_patched = True
