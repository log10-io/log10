import types
import functools
import inspect
from pprint import pprint
import requests
import os
import json
import time

url = os.environ.get("LOG10_URL")
token = os.environ.get("LOG10_TOKEN")


def intercepting_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Intercepted call to '{func.__name__}'")

        session_url = url + "/api/completions"
        output = None

        try:
            res = requests.request("PUT",
                                session_url, headers={"x-log10-token": token, "Content-Type": "application/json"})

            completionID = res.json()['completionID']

            res = requests.request("POST",
                                session_url + "/" + completionID, headers={"x-log10-token": token, "Content-Type": "application/json"}, json={
                                    "request": json.dumps(kwargs) #do we want to also store args?
                                })

            start_time = time.time()*1000
            output = func(*args, **kwargs)
            duration = time.time()*1000 - start_time

            res = requests.request("POST",
                                session_url + "/" + completionID, headers={"x-log10-token": token, "Content-Type": "application/json"}, json={
                                    "response": json.dumps(output),
                                    "duration": int(duration)
                                })

        except Exception as e:
            print(e)

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
