from copy import deepcopy
import time
from typing import List
import openai
from log10.llm import LLM, ChatCompletion, Kind, Message, TextCompletion, merge_hparams

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
        
        completion_id = self.log_start(request, Kind.chat)

        logging.info(f"Logging completion {completion_id}")

        start_time = time.perf_counter()
        completion = openai.ChatCompletion.create(**request)
        duration = time.perf_counter() - start_time

        self.log_end(completion_id, completion, duration)

        return ChatCompletion(
            role=completion.choices[0]["message"]["role"],
            content=completion.choices[0]["message"]["content"],
            response=completion,
        )

    def chat_request(self, messages: List[Message], hparams: dict = None) -> dict:
        merged_hparams = merge_hparams(hparams, self.hparams)
        return {
            "messages": [message.to_dict() for message in messages],
            **merged_hparams,
        }

    @backoff.on_exception(backoff.expo, (RateLimitError, APIConnectionError))
    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        request = self.text_request(prompt, hparams)

        completion_id = self.log_start(request, Kind.text)

        start_time = time.perf_counter()
        completion = openai.Completion.create(**request)
        duration = time.perf_counter() - start_time

        self.log_end(completion_id, completion, duration)

        return TextCompletion(text=completion.choices[0].text, response=completion)

    def text_request(self, prompt: str, hparams: dict = None) -> dict:
        merged_hparams = merge_hparams(hparams, self.hparams)
        output = {"prompt": prompt, **merged_hparams}
        logging.debug(f"returning request {output}")
        return output
