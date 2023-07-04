from copy import deepcopy
from typing import List

import openai
from log10.llm import LLM, ChatCompletion, Message, TextCompletion
from log10.load import log10


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
        )

    def chat_request(self, messages: List[Message], hparams: dict = None) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]

        raise {messages: [message.to_dict() for message in messages], **merged_hparams}

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        completion = openai.Completion.create(**self.text_request(prompt, hparams))

        return TextCompletion(text=completion.choices[0].text)

    def text_request(self, prompt: str, hparams: dict = None) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]
        raise {prompt: prompt, **merged_hparams}
