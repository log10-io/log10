from abc import ABC, abstractmethod
from copy import deepcopy
from enum import Enum
import os

from anthropic import HUMAN_PROMPT, AI_PROMPT

Role = Enum("Role", ["system", "assistant", "user"])
Kind = Enum("Kind", ["chat", "text"])

from typing import List

import json

import logging
from log10.load import log10
import openai
import anthropic

# log10(openai)
# log10(anthropic)


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

    def __str__(self) -> str:
        return json.dumps(self.to_dict())


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
    def __init__(self, hparams: dict = None):
        self.hparams = hparams

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]

        completion = openai.ChatCompletion.create(
            messages=[message.to_dict() for message in messages], **merged_hparams
        )

        return ChatCompletion(
            role=completion.choices[0]["message"]["role"],
            content=completion.choices[0]["message"]["content"],
        )

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]

        completion = openai.Completion.create(prompt=prompt, **merged_hparams)

        return TextCompletion(text=completion.choices[0].text)


class Anthropic(LLM):
    def __init__(self, hparams: dict = None):
        self.client = anthropic.Client(os.environ["ANTHROPIC_API_KEY"])
        self.hparams = hparams

        if "max_tokens_to_sample" not in self.hparams:
            self.hparams["max_tokens_to_sample"] = 1024

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]
        prompt = Anthropic.convert_history_to_claude(messages)
        completion = self.client.completion(prompt=prompt, **hparams)
        content = completion["completion"]
        return ChatCompletion(role="assistant", content=content)

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]
        completion = self.client.completion(prompt=prompt, **hparams)
        content = completion["completion"]
        return TextCompletion(text=content)

    def convert_history_to_claude(messages: List[Message]):
        text = ""
        for message in messages:
            # Anthropic doesn't support a system prompt OOB
            if message.role == "user" or message.role == "system":
                text += HUMAN_PROMPT
            elif message.role == "assistant":
                text += AI_PROMPT
            text += f"{message.content}"
        text += AI_PROMPT
        return text
