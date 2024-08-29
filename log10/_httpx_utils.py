import asyncio
import json
import logging
import os
import time
import traceback
import uuid
from datetime import datetime, timezone
from enum import Enum

import httpx
from httpx import Request, Response

from log10.llm import Log10Config
from log10.load import get_log10_session_tags, last_completion_response_var, session_id_var


logger: logging.Logger = logging.getLogger("LOG10")

GRAPHQL_URL = "https://graphql.log10.io/graphql"

LOG10_HTTPX_READ_TIMEOUT = os.environ.get("LOG10_HTTPX_READ_TIMEOUT")
_log10_config = Log10Config()
base_url = _log10_config.url
# Default timeouts for httpx client: connect, read, write, and pool are all 5 seconds.
# We're overriding the read timeout to 10s when LOG10_HTTPX_READ_TIMEOUT is not set.
read_timeout = float(LOG10_HTTPX_READ_TIMEOUT) if LOG10_HTTPX_READ_TIMEOUT else 10.0
timeout = httpx.Timeout(5.0, read=read_timeout)
httpx_client = httpx.Client()
httpx_async_client = httpx.AsyncClient(timeout=timeout)


class LLM_CLIENTS(Enum):
    ANTHROPIC = "Anthropic"
    OPENAI = "OpenAI"
    UNKNOWN = "Unknown"


CLIENT_PATHS = {
    LLM_CLIENTS.ANTHROPIC: ["/v1/messages", "/v1/complete"],
    # OpenAI and Mistral use the path "v1/chat/completions"
    # Perplexity uses the path "chat/completions". Documentation: https://docs.perplexity.ai/reference/post_chat_completions
    LLM_CLIENTS.OPENAI: ["v1/chat/completions", "chat/completions"],
}

USER_AGENT_NAME_TO_PROVIDER = {
    "AsyncOpenAI": LLM_CLIENTS.OPENAI,
    "AsyncAnthropic": LLM_CLIENTS.ANTHROPIC,
    "Anthropic": LLM_CLIENTS.ANTHROPIC,
    "OpenAI": LLM_CLIENTS.OPENAI,
}


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
        logger.error(f"Failed to insert in log10: {payload} with error {err}.", exc_info=True)


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
    except httpx.ReadTimeout as read_timeout_err:
        logger.error(f"Failed to post request to {url} with {payload} due to a read timeout error: {read_timeout_err}")
    except httpx.HTTPStatusError as http_err:
        if "401" in str(http_err):
            logger.error(
                "Failed authorization. Please verify that LOG10_TOKEN and LOG10_ORG_ID are set correctly and try again."
                + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details"
            )
        else:
            logger.error(f"Failed with error: {http_err}")
    except Exception as err:
        logger.error(f"Failed to insert in log10: {payload} with error {err}.", exc_info=True)


def format_anthropic_request(request_content) -> str:
    if system_message := request_content.get("system", ""):
        request_content["messages"].insert(0, {"role": "system", "content": system_message})

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


def _get_llm_client(request: Request) -> LLM_CLIENTS:
    """
    The request object includes the user-agent header, which is used to identify the LLM client.
    For example:
    - headers({'user-agent': 'AsyncOpenAI/Python 1.40.6'})
    - headers({'user-agent': 'Anthropic/Python 0.34.0'})
    """
    user_agent = request.headers.get("user-agent", "")
    class_name = user_agent.split("/")[0]

    if class_name in USER_AGENT_NAME_TO_PROVIDER.keys():
        return USER_AGENT_NAME_TO_PROVIDER[class_name]
    else:
        return LLM_CLIENTS.UNKNOWN


def _init_log_row(request: Request):
    start_time = time.time()
    request.started = start_time
    orig_module = ""
    orig_qualname = ""
    request_content_decode = request.content.decode("utf-8")
    llm_client = _get_llm_client(request)

    if llm_client == LLM_CLIENTS.OPENAI:
        if "chat" in str(request.url):
            kind = "chat"
            orig_module = "openai.api_resources.chat_completion"
            orig_qualname = "ChatCompletion.create"
        else:
            kind = "completion"
            orig_module = "openai.api_resources.completion"
            orig_qualname = "Completion.create"
    elif llm_client == LLM_CLIENTS.ANTHROPIC:
        kind = "chat"
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
        logger.debug("Currently logging is only available for async openai and anthropic.")
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


def get_completion_id(request: Request):
    llm_client = _get_llm_client(request)
    if llm_client is LLM_CLIENTS.UNKNOWN:
        logger.debug("Currently logging is only available for async openai and anthropic.")
        return

    # Check if the request URL matches any of the allowed paths for the class name
    if not any(path in str(request.url) for path in CLIENT_PATHS.get(llm_client, [])):
        logger.debug(f"Currently logging is only available for {llm_client} {', '.join(CLIENT_PATHS[llm_client])}.")
        return

    completion_id = str(uuid.uuid4())
    request.headers["x-log10-completion-id"] = completion_id
    last_completion_response_var.set({"completionID": completion_id})
    return completion_id


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
            prompt = ""
            if request.content:
                content = request.content.decode("utf-8")
                content_json = json.loads(content)
                prompt = content_json.get("prompt", "")

            llm_response = Anthropic.prepare_response(Completion(**llm_response), input_prompt=prompt)
        else:
            logger.debug("Currently logging is only available for anthropic v1/messages and v1/complete.")

    log_row["status"] = "finished"
    log_row["response"] = json.dumps(llm_response)
    log_row["duration"] = int(elapsed * 1000)
    log_row["stacktrace"] = json.dumps(stacktrace)
    if get_log10_session_tags():
        log_row["tags"] = get_log10_session_tags()

    return log_row


class _RequestHooks:
    """
    The class to manage the event hooks for sync requests and initialize the log row.
    The event hooks are:
    - get_completion_id: to generate the completion id
    - log_request: to send the sync request with initial log row to the log10 platform
    """

    def __init__(self):
        logger.debug("LOG10: initializing request hooks")
        self.event_hooks = {
            "request": [self.log_request],
        }
        self.log_row = {}

    def log_request(self, request: httpx.Request):
        logger.debug("LOG10: generating completion id")
        completion_id = get_completion_id(request)
        if not completion_id:
            logger.debug("LOG10: completion id is not generated. Skipping")
            return

        logger.debug("LOG10: sending sync request")
        self.log_row = _init_log_row(request)
        if not self.log_row:
            logger.debug("LOG10: log row is not initialized. Skipping")
            return

        _try_post_request(url=f"{base_url}/api/completions/{completion_id}", payload=self.log_row)


class _AsyncRequestHooks:
    """
    The class to manage the event hooks for async requests and initialize the log row.
    The event hooks are:
    - get_completion_id: to generate the completion id
    - log_request: to send the sync request with initial log row to the log10 platform
    """

    def __init__(self):
        logger.debug("LOG10: initializing async request hooks")
        self.event_hooks = {
            "request": [self.log_request],
        }
        self.log_row = {}

    async def log_request(self, request: httpx.Request):
        logger.debug("LOG10: generating completion id")
        completion_id = get_completion_id(request)
        if not completion_id:
            logger.debug("LOG10: completion id is not generated. Skipping")
            return

        logger.debug("LOG10: sending async request")
        self.log_row = _init_log_row(request)
        if not self.log_row:
            logger.debug("LOG10: log row is not initialized. Skipping")
            return

        asyncio.create_task(
            _try_post_request_async(url=f"{base_url}/api/completions/{completion_id}", payload=self.log_row)
        )


class _LogResponse(Response):
    def __init__(self, *args, **kwargs):
        self.log_row = kwargs.pop("log_row")
        self.llm_client = _get_llm_client(kwargs.get("request"))
        self.host_header = kwargs.get("request").headers.get("host")
        super().__init__(*args, **kwargs)

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

        separator = (
            "\r\n\r\n" if self.llm_client == LLM_CLIENTS.OPENAI and "perplexity" in self.host_header else "\n\n"
        )
        responses = full_response.split(separator)
        filter_responses = [r for r in responses if r]
        response_json = self.parse_response_data(filter_responses)

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
                    asyncio.create_task(
                        _try_post_request_async(
                            url=f"{base_url}/api/completions/{completion_id}", payload=self.log_row
                        )
                    )
            yield chunk

    def is_response_end_reached(self, text: str) -> bool:
        if self.llm_client == LLM_CLIENTS.ANTHROPIC:
            return self.is_anthropic_response_end_reached(text)
        elif self.llm_client == LLM_CLIENTS.OPENAI:
            return self.is_openai_response_end_reached(text)
        else:
            logger.debug("Currently logging is only available for async openai and anthropic.")
            return False

    def is_anthropic_response_end_reached(self, text: str):
        return "event: message_stop" in text

    def has_response_finished_with_stop_reason(self, text: str, parse_single_data_entry: bool = False):
        json_strings = text.split("data: ")[1:]
        # Parse the last JSON string
        last_json_str = json_strings[-1].strip()
        try:
            last_object = json.loads(last_json_str)
        except json.JSONDecodeError:
            logger.debug(f"Full response: {repr(text)}")
            logger.debug(f"Failed to parse the last JSON string: {last_json_str}")
            return False

        if choices := last_object.get("choices", []):
            choice = choices[0]
        else:
            return False

        finish_reason = choice.get("finish_reason", "")
        content = choice.get("delta", {}).get("content", "")

        if finish_reason == "stop":
            return not content if parse_single_data_entry else True
        return False

    def is_openai_response_end_reached(self, text: str, parse_single_data_entry: bool = False):
        """
        OpenAI, Mistral response end is reached when the data contains "data: [DONE]\n\n".
        Perplexity, Cerebras response end is reached when the last JSON object contains finish_reason == stop.
        The parse_single_data_entry argument is used to distinguish between a single data entry and multiple data entries.
        The function is called in two contexts: first, to assess whether the entire accumulated response has completed when processing streaming data, and second, to verify if a single response object has finished processing during individual response handling.
        """
        hosts = ["openai", "mistral"]

        if any(p in self.host_header for p in hosts):
            suffix = "data: [DONE]" + ("" if parse_single_data_entry else "\n\n")
            if text.endswith(suffix):
                return True

        return self.has_response_finished_with_stop_reason(text, parse_single_data_entry)

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

        if tool_calls:
            message["tool_calls"] = tool_calls

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
            if self.is_openai_response_end_reached(r, parse_single_data_entry=True):
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
        if self.llm_client == LLM_CLIENTS.ANTHROPIC:
            return self.parse_anthropic_responses(responses)
        elif self.llm_client == LLM_CLIENTS.OPENAI:
            return self.parse_openai_responses(responses)
        else:
            logger.debug("Currently logging is only available for async openai and anthropic.")
            return None


class _LogTransport(httpx.BaseTransport):
    def __init__(self, transport: httpx.BaseTransport, request_hooks: _RequestHooks):
        self.transport = transport
        self.request_hooks = request_hooks

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
            log_row = patch_response(self.request_hooks.log_row, llm_response, request)
            _try_post_request(url=f"{base_url}/api/completions/{completion_id}", payload=log_row)
            return response
        elif response.headers.get("content-type").startswith("text/event-stream"):
            return _LogResponse(
                status_code=response.status_code,
                headers=response.headers,
                stream=response.stream,
                extensions=response.extensions,
                request=request,
                log_row=self.request_hooks.log_row,
            )

        # In case of an error, get out of the way
        return response


class _AsyncLogTransport(httpx.AsyncBaseTransport):
    def __init__(self, transport: httpx.AsyncBaseTransport, async_request_hooks: _AsyncRequestHooks):
        self.transport = transport
        self.async_request_hooks = async_request_hooks

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
            log_row = patch_response(self.async_request_hooks.log_row, llm_response, request)
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
                log_row=self.async_request_hooks.log_row,
            )

        # In case of an error, get out of the way
        return response


class InitPatcher:
    def __init__(self, module, class_names: list[str]):
        logger.debug("LOG10: initializing patcher")

        allowed_modules = ["openai", "anthropic"]
        if not any(allowed_module in module.__name__ for allowed_module in allowed_modules):
            raise ValueError("Only openai and anthropic modules are allowed.")

        self.module = module
        if len(class_names) > 2:
            raise ValueError("Only two class names (sync and async) are allowed")

        self.async_class_name = None
        self.sync_class_name = None

        for class_name in class_names:
            if class_name.startswith("Async"):
                self.async_class_name = class_name
                self.async_origin_init = getattr(module, self.async_class_name).__init__
            else:
                self.sync_class_name = class_name
                self.origin_init = getattr(module, self.sync_class_name).__init__

        self._patch_init()

    def _patch_init(self):
        def new_init(instance, *args, **kwargs):
            logger.debug(f"LOG10: patching {self.sync_class_name}.__init__")

            request_hooks = _RequestHooks()
            httpx_client = httpx.Client(
                event_hooks=request_hooks.event_hooks,
                transport=_LogTransport(httpx.HTTPTransport(), request_hooks),
            )
            kwargs["http_client"] = httpx_client
            self.origin_init(instance, *args, **kwargs)

        def async_new_init(instance, *args, **kwargs):
            logger.debug(f"LOG10: patching {self.async_class_name}.__init__")

            async_request_hooks = _AsyncRequestHooks()
            async_httpx_client = httpx.AsyncClient(
                event_hooks=async_request_hooks.event_hooks,
                transport=_AsyncLogTransport(httpx.AsyncHTTPTransport(), async_request_hooks),
            )
            kwargs["http_client"] = async_httpx_client
            self.async_origin_init(instance, *args, **kwargs)

        # Patch the asynchronous class __init__
        if self.async_class_name:
            async_class = getattr(self.module, self.async_class_name)
            async_class.__init__ = async_new_init

        # Patch the synchronous class __init__ if provided
        if self.sync_class_name:
            sync_class = getattr(self.module, self.sync_class_name)
            sync_class.__init__ = new_init


async def finalize():
    pending = asyncio.all_tasks()
    pending.remove(asyncio.current_task())
    await asyncio.gather(*pending)
