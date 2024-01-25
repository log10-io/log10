import asyncio
import functools
import json
import logging
import os
import queue
import threading
import time
import traceback
from contextlib import contextmanager
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
        # todo: set timeout
        res = requests.post(url, headers=headers, json=json_payload)
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

    try:
        res = post_session_request()

        return res.json()["sessionID"]
    except requests.HTTPError as http_err:
        if "401" in str(http_err):
            raise Exception(
                "Failed anthorization. Please verify that LOG10_TOKEN and LOG10_ORG_ID are set correctly and try again."
                + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
            )
        else:
            raise Exception(f"Failed to create LOG10 session. Error: {http_err}")
    except requests.ConnectionError:
        raise Exception(
            "Invalid LOG10_URL. Please verify that LOG10_URL is set correctly and try again."
            + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
        )
    except Exception as e:
        raise Exception(
            "Failed to create LOG10 session: "
            + str(e)
            + "\nLikely cause: LOG10 env vars missing or not picked up correctly!"
            + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
        )


# Global variable to store the current sessionID.
sessionID = get_session_id()
last_completion_response = None
global_tags = []


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


async def log_async(completion_url, func, **kwargs):
    global last_completion_response

    res = post_request(completion_url)
    # todo: handle session id for bigquery scenario
    last_completion_response = res.json()
    completionID = res.json()["completionID"]

    if DEBUG:
        log_url(res, completionID)

    # in case the usage of load(openai) and langchain.ChatOpenAI
    if "api_key" in kwargs:
        kwargs.pop("api_key")

    log_row = {
        # do we want to also store args?
        "status": "started",
        "orig_module": func.__module__,
        "orig_qualname": func.__qualname__,
        "request": json.dumps(kwargs),
        "session_id": sessionID,
        "tags": global_tags,
    }
    if target_service == "log10":
        res = post_request(completion_url + "/" + completionID, log_row)
    elif target_service == "bigquery":
        pass
        # NOTE: We only save on request finalization.

    return completionID


def run_async_in_thread(completion_url, func, result_queue, **kwargs):
    result = asyncio.run(log_async(completion_url=completion_url, func=func, **kwargs))
    result_queue.put(result)


def log_sync(completion_url, func, **kwargs):
    global last_completion_response
    res = post_request(completion_url)

    last_completion_response = res.json()
    completionID = res.json()["completionID"]
    if DEBUG:
        log_url(res, completionID)
    # in case the usage of load(openai) and langchain.ChatOpenAI
    if "api_key" in kwargs:
        kwargs.pop("api_key")
    log_row = {
        # do we want to also store args?
        "status": "started",
        "orig_module": func.__module__,
        "orig_qualname": func.__qualname__,
        "request": json.dumps(kwargs),
        "session_id": sessionID,
        "tags": global_tags,
    }
    res = post_request(completion_url + "/" + completionID, log_row)
    return completionID


def intercepting_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        completion_url = url + "/api/completions"
        output = None
        result_queue = queue.Queue()

        try:
            with timed_block(sync_log_text + " call duration"):
                if USE_ASYNC:
                    threading.Thread(
                        target=run_async_in_thread,
                        kwargs={
                            "completion_url": completion_url,
                            "func": func,
                            "result_queue": result_queue,
                            **kwargs,
                        },
                    ).start()
                else:
                    completionID = log_sync(completion_url=completion_url, func=func, **kwargs)

            current_stack_frame = traceback.extract_stack()
            stacktrace = [
                {
                    "file": frame.filename,
                    "line": frame.line,
                    "lineno": frame.lineno,
                    "name": frame.name,
                }
                for frame in current_stack_frame
            ]

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
            logger.debug(f"LOG10: failed - {e}")
            # todo: change with openai v1 update
            if type(e).__name__ == "InvalidRequestError" and "This model's maximum context length" in str(e):
                failure_kind = "ContextWindowExceedError"
            else:
                failure_kind = type(e).__name__
            failure_reason = str(e)
            log_row = {
                "status": "failed",
                "failure_kind": failure_kind,
                "failure_reason": failure_reason,
                "stacktrace": json.dumps(stacktrace),
                "kind": "completion",
                "orig_module": func.__module__,
                "orig_qualname": func.__qualname__,
                "session_id": sessionID,
                "tags": global_tags,
            }
            res = post_request(completion_url + "/" + completionID, log_row)
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
                if "anthropic" in type(output).__module__:
                    from log10.anthropic import Anthropic

                    response = Anthropic.prepare_response(kwargs["prompt"], output, "text")
                    kind = "completion"
                else:
                    response = output
                    kind = "chat" if output.object == "chat.completion" else "completion"

                # in case the usage of load(openai) and langchain.ChatOpenAI
                if "api_key" in kwargs:
                    kwargs.pop("api_key")

                if hasattr(response, "model_dump_json"):
                    response = response.model_dump_json()
                else:
                    response = json.dumps(response)
                log_row = {
                    "response": response,
                    "status": "finished",
                    "duration": int(duration * 1000),
                    "stacktrace": json.dumps(stacktrace),
                    "kind": kind,
                    "orig_module": func.__module__,
                    "orig_qualname": func.__qualname__,
                    "request": json.dumps(kwargs),
                    "session_id": sessionID,
                    "tags": global_tags,
                }

                if target_service == "log10":
                    res = post_request(completion_url + "/" + completionID, log_row)
                    if res.status_code != 200:
                        logger.error(f"LOG10: failed to insert in log10: {log_row} with error {res.text}")
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
    support both openai V0 and V1, and anthropic

    Keyword arguments:
    module -- the module to be intercepted (e.g. openai)
    DEBUG_ -- whether to show log10 related debug statements via python logging (default False)
    USE_ASYNC_ -- whether to run in async mode (default True)

    Openai V0 example:
    Example:
        >>> from log10.load import log10 # xdoctest: +SKIP
        >>> import openai
        >>> log10(openai)
        >>> completion = openai.Completion.create(
        >>>     model="gpt-3.5-turbo-instruct",
        >>>     prompt="Once upon a time",
        >>>     max_tokens=32,
        >>> )
        >>> print(completion)

    Example:
        >>> from log10.load import log10 # xdoctest: +SKIP
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
        else:
            attr = module.api_resources.completion.Completion
            method = getattr(attr, "create")
            setattr(attr, "create", intercepting_decorator(method))

            attr = module.api_resources.chat_completion.ChatCompletion
            mothod = getattr(attr, "create")
            setattr(attr, "create", intercepting_decorator(mothod))

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
