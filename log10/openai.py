import logging
import time
from copy import deepcopy
from typing import List

# for exponential backoff
import backoff
import openai
from openai.error import APIConnectionError, RateLimitError

from log10.llm import LLM, ChatCompletion, Message, TextCompletion


class OpenAI(LLM):
    def __init__(self, hparams: dict = None, log10_config=None):
        super().__init__(hparams, log10_config)

    @backoff.on_exception(backoff.expo, (RateLimitError, APIConnectionError))
    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        completion = openai.ChatCompletion.create(**self.chat_request(messages, hparams))

        return ChatCompletion(
            role=completion.choices[0]['message']['role'],
            content=completion.choices[0]['message']['content'],
            response=completion,
        )

    def chat_request(self, messages: List[Message], hparams: dict = None) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]

        return {
            'messages': [message.to_dict() for message in messages],
            **merged_hparams,
        }

    @backoff.on_exception(backoff.expo, (RateLimitError, APIConnectionError))
    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        request = self.text_request(prompt, hparams)
        completion = openai.Completion.create(**request)
        return TextCompletion(text=completion.choices[0].text, response=completion)

    def text_request(self, prompt: str, hparams: dict = None) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]
        output = {'prompt': prompt, **merged_hparams}
        return output
