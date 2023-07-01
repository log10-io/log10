from copy import deepcopy
from typing import List

import openai
from log10.llm import LLM, ChatCompletion, Message, TextCompletion
from log10.load import log10

log10(openai)


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
