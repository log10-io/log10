import os
from copy import deepcopy
from typing import List
from log10.llm import LLM, ChatCompletion, Message, TextCompletion


from anthropic import HUMAN_PROMPT, AI_PROMPT
import anthropic

import uuid

import logging


class Anthropic(LLM):
    def __init__(self, hparams: dict = None, skip_initialization: bool = False):
        if not skip_initialization:
            self.client = anthropic.Anthropic()
        self.hparams = hparams

        if "max_tokens_to_sample" not in self.hparams:
            self.hparams["max_tokens_to_sample"] = 1024

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        completion = self.client.completions.create(
            **self.chat_request(messages, hparams)
        )
        content = completion.completion

        reason = "stop"
        if completion.stop_reason == "stop_sequence":
            reason = "stop"
        elif completion.stop_reason == "max_tokens":
            reason = "length"

        # Imitate OpenAI reponse format.
        response = {
            "id": str(uuid.uuid4()),
            "object": "chat.completion",
            "model": completion.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": reason,
                }
            ],
        }

        return ChatCompletion(role="assistant", content=content, response=response)

    def chat_request(self, messages: List[Message], hparams: dict = None) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]

        # NOTE: That we may have to convert this to openai messages, if we want
        #       to use the same log viewer for all chat based models.
        prompt = Anthropic.convert_history_to_claude(messages)
        return {"prompt": prompt, "stop_sequences": [HUMAN_PROMPT], **merged_hparams}

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        completion = self.client.completions.create(
            **self.text_request(prompt, hparams)
        )
        text = completion.completion

        # Imitate OpenAI reponse format.
        reason = "stop"
        if completion.stop_reason == "stop_sequence":
            reason = "stop"
        elif completion.stop_reason == "max_tokens":
            reason = "length"

        # Imitate OpenAI reponse format.
        response = {
            "id": str(uuid.uuid4()),
            "object": "text_completion",
            "model": completion.model,
            "choices": [
                {
                    "index": 0,
                    "text": text,
                    "logprobs": None,
                    "finish_reason": reason,
                }
            ],
        }
        logging.info("Returning text completion")
        return TextCompletion(text=text, response=response)

    def text_request(self, prompt: str, hparams: dict = None) -> TextCompletion:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]
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

    def convert_claude_to_messages(prompt: str):
        pass
