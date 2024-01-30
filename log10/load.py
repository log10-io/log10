import functools
import json
import logging
import os
import time
import traceback
import uuid
from importlib.metadata import version

import backoff
import httpx
from dotenv import load_dotenv
from packaging.version import parse


load_dotenv()

logging.basicConfig(
    format="[%(asctime)s - %(name)s - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger("LOG10")

url = os.environ.get("LOG10_URL", "https://log10.io")
token = os.environ.get("LOG10_TOKEN")
org_id = os.environ.get("LOG10_ORG_ID")


# log10, bigquery
target_service = os.environ.get("LOG10_DATA_STORE", "log10")
if target_service == "bigquery":
    raise NotImplementedError("For big query support, please get in touch with us at support@log10.io")


def is_openai_v1() -> bool:
    """Return whether OpenAI API is v1 or more."""
    _version = parse(version("openai"))
    return _version.major >= 1


def func_with_backoff(func, *args, **kwargs):
    """
    openai retries for V0. V1 has built-in retries, so we don't need to do anything in that case.
    """
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


# TODO: Retries on 5xx errors has to be handled in user code, so recommendation is to use tenacity.
transport = httpx.HTTPTransport(retries=5)
httpx_client = httpx.Client(transport=transport)


def try_post_request(url: str, json: dict = {}) -> httpx.Response:
    """
    Authenticated POST request to log10.
    """
    json["organization_id"] = org_id
    r = None
    try:
        # todo: set timeout
        r = httpx_client.post(
            url,
            headers={"x-log10-token": token, "Content-Type": "application/json"},
            json=json,
        )
        r.raise_for_status()
    except httpx.HTTPError as http_err:
        if "401" in str(http_err):
            logging.error(
                "Failed anthorization. Please verify that LOG10_TOKEN and LOG10_ORG_ID are set correctly and try again."
                + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
            )
        else:
            logging.error(f"Failed to create LOG10 session. Error: {http_err}")
    except Exception as e:
        logger.error(f"LOG10: failed to insert in log10: {json} with error {e}")

    return r


def get_session_id():
    """
    Get session ID from log10.
    """
    res = try_post_request(url + "/api/sessions", {})
    sessionID = None
    try:
        sessionID = res.json().get("sessionID")
    except Exception as e:
        logger.warning(f"LOG10: failed to get session ID. Error: {e}. Skipping session scope recording.")

    return sessionID


# Global variable to store the current sessionID.
sessionID = None
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

        return f"{url}/app/{last_completion_response.get('organizationSlug', 'unknown')}/completions/{last_completion_response.get('completionID')}"

    def __exit__(self, exc_type, exc_value, traceback):
        if self.tags is not None:
            global global_tags
            global_tags = None
        return


def intercepting_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global last_completion_response
        global sessionID

        #
        # If session ID is not set, create a new session.
        # If session ID isn't returned, continue with degraded functionality (lost session scope).
        #
        if sessionID is None:
            sessionID = get_session_id()

        #
        # Get completion ID. In case of failure, continue with degraded functionality (lost completion scope).
        #
        organizationSlug = "unknown"
        completionID = None
        r = try_post_request(f"{url}/api/completions", json={})
        try:
            completionID = r.json().get("completionID")
            organizationSlug = r.json().get("organizationSlug")
            last_completion_response = r.json()
        except Exception as e:
            logger.warning(f"LOG10: failed to get completion ID. Error: {e}. Skipping completion recording.")
            return func_with_backoff(func, *args, **kwargs)

        completion_url = f"{url}/api/completions/{completionID}"

        full_url = f"{url}/app/{organizationSlug}/completions/{completionID}"
        if DEBUG:
            logger.debug(f"Completion URL: {full_url}")

        #
        # Create base log row (resending request in case of failure)
        #
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
        log_row = {
            "status": "started",
            "orig_module": func.__module__,
            "orig_qualname": func.__qualname__,
            "stacktrace": json.dumps(stacktrace),
            "request": json.dumps(kwargs),
            "session_id": sessionID,
            "tags": global_tags,
        }

        #
        # Store request
        #
        try_post_request(completion_url, json=log_row)

        output = None
        start_time = None
        try:
            #
            # Call LLM
            #
            start_time = time.perf_counter()
            output = func_with_backoff(func, *args, **kwargs)

        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.debug(f"LOG10: failed - {e}")
            # todo: change with openai v1 update
            if type(e).__name__ == "InvalidRequestError" and "This model's maximum context length" in str(e):
                failure_kind = "ContextWindowExceedError"
            else:
                failure_kind = type(e).__name__

            failure_reason = str(e)

            log_row["status"] = "failed"
            log_row["duration"] = int(duration * 1000)
            log_row["failure_kind"] = failure_kind
            log_row["failure_reason"] = failure_reason

            try_post_request(completion_url, log_row)

            # We forward non-logger errors
            raise e
        else:
            #
            # Store both request and response, in case of failure of first call.
            #
            duration = time.perf_counter() - start_time
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

            log_row["status"] = "finished"
            log_row["response"] = response
            log_row["duration"] = int(duration * 1000)
            log_row["kind"] = kind

            try_post_request(completion_url, log_row)

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
