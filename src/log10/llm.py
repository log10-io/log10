import json
import logging
import os
import traceback
from abc import ABC
from enum import Enum
from typing import List, Optional

import requests


Role = Enum("Role", ["system", "assistant", "user"])
Kind = Enum("Kind", ["chat", "text"])


class Log10Config:
    def __init__(
        self,
        url: str = None,
        token: str = None,
        org_id: str = None,
        tags: List[str] = None,
        DEBUG: bool = False,
    ):
        self.url = url if url else os.getenv("LOG10_URL")
        self.token = token if token else os.getenv("LOG10_TOKEN")
        self.org_id = org_id if org_id else os.getenv("LOG10_ORG_ID")
        self.DEBUG = DEBUG

        # Get tags from env, if not set, use empty list
        if tags:
            self.tags = tags
        elif os.getenv("LOG10_TAGS") is not None:
            self.tags = os.getenv("LOG10_TAGS").split(",")
        else:
            self.tags = []


class Message(ABC):
    def __init__(self, role: Role, content: str, id: str = None, completion: str = None):
        self.id = id
        self.role = role
        self.content = content
        self.completion = completion

    def to_dict(self):
        return {
            "role": self.role,
            "content": self.content,
        }

    def from_dict(message: dict):
        return Message(
            role=message["role"],
            content=message["content"],
            id=message.get("id"),
            completion=message.get("completion"),
        )


class Messages(ABC):
    def from_dict(messages: dict):
        return [Message.from_dict(message) for message in messages]


class Completion(ABC):
    pass


class ChatCompletion(Completion):
    def __init__(self, role: str, content: str, response: dict = None, completion_id: str = None):
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
    def __init__(self, text: str, response: dict = None, completion_id=None):
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

    def __init__(self, hparams: dict = None, log10_config: Log10Config = None):
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
                    f"Failed to start session with {session_url} using token {self.log10_config.token}. Won't be able to log. {e}"
                    + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details."
                )
                self.log10_config = None
        else:
            logging.warning(
                "log10_config is not set. Won't be able to log with log10.io."
                + "\nSee https://github.com/log10-io/log10#%EF%B8%8F-setup for details."
            )

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

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        raise Exception("Not implemented")

    def text_request(self, prompt: str, hparams: dict = None) -> dict:
        raise Exception("Not implemented")

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        raise Exception("Not implemented")

    def chat_request(self, messages: List[Message], hparams: dict = None) -> dict:
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
    def log_start(self, request, kind: Kind, tags: Optional[List[str]] = None):
        if not self.log10_config:
            return None

        res = self.api_request("/api/completions", "POST", {"organization_id": self.log10_config.org_id})
        self.last_completion_response = res.json()
        completion_id = res.json()["completionID"]

        # merge tags
        if tags:
            tags = list(set(tags + self.log10_config.tags))
        else:
            tags = self.log10_config.tags

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
                "orig_qualname": "Completion.create" if kind == Kind.text else "ChatCompletion.create",
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
                "organization_id": self.log10_config.org_id,
                "response": json.dumps(response),
                "status": "finished",
                "duration": duration_sec,
                "stacktrace": json.dumps(stacktrace),
            },
        )


class NoopLLM(LLM):
    def __init__(self, hparams: dict = None, log10_config=None):
        pass

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        logging.info("Received chat completion requst: " + str(messages))
        return ChatCompletion(role="assistant", content="I'm not a real LLM")

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        logging.info("Received text completion requst: " + prompt)
        return TextCompletion(text="I'm not a real LLM")
