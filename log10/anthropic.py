import os
from copy import deepcopy
from typing import List
from log10.llm import LLM, ChatCompletion, Message, TextCompletion


from anthropic import HUMAN_PROMPT, AI_PROMPT
import anthropic

from log10.load import log10

log10(anthropic)


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
        completion = self.client.completion(
            prompt=prompt, stop_sequences=[HUMAN_PROMPT], **merged_hparams
        )
        content = completion["completion"]
        return ChatCompletion(role="assistant", content=content)

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]
        completion = self.client.completion(prompt=prompt, **merged_hparams)
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
