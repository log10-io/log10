from abc import ABC, abstractmethod
from enum import Enum

from anthropic import HUMAN_PROMPT, AI_PROMPT

Role = Enum("Role", ["system", "assistant", "user"])
Kind = Enum("Kind", ["chat", "text"])

from typing import List


class Message(ABC):
    def __init__(self, role: Role, content: str, id: str, completion: str = None):
        self.id = id
        self.role = role
        self.content = content
        self.completion = None


class Completion(ABC):
    @abstractmethod
    def completion_id(self) -> str:
        pass

    @abstractmethod
    def to_dict(self) -> dict:
        pass


class ChatCompletion(Completion):
    def __init__(self, message: dict):
        self.message = message

    def completion_id(self) -> str:
        return self.message["completion"]

    def to_dict(self) -> dict:
        return self.message


class TextCompletion(Completion):
    def __init__(self, output: dict):
        self.output = output

    def completion_id(self) -> str:
        return self.output["completion_id"]

    def to_dict(self) -> dict:
        return self.output


class LLM(ABC):
    @abstractmethod
    def text(self, prompt: str) -> TextCompletion:
        raise Exception("Not implemented")

    @abstractmethod
    def chat(self, messages: List[Message]) -> ChatCompletion:
        raise Exception("Not implemented")


class HParams(ABC):
    pass


def convert_history_to_claude(history):
    text = ""
    for item in history:
        # Anthropic doesn't support a system prompt OOB
        if item["role"] == "user" or item["role"] == "system":
            text += HUMAN_PROMPT
        elif item["role"] == "assistant":
            text += AI_PROMPT
        text += f"{item['content']}"
    text += AI_PROMPT
    return text
