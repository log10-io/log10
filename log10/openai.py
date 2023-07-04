from copy import deepcopy
from typing import List
import openai
from log10.llm import LLM, ChatCompletion, Message, TextCompletion

import logging


class OpenAI(LLM):
    def __init__(self, hparams: dict = None):
        self.hparams = hparams

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        completion = openai.ChatCompletion.create(
            **self.chat_request(messages, hparams)
        )

        return ChatCompletion(
            role=completion.choices[0]["message"]["role"],
            content=completion.choices[0]["message"]["content"],
            response=completion,
        )

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
        request = self.text_request(prompt, hparams)
        logging.info(f"sending request: {request}")
        completion = openai.Completion.create(**request)
        logging.info(f"received response: {completion}")
        return TextCompletion(text=completion.choices[0].text, response=completion)

    def text_request(self, prompt: str, hparams: dict = None) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]
        output = {"prompt": prompt, **merged_hparams}
        logging.info(f"returning request {output}")
        return output
