import types
import functools
import inspect
from pprint import pprint
import requests
import os
import json
import time
import traceback

url = os.environ.get("LOG10_URL")
token = os.environ.get("LOG10_TOKEN")
org_id = os.environ.get("LOG10_ORG_ID")


def get_session_id():
    try:
        session_url = url + "/api/sessions"
        res = requests.request("POST",
                               session_url, headers={"x-log10-token": token, "Content-Type": "application/json"}, json={
                                   "organization_id": org_id
                               })

        return res.json()['sessionID']
    except Exception as e:
        raise Exception("Failed to create LOG10 session: " + str(e))


# Global variable to store the current sessionID.
sessionID = get_session_id()


def intercepting_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        completion_url = url + "/api/completions"
        output = None

        try:
            res = requests.request("POST",
                                   completion_url, headers={"x-log10-token": token, "Content-Type": "application/json"}, json={
                                       "organization_id": org_id
                                   })
            completionID = res.json()['completionID']

            res = requests.request("POST",
                                   completion_url + "/" + completionID, headers={"x-log10-token": token, "Content-Type": "application/json"}, json={
                                       # do we want to also store args?
                                       "status": "started",
                                       "orig_module": func.__module__,
                                       "orig_qualname": func.__qualname__,
                                       "request": json.dumps(kwargs),
                                       "session_id": sessionID,
                                       "organization_id": org_id
                                   })

            current_stack_frame = traceback.extract_stack()
            stacktrace = ([{"file": frame.filename,
                          "line": frame.line,
                           "lineno": frame.lineno,
                            "name": frame.name} for frame in current_stack_frame])

            start_time = time.time()*1000
            output = func(*args, **kwargs)
            duration = time.time()*1000 - start_time

            res = requests.request("POST",
                                   completion_url + "/" + completionID, headers={"x-log10-token": token, "Content-Type": "application/json"}, json={
                                       "response": json.dumps(output),
                                       "status": "finished",
                                       "duration": int(duration),
                                       "stacktrace": json.dumps(stacktrace)
                                   })

        except Exception as e:
            print("failed", e)

        return output

    return wrapper


def log10(module):
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
