import time
from copy import deepcopy
from importlib.metadata import version
from typing import List

import openai
from packaging.version import parse

from log10.llm import LLM, ChatCompletion, Kind, Message, TextCompletion


def is_openai_v1() -> bool:
    """Return whether OpenAI API is v1 or more."""
    _version = parse(version("openai"))
    return _version.major >= 1


class OpenAI(LLM):
    def __init__(self, hparams: dict = None, log10_config=None):
        assert is_openai_v1(), "OpenAI API version must be >= 1.0.0 to use log10.OpenAI class"
        super().__init__(hparams, log10_config)
        self._client = openai.OpenAI()

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        """
        Example:
            >>> from log10.llm import Log10Config, Message
            >>> from log10.openai import OpenAI
            >>> llm = OpenAI({"model": "gpt-3.5-turbo"}, log10_config=Log10Config())
            >>> response = llm.chat([Message(role="user", content="Hello")])
            >>> print(response)
        """
        request = self.chat_request(messages, hparams)

        start_time = time.perf_counter()
        completion = self._client.chat.completions.create(**request)

        self.completion_id = self.log_start(request, Kind.chat)

        response = ChatCompletion(
            role=completion.choices[0].message.role,
            content=completion.choices[0].message.content,
            response=completion,
        )

        self.log_end(
            self.completion_id,
            completion.model_dump(),
            time.perf_counter() - start_time,
        )

        return response

    def chat_request(self, messages: List[Message], hparams: dict = None) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]

        return {
            "messages": [message.to_dict() for message in messages],
            **merged_hparams,
        }

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        """
        Example:
            >>> from log10.llm import Log10Config
            >>> from log10.openai import OpenAI
            >>> llm = OpenAI({"model": "gpt-3.5-turbo-instruct"}, log10_config=Log10Config())
            >>> response = llm.text("This is a test.")
            >>> print(response)
        """
        request = self.text_request(prompt, hparams)

        start_time = time.perf_counter()
        completion_id = self.log_start(request, Kind.text)

        completion = self._client.completions.create(**request)
        response = TextCompletion(text=completion.choices[0].text, response=completion)

        self.log_end(
            completion_id,
            completion.model_dump(),
            time.perf_counter() - start_time,
        )

        return response

    def text_request(self, prompt: str, hparams: dict = None) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]
        output = {"prompt": prompt, **merged_hparams}
        return output
