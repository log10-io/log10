import types
import functools
import inspect
import requests
import os
import json
import time
import traceback
from aiohttp import ClientSession
import asyncio
import threading
import queue
from contextlib import contextmanager
import logging
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("LOG10_URL")
token = os.environ.get("LOG10_TOKEN")
org_id = os.environ.get("LOG10_ORG_ID")

# log10, bigquery
target_service = os.environ.get("LOG10_DATA_STORE")

if target_service == "bigquery":
    from log10.bigquery import initialize_bigquery
    bigquery_client, bigquery_table = initialize_bigquery()
    import uuid
    from datetime import datetime, timezone
elif target_service is None:
    target_service = "log10"  # default to log10


def get_session_id():
    if target_service == "bigquery":
        return str(uuid.uuid4())

    try:
        session_url = url + "/api/sessions"
        res = requests.request("POST",
                               session_url, headers={"x-log10-token": token, "Content-Type": "application/json"}, json={
                                   "organization_id": org_id
                               })

        return res.json()['sessionID']
    except Exception as e:
        raise Exception("Failed to create LOG10 session: " + str(e) + "\nLikely cause: LOG10 env vars missing or not picked up correctly!" +
                        "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details")


# Global variable to store the current sessionID.
sessionID = get_session_id()


class log10_session:
    def __enter__(self):
        global sessionID
        sessionID = get_session_id()

    def __exit__(self, exc_type, exc_value, traceback):
        return


@contextmanager
def timed_block(block_name):
    if DEBUG:
        start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed_time = time.perf_counter() - start_time
            logging.debug(
                f"TIMED BLOCK - {block_name} took {elapsed_time:.6f} seconds to execute.")
    else:
        yield


def log_url(res, completionID):
    output = res.json()
    organizationSlug = output['organizationSlug']
    full_url = url + '/app/' + organizationSlug + '/completions/' + completionID
    logging.debug(f"LOG10: Completion URL: {full_url}")


async def log_async(completion_url, func, **kwargs):
    async with ClientSession() as session:
        res = requests.request("POST",
                               completion_url, headers={"x-log10-token": token, "Content-Type": "application/json"}, json={
                                   "organization_id": org_id
                               })
        # todo: handle session id for bigquery scenario
        completionID = res.json()['completionID']
        if DEBUG:
            log_url(res, completionID)
        log_row = {
            # do we want to also store args?
            "status": "started",
            "orig_module": func.__module__,
            "orig_qualname": func.__qualname__,
            "request": json.dumps(kwargs),
            "session_id": sessionID,
            "organization_id": org_id
        }
        if target_service == "log10":
            res = requests.request("POST",
                                   completion_url + "/" + completionID,
                                   headers={"x-log10-token": token,
                                            "Content-Type": "application/json"},
                                   json=log_row)
        elif target_service == "bigquery":
            pass
            # NOTE: We only save on request finalization.

        return completionID


def run_async_in_thread(completion_url, func, result_queue, **kwargs):
    result = asyncio.run(
        log_async(completion_url=completion_url, func=func, **kwargs))
    result_queue.put(result)


def log_sync(completion_url, func, **kwargs):
    res = requests.request("POST",
                           completion_url, headers={"x-log10-token": token, "Content-Type": "application/json"}, json={
                               "organization_id": org_id
                           })
    completionID = res.json()['completionID']
    if DEBUG:
        log_url(res, completionID)
    res = requests.request("POST",
                           completion_url + "/" + completionID,
                           headers={"x-log10-token": token,
                                    "Content-Type": "application/json"},
                           json={
                               # do we want to also store args?
                               "status": "started",
                               "orig_module": func.__module__,
                               "orig_qualname": func.__qualname__,
                               "request": json.dumps(kwargs),
                               "session_id": sessionID,
                               "organization_id": org_id
                           })
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
                    threading.Thread(target=run_async_in_thread, kwargs={
                        "completion_url": completion_url, "func": func, "result_queue": result_queue, **kwargs}).start()
                else:
                    completionID = log_sync(
                        completion_url=completion_url, func=func, **kwargs)

            current_stack_frame = traceback.extract_stack()
            stacktrace = ([{"file": frame.filename,
                          "line": frame.line,
                           "lineno": frame.lineno,
                            "name": frame.name} for frame in current_stack_frame])

            start_time = time.perf_counter()
            output = func(*args, **kwargs)
            duration = time.perf_counter() - start_time
            logging.debug(
                f"LOG10: TIMED BLOCK - OpenAI call duration: {duration}")

            if USE_ASYNC:
                with timed_block("extra time spent waiting for log10 call"):
                    while result_queue.empty():
                        pass
                    completionID = result_queue.get()

            with timed_block("result call duration (sync)"):
                log_row = {
                    "response": json.dumps(output),
                    "status": "finished",
                    "duration": int(duration*1000),
                    "stacktrace": json.dumps(stacktrace)
                }

                if target_service == "log10":
                    res = requests.request("POST",
                                           completion_url + "/" + completionID,
                                           headers={
                                               "x-log10-token": token, "Content-Type": "application/json"},
                                           json=log_row)
                elif target_service == "bigquery":
                    try:
                        log_row["id"] = str(uuid.uuid4())
                        log_row["created_at"] = datetime.now(
                            timezone.utc).isoformat()
                        log_row["request"] = json.dumps(kwargs)

                        if func.__qualname__ == "Completion.create":
                            log_row["kind"] = "completion"
                        elif func.__qualname__ == "ChatCompletion.create":
                            log_row["kind"] = "chat"

                        log_row["orig_module"] = func.__module__
                        log_row["orig_qualname"] = func.__qualname__
                        log_row["session_id"] = sessionID

                        bigquery_client.insert_rows_json(
                            bigquery_table, [log_row])

                    except Exception as e:
                        logging.error(
                            f"LOG10: failed to insert in Bigquery: {log_row} with error {e}")
        except Exception as e:
            logging.error("LOG10: failed", e)

        return output

    return wrapper


def set_sync_log_text(USE_ASYNC=True):
    return "async" if USE_ASYNC else "sync"


def log10(module, DEBUG_=False, USE_ASYNC_=True):
    """Intercept and overload module for logging purposes

    Keyword arguments:
    module -- the module to be intercepted (e.g. openai)
    DEBUG_ -- whether to show log10 related debug statements via python logging (default False)
    USE_ASYNC_ -- whether to run in async mode (default True)
    """
    global DEBUG, USE_ASYNC, sync_log_text
    DEBUG = DEBUG_
    USE_ASYNC = USE_ASYNC_
    sync_log_text = set_sync_log_text(USE_ASYNC=USE_ASYNC)
    logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO,
                        format='%(asctime)s - %(levelname)s - LOG10 - %(message)s')

    def intercept_nested_functions(obj):
        for name, attr in vars(obj).items():
            if callable(attr) and isinstance(attr, types.FunctionType):
                setattr(obj, name, intercepting_decorator(attr))
            elif inspect.isclass(attr):
                intercept_class_methods(attr)

    def intercept_class_methods(cls):
        for method_name, method in vars(cls).items():
            if isinstance(method, classmethod):
                original_method = method.__func__
                decorated_method = intercepting_decorator(original_method)
                setattr(cls, method_name, classmethod(decorated_method))
            elif isinstance(method, (types.FunctionType, types.MethodType)):
                setattr(cls, method_name, intercepting_decorator(method))
            elif inspect.isclass(method):  # Handle nested classes
                intercept_class_methods(method)

    for name, attr in vars(module).items():
        if callable(attr) and isinstance(attr, types.FunctionType):
            setattr(module, name, intercepting_decorator(attr))
        elif inspect.isclass(attr):  # Check if attribute is a class
            intercept_class_methods(attr)
        # else: # uncomment if we want to include nested function support
        #     intercept_nested_functions(attr)
