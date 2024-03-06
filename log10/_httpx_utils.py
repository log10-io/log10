import json
import logging
import time
import traceback
from datetime import datetime, timezone

import httpx
from httpx import Request, Response

from log10.llm import Log10Config
from log10.load import get_log10_session_tags, sessionID


logger: logging.Logger = logging.getLogger("LOG10")


_log10_config = Log10Config()
base_url = _log10_config.url
httpx_client = httpx.Client()


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


async def get_completion_id(request: Request):
    if "v1/chat/completions" not in str(request.url):
        logger.warning("Currently logging is only available for v1/chat/completions.")
        return

    completion_url = "/api/completions"
    res = _try_post_request(url=f"{base_url}{completion_url}")
    try:
        completion_id = res.json().get("completionID")
    except Exception as e:
        logger.error(f"Failed to get completion ID. Error: {e}. Skipping completion recording.")
    else:
        request.headers["x-log10-completion-id"] = completion_id


async def log_request(request: Request):
    start_time = time.time()
    request.started = start_time
    completion_id = request.headers.get("x-log10-completion-id", "")
    if not completion_id:
        return

    orig_module = ""
    orig_qualname = ""
    if "chat" in str(request.url):
        kind = "chat"
        orig_module = "openai.api_resources.chat_completion"
        orig_qualname = "ChatCompletion.create"
    else:
        kind = "completion"
        orig_module = "openai.api_resources.completion"
        orig_qualname = "Completion.create"
    log_row = {
        "status": "started",
        "kind": kind,
        "orig_module": orig_module,
        "orig_qualname": orig_qualname,
        "request": request.content.decode("utf-8"),
        "session_id": sessionID,
    }
    if get_log10_session_tags():
        log_row["tags"] = get_log10_session_tags()
    _try_post_request(url=f"{base_url}/api/completions/{completion_id}", payload=log_row)


class _LogResponse(Response):
    async def aiter_bytes(self, *args, **kwargs):
        full_response = ""
        finished = False
        async for chunk in super().aiter_bytes(*args, **kwargs):
            full_response += chunk.decode(errors="ignore")

            if "data: [DONE]" in full_response:
                finished = True
            yield chunk

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
            full_content = ""
            function_name = ""
            full_argument = ""
            responses = full_response.split("\n\n")
            for r in responses:
                if "data: [DONE]" in r:
                    break

                r_json = json.loads(r[6:])

                delta = r_json["choices"][0]["delta"]

                # Delta may have content
                if "content" in delta:
                    content = delta["content"]
                    if content:
                        full_content += content

                # May be a function call, and have to reconstruct the arguments
                if "function_call" in delta:
                    # May be function name
                    if "name" in delta["function_call"]:
                        function_name = delta["function_call"]["name"]
                    # May be function arguments
                    if "arguments" in delta["function_call"]:
                        full_argument += delta["function_call"]["arguments"]

            response_json = r_json.copy()
            response_json["object"] = "completion"

            # If finish_reason is function_call - don't log the response
            if not (
                "choices" in response_json
                and response_json["choices"]
                and response_json["choices"][0]["finish_reason"] == "function_call"
            ):
                response_json["choices"][0]["message"] = {"role": "assistant", "content": full_content}
            else:
                response_json["choices"][0]["function_call"] = {
                    "name": function_name,
                    "arguments": full_argument,
                }

            log_row = {
                "response": json.dumps(response_json),
                "status": "finished",
                "duration": int(time.time() - self.request.started) * 1000,
                "stacktrace": json.dumps(stacktrace),
                "kind": "chat",
                "request": self.request.content.decode("utf-8"),
                "session_id": sessionID,
            }
            if get_log10_session_tags():
                log_row["tags"] = get_log10_session_tags()
            _try_post_request(url=f"{base_url}/api/completions/{completion_id}", payload=log_row)


class _LogTransport(httpx.AsyncBaseTransport):
    def __init__(self, transport: httpx.AsyncBaseTransport):
        self.transport = transport

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self.transport.handle_async_request(request)

        completion_id = request.headers.get("x-log10-completion-id", "")
        if not completion_id:
            return response

        if response.headers.get("content-type") == "application/json":
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
            log_row = {
                "response": json.dumps(llm_response),
                "status": "finished",
                "duration": int(elapsed * 1000),
                "stacktrace": json.dumps(stacktrace),
                "kind": "chat",
                "request": request.content.decode("utf-8"),
                "session_id": sessionID,
            }
            if get_log10_session_tags():
                log_row["tags"] = get_log10_session_tags()
            _try_post_request(url=f"{base_url}/api/completions/{completion_id}", payload=log_row)
            return response
        elif response.headers.get("content-type") == "text/event-stream":
            return _LogResponse(
                status_code=response.status_code,
                headers=response.headers,
                stream=response.stream,
                extensions=response.extensions,
                request=request,
            )
