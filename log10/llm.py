import json
import logging
import os
import traceback
from abc import ABC
from enum import Enum
from typing import Optional

import requests

Role = Enum("Role", ["system", "assistant", "user"])
Kind = Enum("Kind", ["chat", "text"])

def _get_or_throw(arg:Optional[str], arg_name: str, env_name: str) -> str:
    if arg is not None:
        return arg
    if os.getenv(env_name) is not None:
        return os.getenv(env_name)  # type: ignore[return-value]
    raise Exception(f"Missing {arg_name} argument and {env_name} environment variable")


class Log10Config:
    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        org_id: Optional[str] = None,
        tags: Optional[list[str]] = None,
        DEBUG: bool = False,
    ):
        self.url = _get_or_throw(url,"Log 10 URL", "LOG10_URL")
        self.token = _get_or_throw(token, "Log 10 Token", "LOG10_TOKEN")
        self.org_id = _get_or_throw(org_id, "Log10 Organization Id", "LOG10_ORG_ID")
        self.DEBUG = DEBUG

        # Get tags from env, if not set, use empty list
        if tags is not None and len(tags) > 0:
            self.tags = tags
        elif os.getenv("LOG10_TAGS") is not None:
            self.tags = os.getenv("LOG10_TAGS").split(",")  # type: ignore[union-attr]
        else:
            self.tags = []
   


class Message:
    def __init__(
        self,
        role: Role,
        content: str,
        id: Optional[str] = None,
        completion: Optional[str] = None,
    ):
        self.id = id
        self.role = role
        self.content = content
        self.completion = completion

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, message: dict):
        return cls(
            role=message["role"],
            content=message["content"],
            id=message.get("id"),
            completion=message.get("completion"),
        )


class Messages:
    @staticmethod
    def from_dict(messages: dict):
        return [Message.from_dict(message) for message in messages]


class Completion:
    pass


class ChatCompletion(Completion):
    def __init__(
        self,
        role: str,
        content: str,
        response: dict,
        completion_id: Optional[str] = None,
    ):
        self.role = role
        self.content = content
        self.response = response
        self.completion_id = completion_id

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
        }

    def __str__(self) -> str:
        return json.dumps(self.to_dict())


class TextCompletion(Completion):
    def __init__(self, text: str, response: dict, completion_id: Optional[str] = None):
        self._text = text
        self.response = response
        self.completion_id = completion_id

    def text(self) -> str:
        return self._text

    def __str__(self) -> str:
        return self._text


class LLM(ABC):
    last_completion_response = None
    duration = None

    def __init__(self, hparams: dict, log10_config: Log10Config):
        self.log10_config = log10_config
        self.hparams = hparams

        # Start session
        if self.log10_config:
            session_url = self.log10_config.url + "/api/sessions"
            try:
                res = requests.request(
                    "POST",
                    session_url,
                    headers={
                        "x-log10-token": self.log10_config.token,
                        "Content-Type": "application/json",
                    },
                    json={"organization_id": self.log10_config.org_id},
                )
                response = res.json()
                self.session_id = response["sessionID"]
            except Exception as e:
                logging.warning(
                    f"Failed to start session with {session_url} using token {self.log10_config.token}."
                    + f"Won't be able to log. {e}"
                )
                self.log10_config = None

    def last_completion_url(self):
        if self.last_completion_response is None:
            return None

        return (
            self.log10_config.url
            + "/app/"
            + self.last_completion_response["organizationSlug"]
            + "/completions/"
            + self.last_completion_response["completionID"]
        )

    def last_duration(self):
        if self.duration is None:
            return None

        return self.duration

    def text(self, prompt: str, hparams: dict) -> TextCompletion:
        raise Exception("Not implemented")

    def text_request(self, prompt: str, hparams: dict) -> dict:
        raise Exception("Not implemented")

    def chat(self, messages: list[Message], hparams: dict) -> ChatCompletion:
        raise Exception("Not implemented")

    def chat_request(self, messages: list[Message], hparams: dict) -> dict:
        raise Exception("Not implemented")

    def api_request(self, rel_url: str, method: str, request: dict):
        return requests.request(
            method,
            f"{self.log10_config.url}{rel_url}",
            headers={
                "x-log10-token": self.log10_config.token,
                "Content-Type": "application/json",
            },
            json=request,
        )

    # Save the start of a completion in **openai request format**.
    def log_start(self, request, kind: Kind, tags: Optional[list[str]] = None):
        if not self.log10_config:
            return None

        res = self.api_request(
            "/api/completions", "POST", {"organization_id": self.log10_config.org_id}
        )
        self.last_completion_response = res.json()
        completion_id = res.json()["completionID"]

        # merge tags
        tags = (
            list(set(tags + self.log10_config.tags)) if tags else self.log10_config.tags
        )

        res = self.api_request(
            f"/api/completions/{completion_id}",
            "POST",
            {
                "kind": kind == Kind.text and "completion" or "chat",
                "organization_id": self.log10_config.org_id,
                "session_id": self.session_id,
                "orig_module": "openai.api_resources.completion"
                if kind == Kind.text
                else "openai.api_resources.chat_completion",
                "orig_qualname": "Completion.create"
                if kind == Kind.text
                else "ChatCompletion.create",
                "status": "started",
                "tags": tags,
                "request": json.dumps(request),
            },
        )

        return completion_id

    # Save the end of a completion in **openai request format**.
    def log_end(self, completion_id: str, response: dict, duration: int):
        if not self.log10_config:
            return None

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

        duration_sec = int(duration * 1000)
        self.duration = duration_sec

        self.api_request(
            f"/api/completions/{completion_id}",
            "POST",
            {
                "response": json.dumps(response),
                "status": "finished",
                "duration": duration_sec,
                "stacktrace": json.dumps(stacktrace),
            },
        )


class NoopLLM(LLM):
    def __init__(self, hparams: dict, log10_config=None):
        pass

    def chat(self, messages: list[Message], hparams: dict) -> ChatCompletion:
        logging.info("Received chat completion requst: " + str(messages))
        return ChatCompletion(role="assistant", content="I'm not a real LLM")

    def text(self, prompt: str, hparams: dict) -> TextCompletion:
        logging.info("Received text completion requst: " + prompt)
        return TextCompletion(text="I'm not a real LLM")
