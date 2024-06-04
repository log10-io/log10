import asyncio
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


def format_anthropic_tools_request(request_content) -> str:
    new_tools = []
    for tool in request_content["tools"]:
        new_tool = {
            "type": "function",
            "function": {"name": tool["name"], "description": tool["description"], "parameters": tool["input_schema"]},
        }
        new_tools.append(new_tool)
    request_content["tools"] = new_tools
    return json.dumps(request_content)


async def get_completion_id(request: Request):
    host = request.headers.get("host")
    if "anthropic" in host and "/v1/messages" not in str(request.url):
        logger.warning("Currently logging is only available for anthropic v1/messages.")
        return

    if "openai" in host and "v1/chat/completions" not in str(request.url):
        logger.warning("Currently logging is only available for openai v1/chat/completions.")
        return

    request.headers["x-log10-completion-id"] = str(uuid.uuid4())


async def log_request(request: Request):
    start_time = time.time()
    request.started = start_time
    completion_id = request.headers.get("x-log10-completion-id", "")
    if not completion_id:
        return

    last_completion_response_var.set({"completionID": completion_id})
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
        request_content = json.loads(request_content_decode)
        if "tools" in request_content:
            orig_module = "anthropic.resources.beta.tools"
            orig_qualname = "Messages.stream"
            request_content_decode = format_anthropic_tools_request(request_content)
        else:
            orig_module = "anthropic.resources.messages"
            orig_qualname = "Messages.stream"
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
    asyncio.create_task(_try_post_request_async(url=f"{base_url}/api/completions/{completion_id}", payload=log_row))


class _LogResponse(Response):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.full_content = ""
        self.function_name = ""
        self.full_argument = ""
        self.tool_calls = []
        self.finish_reason = ""

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
                    r_json = self.parse_response_data(responses)

                    response_json = r_json.copy()
                    # r_json is the last response before "data: [DONE]"

                    # Choices can be empty list with the openai version > 1.26.0
                    if not response_json.get("choices"):
                        response_json["choices"] = [{"index": 0}]

                    if response_json.get("choices", []):
                        # It will only set finish_reason for openai version > 1.26.0
                        if self.finish_reason:
                            response_json["choices"][0]["finish_reason"] = self.finish_reason

                        if self.full_content:
                            response_json["choices"][0]["message"] = {
                                "role": "assistant",
                                "content": self.full_content,
                            }
                        elif self.tool_calls:
                            response_json["choices"][0]["message"] = {
                                "content": None,
                                "role": "assistant",
                                "tool_calls": self.tool_calls,
                            }
                        elif self.function_name and self.full_argument:
                            # function is deprecated in openai api
                            response_json["choices"][0]["function_call"] = {
                                "name": self.function_name,
                                "arguments": self.full_argument,
                            }

                    request_content_decode = self.request.content.decode("utf-8")
                    if "anthropic" in self.request.headers.get("host"):
                        request_content = json.loads(request_content_decode)
                        if "tools" in request_content:
                            request_content_decode = format_anthropic_tools_request(request_content)

                    log_row = {
                        "response": json.dumps(response_json),
                        "status": "finished",
                        "duration": duration,
                        "stacktrace": json.dumps(stacktrace),
                        "kind": "chat",
                        "request": request_content_decode,
                        "session_id": session_id_var.get(),
                    }
                    if get_log10_session_tags():
                        log_row["tags"] = get_log10_session_tags()
                    asyncio.create_task(
                        _try_post_request_async(url=f"{base_url}/api/completions/{completion_id}", payload=log_row)
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
        message_id = None
        model = None
        finish_reason = None
        input_tokens = 0
        output_tokens = 0
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
                message_id = r_json["message"]["id"]
                model = r_json["message"]["model"]
                input_tokens = r_json["message"]["usage"]["input_tokens"]
            elif type == "content_block_start":
                content_block = r_json["content_block"]
                type = content_block["type"]
                if type == "tool_use":
                    id = content_block["id"]
                    tool_call = {
                        "id": id,
                        "type": "function",
                        "function": {"name": content_block["name"], "arguments": ""},
                    }

                if content_block_text := content_block.get("text", ""):
                    self.full_content += content_block_text
            elif type == "content_block_delta":
                delta = r_json["delta"]
                if delta_text := delta.get("text", ""):
                    self.full_content += delta_text

                if delta_partial_json := delta.get("partial_json", ""):
                    if self.full_content:
                        self.full_content += delta_partial_json
                    else:
                        arguments += delta_partial_json
            elif type == "message_delta":
                finish_reason = r_json["delta"]["stop_reason"]
                output_tokens = r_json["usage"]["output_tokens"]
            elif type == "content_block_end" or type == "message_end":
                if tool_call:
                    tool_call["function"]["arguments"] = arguments
                    self.tool_calls.append(tool_call)
                    tool_call = {}
                    arguments = ""

        return {
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

    def parse_openai_responses(self, responses: list[str]):
        r_json = {}
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
                        self.full_content += content

                    # May be a function call, and have to reconstruct the arguments
                    if function_call := delta.get("function_call", {}):
                        # May be function name
                        if function_name := function_call.get("name", ""):
                            self.function_name = function_name
                        # May be function arguments
                        if arguments := function_call.get("arguments", ""):
                            self.full_argument += arguments

                    if tc := delta.get("tool_calls", []):
                        if tc[0].get("id", ""):
                            self.tool_calls.append(tc[0])
                        elif tc[0].get("function", {}).get("arguments", ""):
                            idx = tc[0].get("index")
                            self.tool_calls[idx]["function"]["arguments"] += tc[0]["function"]["arguments"]

                if fr := r_json["choices"][0].get("finish_reason", ""):
                    self.finish_reason = fr

        r_json["object"] = "chat.completion"

        return r_json

    def parse_response_data(self, responses: list[str]):
        host = self.request.headers.get("host")
        if "openai" in host:
            return self.parse_openai_responses(responses)
        elif "anthropic" in host:
            return self.parse_anthropic_responses(responses)
        else:
            logger.warning("Currently logging is only available for async openai and anthropic.")
            return None


class _LogTransport(httpx.AsyncBaseTransport):
    def __init__(self, transport: httpx.AsyncBaseTransport):
        self.transport = transport

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
                from anthropic.types.beta.tools import (
                    ToolsBetaMessage,
                )

                from log10.anthropic import Anthropic

                llm_response = Anthropic.prepare_response(ToolsBetaMessage(**llm_response))

            log_row = {
                "response": json.dumps(llm_response),
                "status": "finished",
                "duration": int(elapsed * 1000),
                "stacktrace": json.dumps(stacktrace),
                "kind": "chat",
                "request": request.content.decode("utf-8"),
                "session_id": session_id_var.get(),
            }
            if get_log10_session_tags():
                log_row["tags"] = get_log10_session_tags()
            asyncio.create_task(
                _try_post_request_async(url=f"{base_url}/api/completions/{completion_id}", payload=log_row)
            )
            return response
        elif response.headers.get("content-type").startswith("text/event-stream"):
            return _LogResponse(
                status_code=response.status_code,
                headers=response.headers,
                stream=response.stream,
                extensions=response.extensions,
                request=request,
            )

        # In case of an error, get out of the way
        return response


async def finalize():
    pending = asyncio.all_tasks()
    pending.remove(asyncio.current_task())
    await asyncio.gather(*pending)
