import json
import logging
import time
import traceback
import uuid
from datetime import datetime, timezone

import httpx
from httpx import Request, Response

from log10.llm import Log10Config
from log10.load import get_log10_session_tags, last_completion_response_var, session_id_var


logger: logging.Logger = logging.getLogger("LOG10")

GRAPHQL_URL = "https://graphql.log10.io/graphql"

_log10_config = Log10Config()
base_url = _log10_config.url
httpx_client = httpx.Client()
httpx_async_client = httpx.AsyncClient()


def _get_time_diff(created_at):
    time = datetime.fromisoformat(created_at)
    now = datetime.now(timezone.utc)
    diff = now - time
    # convert the time difference to human readable format
    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds//3600} hours ago"
    elif diff.seconds > 60:
        return f"{diff.seconds//60} minutes ago"


def _try_get(url: str, timeout: int = 10) -> httpx.Response:
    httpx_client.headers = {
        "x-log10-token": _log10_config.token,
        "x-log10-organization-id": _log10_config.org_id,
        "Content-Type": "application/json",
    }
    httpx_timeout = httpx.Timeout(timeout)
    try:
        res = httpx_client.get(url, timeout=httpx_timeout)
        res.raise_for_status()
        return res
    except httpx.HTTPError as http_err:
        if "401" in str(http_err):
            logger.error(
                "Failed anthorization. Please verify that LOG10_TOKEN and LOG10_ORG_ID are set correctly and try again."
                + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
            )
        else:
            logger.error(f"Failed with error: {http_err}")
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
            logger.error(e.response.json()["error"])
        raise


def _try_post_request(url: str, payload: dict = {}) -> httpx.Response:
    headers = {
        "x-log10-token": _log10_config.token,
        "x-log10-organization-id": _log10_config.org_id,
        "Content-Type": "application/json",
    }
    payload["organization_id"] = _log10_config.org_id
    res = None
    try:
        res = httpx_client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res
    except httpx.HTTPError as http_err:
        if "401" in str(http_err):
            logger.error(
                "Failed anthorization. Please verify that LOG10_TOKEN and LOG10_ORG_ID are set correctly and try again."
                + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
            )
        else:
            logger.error(f"Failed with error: {http_err}")
    except Exception as err:
        logger.error(f"Failed to insert in log10: {payload} with error {err}")


def _try_post_graphql_request(query: str, variables: dict = {}) -> httpx.Response:
    headers = {"content-type": "application/json", "x-api-token": _log10_config.token}

    payload = {"query": query, "variables": variables}
    res = None
    try:
        res = httpx_client.post(GRAPHQL_URL, headers=headers, json=payload)
        res.raise_for_status()
        return res
    except httpx.HTTPError as http_err:
        if "401" in str(http_err):
            logger.error(
                "Failed anthorization. Please verify that LOG10_TOKEN and LOG10_ORG_ID are set correctly and try again."
                + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
            )
        else:
            logger.error(f"Failed with error: {http_err}")
    except Exception as err:
        logger.error(f"Failed to make requests to log10 graphQL: {payload} with error {err}")


async def _try_post_graphql_request_async(query: str, variables: dict = {}) -> httpx.Response:
    headers = {"content-type": "application/json", "x-api-token": _log10_config.token}

    payload = {"query": query, "variables": variables}
    res = None
    try:
        res = await httpx_async_client.post(GRAPHQL_URL, headers=headers, json=payload)
        res.raise_for_status()
        return res
    except httpx.HTTPError as http_err:
        if "401" in str(http_err):
            logger.error(
                "Failed anthorization. Please verify that LOG10_TOKEN and LOG10_ORG_ID are set correctly and try again."
                + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
            )
        else:
            logger.error(f"Failed with error: {http_err}")
    except Exception as err:
        logger.error(f"Failed to make requests to log10 graphQL: {payload} with error {err}")


async def _try_post_request_async(url: str, payload: dict = {}) -> httpx.Response:
    headers = {
        "x-log10-token": _log10_config.token,
        "x-log10-organization-id": _log10_config.org_id,
        "Content-Type": "application/json",
    }
    payload["organization_id"] = _log10_config.org_id
    try:
        res = await httpx_async_client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res
    except httpx.HTTPStatusError as http_err:
        if "401" in str(http_err):
            logger.error(
                "Failed authorization. Please verify that LOG10_TOKEN and LOG10_ORG_ID are set correctly and try again."
                + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
            )
        else:
            logger.error(f"Failed with error: {http_err}")
    except Exception as err:
        logger.error(f"Failed to insert in log10: {payload} with error {err}")


def format_anthropic_request(request_content) -> str:
    for message in request_content.get("messages", []):
        new_content = []
        message_content = message.get("content")

        if isinstance(message_content, list):
            for c in message_content:
                c_type = c.get("type", "")
                if c_type == "image":
                    image_type = c.get("source", {}).get("media_type", "")
                    image_data = c.get("source", {}).get("data", "")
                    new_content.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{image_type};base64,{image_data}"},
                        }
                    )
                elif c_type == "tool_use":
                    tool_call = {
                        "id": c.get("id", ""),
                        "type": "function",
                        "function": {
                            "name": c.get("name", ""),
                            "arguments": str(c.get("input", {})),
                        },
                    }
                    message["tool_calls"] = [tool_call]
                    del message["content"]
                elif c_type == "tool_result":
                    content_block_content = c.get("content", "")
                    if isinstance(content_block_content, list):
                        for content in content_block_content:
                            if content.get("type", "") == "text":
                                message["content"] = content.get("text", "")
                else:
                    new_content.append(c)

        if new_content:
            message["content"] = new_content

    new_tools = []
    for tool in request_content.get("tools", []):
        if input_schema := tool.get("input_schema", {}):
            parameters = input_schema
        else:
            parameters = {}
        new_tool = {
            "type": "function",
            "function": {
                "name": tool.get("name", ""),
                "description": tool.get("description", ""),
                "parameters": parameters,
            },
        }
        new_tools.append(new_tool)

    if new_tools:
        request_content["tools"] = new_tools

    return json.dumps(request_content)


# def get_completion_id(request: Request):
#     host = request.headers.get("host")
#     if "anthropic" in host:
#         paths = ["/v1/messages", "/v1/complete"]
#         if not any(path in str(request.url) for path in paths):
#             logger.warning("Currently logging is only available for anthropic v1/messages and v1/complete.")
#             return

#     if "openai" in host and "v1/chat/completions" not in str(request.url):
#         logger.warning("Currently logging is only available for openai v1/chat/completions.")
#         return

#     request.headers["x-log10-completion-id"] = str(uuid.uuid4())


# def _get_completion_id_from_request(request: Request):
#     completion_id = request.headers.get("x-log10-completion-id", "")
#     if not completion_id:
#         return

#     last_completion_response_var.set({"completionID": completion_id})
#     return completion_id


def _init_log_row(request: Request):
    start_time = time.time()
    request.started = start_time
    orig_module = ""
    orig_qualname = ""
    request_content_decode = request.content.decode("utf-8")
    host = request.headers.get("host")
    if "openai" in host:
        if "chat" in str(request.url):
            kind = "chat"
            orig_module = "openai.api_resources.chat_completion"
            orig_qualname = "ChatCompletion.create"
        else:
            kind = "completion"
            orig_module = "openai.api_resources.completion"
            orig_qualname = "Completion.create"
    elif "anthropic" in host:
        kind = "chat"
        ### TODO how to know whether it's create or stream?
        url_path = request.url
        content_type = request.headers.get("content-type")
        request_content = json.loads(request_content_decode)
        if "/v1/messages" in str(url_path):
            if content_type == "application/json":
                orig_module = "anthropic.resources.messages"
                orig_qualname = "Messages.create"
            else:
                orig_module = "anthropic.resources.messages"
                orig_qualname = "Messages.stream"
        else:
            kind = "completion"
            orig_module = "anthropic.resources.completions"
            orig_qualname = "Completions.create"

        request_content_decode = format_anthropic_request(request_content)

    else:
        logger.warning("Currently logging is only available for async openai and anthropic.")
        return
    log_row = {
        "status": "started",
        "kind": kind,
        "orig_module": orig_module,
        "orig_qualname": orig_qualname,
        "request": request_content_decode,
        "session_id": session_id_var.get(),
    }
    if get_log10_session_tags():
        log_row["tags"] = get_log10_session_tags()

    return log_row


# def log_request(request: Request):
#     log_row = _init_log_row(request)
#     completion_id = _get_completion_id_from_request(request)
#     _try_post_request(url=f"{base_url}/api/completions/{completion_id}", payload=log_row)


# async def alog_request(request: Request):
#     log_row = _init_log_row(request)
#     completion_id = _get_completion_id_from_request(request)
#     await _try_post_request_async(url=f"{base_url}/api/completions/{completion_id}", payload=log_row)


def check_provider_request(request: Request):
    host = request.headers.get("host")
    if "anthropic" in host:
        paths = ["/v1/messages", "/v1/complete"]
        if not any(path in str(request.url) for path in paths):
            logger.warning("Currently logging is only available for anthropic v1/messages and v1/complete.")
            return

    if "openai" in host and "v1/chat/completions" not in str(request.url):
        logger.warning("Currently logging is only available for openai v1/chat/completions.")
        return


def get_completion_id(request: Request):
    completion_id = str(uuid.uuid4())
    request.headers["x-log10-completion-id"] = completion_id
    last_completion_response_var.set({"completionID": completion_id})
    return completion_id


class _EventHookManager:
    def __init__(self):
        self.event_hooks = {
            "request": [self.get_completion_id, self.log_request],
        }
        self.completion_id = ""
        self.log_row = {}

    def get_completion_id(self, request: httpx.Request):
        logger.debug("LOG10: generating completion id")
        check_provider_request(request)
        self.completion_id = get_completion_id(request)

    def log_request(self, request: httpx.Request):
        logger.debug("LOG10: sending sync request")
        self.log_row = _init_log_row(request)
        _try_post_request(url=f"{base_url}/api/completions/{self.completion_id}", payload=self.log_row)


class _AsyncEventHookManager:
    def __init__(self):
        logger.debug("LOG10: initializing async event hook manager")
        self.event_hooks = {
            "request": [self.get_completion_id, self.log_request],
        }
        self.completion_id = ""
        self.log_row = {}

    async def get_completion_id(self, request: httpx.Request):
        logger.debug("LOG10: generating completion id")
        check_provider_request(request)
        self.completion_id = get_completion_id(request)

    async def log_request(self, request: httpx.Request):
        logger.debug("LOG10: sending async request")
        self.log_row = _init_log_row(request)
        await _try_post_request_async(url=f"{base_url}/api/completions/{self.completion_id}", payload=self.log_row)


class _LogResponse(Response):
    def __init__(self, *args, **kwargs):
        self.log_row = kwargs["log_row"]
        del kwargs["log_row"]
        super().__init__(*args, **kwargs)
        # self.full_content = ""
        # self.function_name = ""
        # self.full_argument = ""
        # self.tool_calls = []
        # self.finish_reason = ""

    def patch_streaming_log(self, duration: int, full_response: str):
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

        responses = full_response.split("\n\n")
        response_json = self.parse_response_data(responses)

        # Choices can be empty list with the openai version > 1.26.0
        # if not response_json.get("choices"):
        #     response_json["choices"] = [{"index": 0}]

        # if response_json.get("choices", []):
        #     # It will only set finish_reason for openai version > 1.26.0
        #     if self.finish_reason:
        #         response_json["choices"][0]["finish_reason"] = self.finish_reason

        #     if self.full_content:
        #         response_json["choices"][0]["message"] = {
        #             "role": "assistant",
        #             "content": self.full_content,
        #         }
        #     elif self.tool_calls:
        #         response_json["choices"][0]["message"] = {
        #             "content": None,
        #             "role": "assistant",
        #             "tool_calls": self.tool_calls,
        #         }
        #     elif self.function_name and self.full_argument:
        #         # function is deprecated in openai api
        #         response_json["choices"][0]["function_call"] = {
        #             "name": self.function_name,
        #             "arguments": self.full_argument,
        #         }

        self.log_row["response"] = json.dumps(response_json)
        self.log_row["status"] = "finished"
        self.log_row["duration"] = duration
        self.log_row["stacktrace"] = json.dumps(stacktrace)

    def iter_bytes(self, *args, **kwargs):
        full_response = ""
        finished = False
        for chunk in super().iter_bytes(*args, **kwargs):
            full_response += chunk.decode(errors="ignore")
            if self.is_response_end_reached(full_response):
                finished = True
                duration = int(time.time() - self.request.started) * 1000

                completion_id = self.request.headers.get("x-log10-completion-id", "")
                if finished and completion_id:
                    self.patch_streaming_log(duration, full_response)
                    _try_post_request(url=f"{base_url}/api/completions/{completion_id}", payload=self.log_row)
            yield chunk

    async def aiter_bytes(self, *args, **kwargs):
        full_response = ""
        finished = False
        async for chunk in super().aiter_bytes(*args, **kwargs):
            full_response += chunk.decode(errors="ignore")
            if self.is_response_end_reached(full_response):
                finished = True
                duration = int(time.time() - self.request.started) * 1000

                completion_id = self.request.headers.get("x-log10-completion-id", "")
                if finished and completion_id:
                    self.patch_streaming_log(duration, full_response)
                    await _try_post_request_async(
                        url=f"{base_url}/api/completions/{completion_id}", payload=self.log_row
                    )
            yield chunk

    def is_response_end_reached(self, text: str):
        host = self.request.headers.get("host")
        if "anthropic" in host:
            return self.is_anthropic_response_end_reached(text)
        elif "openai" in host:
            return self.is_openai_response_end_reached(text)
        else:
            logger.warning("Currently logging is only available for async openai and anthropic.")
            return False

    def is_anthropic_response_end_reached(self, text: str):
        return "event: message_stop" in text

    def is_openai_response_end_reached(self, text: str):
        return "data: [DONE]" in text

    def parse_anthropic_responses(self, responses: list[str]):
        message_id = ""
        model = ""
        finish_reason = None
        full_content = ""
        input_tokens = 0
        output_tokens = 0
        tool_calls = []
        tool_call = {}
        arguments = ""

        for r in responses:
            if not r:
                break

            data_index = r.find("data:")
            r_json = json.loads(r[data_index + len("data:") :])

            ### anthropic first data contains
            ### {"event":"message_start","data":{"message":{"role":"user","content":"Hello, how are you today?"}}}
            type = r_json["type"]
            if type == "message_start":
                message = r_json.get("message", {})
                message_id = message.get("id", "")
                model = message.get("model", "")
                input_tokens = message.get("usage", {}).get("input_tokens", 0)
            elif type == "content_block_start":
                content_block = r_json.get("content_block", {})
                content_block_type = content_block.get("type", "")
                if content_block_type == "tool_use":
                    tool_call = {
                        "id": content_block.get("id", ""),
                        "type": "function",
                        "function": {"name": content_block.get("name", ""), "arguments": ""},
                    }
                if content_block_type == "text":
                    full_content += content_block.get("text", "")
            elif type == "content_block_delta":
                delta = r_json.get("delta", {})
                if (delta_text := delta.get("text")) is not None:
                    full_content += delta_text

                if (delta_partial_json := delta.get("partial_json")) is not None:
                    ## If there is a content of chain of thoughts,
                    ## then the next one should be append to the tool_call
                    arguments += delta_partial_json
            elif type == "message_delta":
                finish_reason = r_json.get("delta", {}).get("stop_reason", "")
                output_tokens = r_json.get("usage", {}).get("output_tokens", 0)
            elif type == "content_block_stop" or type == "message_stop":
                if tool_call:
                    tool_call["function"]["arguments"] = arguments
                    tool_calls.append(tool_call)
                    arguments = ""
                    tool_call = {}

        response = {
            "id": message_id,
            "object": "chat",
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }

        response_json = response.copy()
        message = {
            "role": "assistant",
        }

        if full_content:
            message["content"] = full_content
            # response_json["choices"][0]["message"] = {"role": "assistant", "content": full_content}

        if tool_calls:
            message["tool_calls"] = tool_calls
            # response_json["choices"][0]["message"] = {
            #     "content": None,
            #     "role": "assistant",
            #     "tool_calls": tool_calls,
            # }

        response_json["choices"][0]["message"] = message
        return response_json

    def parse_openai_responses(self, responses: list[str]):
        r_json = {}
        tool_calls = []
        full_content = ""
        function_name = ""
        full_argument = ""
        finish_reason = ""

        for r in responses:
            if self.is_openai_response_end_reached(r):
                break

            # loading the substring of response text after 'data: '.
            # example: 'data: {"choices":[{"text":"Hello, how can I help you today?"}]}'
            data_index = r.find("data:")
            r_json = json.loads(r[data_index + len("data:") :])

            if r_json.get("choices", []):
                if delta := r_json["choices"][0].get("delta", {}):
                    # Delta may have content
                    # delta: { "content": " "}
                    if content := delta.get("content", ""):
                        full_content += content

                    # May be a function call, and have to reconstruct the arguments
                    if function_call := delta.get("function_call", {}):
                        # May be function name
                        if function_call_name := function_call.get("name", ""):
                            function_name = function_call_name
                        # May be function arguments
                        if arguments := function_call.get("arguments", ""):
                            full_argument += arguments

                    if tc := delta.get("tool_calls", []):
                        if tc[0].get("id", ""):
                            tool_calls.append(tc[0])
                        elif tc[0].get("function", {}).get("arguments", ""):
                            idx = tc[0].get("index")
                            tool_calls[idx]["function"]["arguments"] += tc[0]["function"]["arguments"]

                if fr := r_json["choices"][0].get("finish_reason", ""):
                    finish_reason = fr

        r_json["object"] = "chat.completion"
        # r_json is the last response before "data: [DONE]"
        response_json = r_json.copy()

        if not response_json.get("choices"):
            response_json["choices"] = [{"index": 0}]

        if response_json.get("choices", []):
            # It will only set finish_reason for openai version > 1.26.0
            if finish_reason:
                response_json["choices"][0]["finish_reason"] = finish_reason

            if full_content:
                response_json["choices"][0]["message"] = {
                    "role": "assistant",
                    "content": full_content,
                }
            elif tool_calls:
                response_json["choices"][0]["message"] = {
                    "content": None,
                    "role": "assistant",
                    "tool_calls": tool_calls,
                }
            elif function_name and full_argument:
                # function is deprecated in openai api
                response_json["choices"][0]["function_call"] = {
                    "name": function_name,
                    "arguments": full_argument,
                }

        return response_json

    def parse_response_data(self, responses: list[str]):
        host = self.request.headers.get("host")
        if "openai" in host:
            return self.parse_openai_responses(responses)
        elif "anthropic" in host:
            return self.parse_anthropic_responses(responses)
        else:
            logger.warning("Currently logging is only available for async openai and anthropic.")
            return None


def patch_response(log_row: dict, llm_response: dict, request: Request):
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

    elapsed = time.time() - request.started
    if "anthropic" in request.url.host:
        from anthropic.types.completion import Completion
        from anthropic.types.message import Message

        from log10.anthropic import Anthropic

        if "v1/messages" in str(request.url):
            llm_response = Anthropic.prepare_response(Message(**llm_response))
        elif "v1/complete" in str(request.url):
            llm_response = Anthropic.prepare_response(Completion(**llm_response))
        else:
            logger.warning("Currently logging is only available for anthropic v1/messages and v1/complete.")

    log_row["status"] = "finished"
    log_row["response"] = json.dumps(llm_response)
    log_row["duration"] = int(elapsed * 1000)
    log_row["stacktrace"] = json.dumps(stacktrace)
    if get_log10_session_tags():
        log_row["tags"] = get_log10_session_tags()

    return log_row


class _LogTransport(httpx.BaseTransport):
    def __init__(self, transport: httpx.BaseTransport, event_hook_manager: _EventHookManager):
        self.transport = transport
        self.event_hook_manager = event_hook_manager

    def handle_request(self, request: Request) -> Response:
        try:
            response = self.transport.handle_request(request)
        except Exception as e:
            logger.warning(f"Failed to send request: {e}")
            return

        if response.status_code >= 400:
            logger.warning(f"HTTP error occurred: {response.status_code}")
            return

        completion_id = request.headers.get("x-log10-completion-id", "")
        if not completion_id:
            return response

        if response.headers.get("content-type").startswith("application/json"):
            response.read()
            llm_response = response.json()
            log_row = patch_response(self.event_hook_manager.log_row, llm_response, request)

            # current_stack_frame = traceback.extract_stack()
            # stacktrace = [
            #     {
            #         "file": frame.filename,
            #         "line": frame.line,
            #         "lineno": frame.lineno,
            #         "name": frame.name,
            #     }
            #     for frame in current_stack_frame
            # ]

            # elapsed = time.time() - request.started
            # if "anthropic" in request.url.host:
            #     from anthropic.types.completion import Completion
            #     from anthropic.types.message import Message

            #     from log10.anthropic import Anthropic

            #     if "v1/messages" in str(request.url):
            #         llm_response = Anthropic.prepare_response(Message(**llm_response))
            #     elif "v1/complete" in str(request.url):
            #         llm_response = Anthropic.prepare_response(Completion(**llm_response))
            #     else:
            #         logger.warning("Currently logging is only available for anthropic v1/messages and v1/complete.")

            # log_row["status"] = "finished"
            # log_row["response"] = json.dumps(llm_response)
            # log_row["duration"] = int(elapsed * 1000)
            # log_row["stacktrace"] = json.dumps(stacktrace)

            # if get_log10_session_tags():
            #     log_row["tags"] = get_log10_session_tags()
            _try_post_request(url=f"{base_url}/api/completions/{completion_id}", payload=log_row)
            return response
        elif response.headers.get("content-type").startswith("text/event-stream"):
            return _LogResponse(
                status_code=response.status_code,
                headers=response.headers,
                stream=response.stream,
                extensions=response.extensions,
                request=request,
                log_row=self.event_hook_manager.log_row,
            )

        # In case of an error, get out of the way
        return response


class _AsyncLogTransport(httpx.AsyncBaseTransport):
    def __init__(self, transport: httpx.AsyncBaseTransport, event_hook_manager: _AsyncEventHookManager):
        self.transport = transport
        self.event_hook_manager = event_hook_manager

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        try:
            response = await self.transport.handle_async_request(request)
        except Exception as e:
            logger.warning(f"Failed to send request: {e}")
            return

        if response.status_code >= 400:
            logger.warning(f"HTTP error occurred: {response.status_code}")
            return

        completion_id = request.headers.get("x-log10-completion-id", "")
        if not completion_id:
            return response

        if response.headers.get("content-type").startswith("application/json"):
            await response.aread()
            llm_response = response.json()

            log_row = patch_response(self.event_hook_manager.log_row, llm_response, request)

            # current_stack_frame = traceback.extract_stack()
            # stacktrace = [
            #     {
            #         "file": frame.filename,
            #         "line": frame.line,
            #         "lineno": frame.lineno,
            #         "name": frame.name,
            #     }
            #     for frame in current_stack_frame
            # ]

            # elapsed = time.time() - request.started
            # if "anthropic" in request.url.host:
            # from anthropic.types.beta.tools import (
            #     ToolsBetaMessage,
            # )

            # from log10.anthropic import Anthropic

            # llm_response = Anthropic.prepare_response(ToolsBetaMessage(**llm_response))

            # log_row = {
            #     "response": json.dumps(llm_response),
            #     "status": "finished",
            #     "duration": int(elapsed * 1000),
            #     "stacktrace": json.dumps(stacktrace),
            #     "kind": "chat",
            #     "request": request.content.decode("utf-8"),
            #     "session_id": session_id_var.get(),
            # }
            # if get_log10_session_tags():
            #     log_row["tags"] = get_log10_session_tags()
            await _try_post_request_async(url=f"{base_url}/api/completions/{completion_id}", payload=log_row)
            return response
        elif response.headers.get("content-type").startswith("text/event-stream"):
            return _LogResponse(
                status_code=response.status_code,
                headers=response.headers,
                stream=response.stream,
                extensions=response.extensions,
                request=request,
                log_row=self.event_hook_manager.log_row,
            )

        # In case of an error, get out of the way
        return response
