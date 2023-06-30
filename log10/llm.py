from abc import ABC, abstractmethod
from enum import Enum

from anthropic import HUMAN_PROMPT, AI_PROMPT

Role = Enum("Role", ["system", "assistant", "user"])
Kind = Enum("Kind", ["chat", "text"])

from typing import List

import logging


class Message(ABC):
    def __init__(
        self, role: Role, content: str, id: str = None, completion: str = None
    ):
        self.id = id
        self.role = role
        self.content = content
        self.completion = completion


class Completion(ABC):
    pass


class ChatCompletion(Completion):
    def __init__(self, role: str, content: str, completion_id: str = None):
        self.role = role
        self.content = content
        self.completion_id = completion_id

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
        }


class TextCompletion(Completion):
    def __init__(self, text):
        self._text = text

    def completion_id(self) -> str:
        return self.output["completion_id"]

    def text(self) -> str:
        return self._text

    def to_dict(self) -> dict:
        return self.output


class LLM(ABC):
    @abstractmethod
    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        raise Exception("Not implemented")

    @abstractmethod
    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
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


class OpenAI(LLM):
    def __init__(self):
        pass

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        pass

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        pass


class Anthropic(LLM):
    def __init__(self):
        pass

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        pass

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
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
