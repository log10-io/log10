import os
from copy import deepcopy
import time
from typing import List
from log10.llm import LLM, ChatCompletion, Kind, Message, TextCompletion, merge_hparams


from anthropic import HUMAN_PROMPT, AI_PROMPT
import anthropic

import uuid


class Anthropic(LLM):
    def __init__(
        self, hparams: dict = None, skip_initialization: bool = False, log10_config=None
    ):
        super().__init__(hparams, log10_config)

        if not skip_initialization:
            self.client = anthropic.Anthropic()

        if "max_tokens_to_sample" not in self.hparams:
            self.hparams["max_tokens_to_sample"] = 1024

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        request = self.chat_request(messages, hparams)
        completion = self.client.completions.create(**request)
        content = completion.completion
        return ChatCompletion(role="assistant", content=content)

    def chat_request(self, messages: List[Message], hparams: dict = None) -> dict:
        merged_hparams = merge_hparams(hparams, self.hparams)

        # NOTE: That we may have to convert this to openai messages, if we want
        #       to use the same log viewer for all chat based models.
        prompt = Anthropic.convert_history_to_claude(messages)
        return {"prompt": prompt, "stop_sequences": [HUMAN_PROMPT], **merged_hparams}

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        request = self.text_request(prompt, hparams)
        completion = self.client.completions.create(**request)
        text = completion.completion
        return TextCompletion(text=text)

    def text_request(self, prompt: str, hparams: dict = None) -> TextCompletion:
        merged_hparams = merge_hparams(hparams, self.hparams)
        return {
            "prompt": HUMAN_PROMPT + prompt + "\n" + AI_PROMPT,
            "stop_sequences": [HUMAN_PROMPT],
            **merged_hparams,
        }

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
