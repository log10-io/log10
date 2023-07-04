from abc import ABC, abstractmethod
from enum import Enum
import os

Role = Enum("Role", ["system", "assistant", "user"])
Kind = Enum("Kind", ["chat", "text"])

from typing import List

import json

import logging


class Message(ABC):
    def __init__(
        self, role: Role, content: str, id: str = None, completion: str = None
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
    def __init__(
        self, role: str, content: str, response: dict = None, completion_id: str = None
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
    def __init__(self, text: str, response: dict = None, completion_id=None):
        self._text = text
        self.response = response
        self.completion_id = completion_id

    def text(self) -> str:
        return self._text


class LLM(ABC):
    @abstractmethod
    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        raise Exception("Not implemented")

    @abstractmethod
    def text_request(self, prompt: str, hparams: dict = None) -> dict:
        raise Exception("Not implemented")

    @abstractmethod
    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        raise Exception("Not implemented")

    @abstractmethod
    def chat_request(self, messages: List[Message], hparams: dict = None) -> dict:
        raise Exception("Not implemented")


class HParams(ABC):
    pass


class NoopLLM(LLM):
    def __init__(self):
        pass

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        logging.info("Received chat completion requst: " + str(messages))
        return ChatCompletion(role="assistant", content="I'm not a real LLM")

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        logging.info("Received text completion requst: " + prompt)
        return TextCompletion(text="I'm not a real LLM")
