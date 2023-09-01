from copy import deepcopy
import time
from typing import List
import openai
from log10.llm import LLM, ChatCompletion, Kind, Message, TextCompletion

import logging

# for exponential backoff
import backoff
from openai.error import RateLimitError, APIConnectionError
import openai


class OpenAI(LLM):
    def __init__(self, hparams: dict = None, log10_config=None):
        super().__init__(hparams, log10_config)

    @backoff.on_exception(backoff.expo, (RateLimitError, APIConnectionError))
    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        request = self.chat_request(messages, hparams)

        start_time = time.perf_counter()
        completion = openai.ChatCompletion.create(**request)

        self.completion_id = self.log_start(request, Kind.chat)

        response = ChatCompletion(
            role=completion.choices[0]["message"]["role"],
            content=completion.choices[0]["message"]["content"],
            response=completion,
        )

        self.log_end(
            self.completion_id,
            completion,
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

    @backoff.on_exception(backoff.expo, (RateLimitError, APIConnectionError))
    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        request = self.text_request(prompt, hparams)

        start_time = time.perf_counter()
        completion_id = self.log_start(request, Kind.text)

        completion = openai.Completion.create(**request)
        response = TextCompletion(text=completion.choices[0].text, response=completion)

        self.log_end(
            completion_id,
            completion,
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
