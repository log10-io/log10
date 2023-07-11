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

        # Log a request which conforms wiht OpenAI.
        merged_hparams = merge_hparams(hparams, self.hparams)
        completion_id = self.log_start(
            {"messages": [message.to_dict() for message in messages], **merged_hparams},
            Kind.chat,
        )

        # Carry out completion
        start_time = time.perf_counter()
        completion = self.client.completions.create(**request)
        duration = time.perf_counter() - start_time
        content = completion.completion

        # Imitate OpenAI reponse format and store.
        reason = "stop"
        if completion.stop_reason == "stop_sequence":
            reason = "stop"
        elif completion.stop_reason == "max_tokens":
            reason = "length"
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
        self.log_end(completion_id, response, duration)

        return ChatCompletion(role="assistant", content=content, response=response)

    def chat_request(self, messages: List[Message], hparams: dict = None) -> dict:
        merged_hparams = merge_hparams(hparams, self.hparams)

        # NOTE: That we may have to convert this to openai messages, if we want
        #       to use the same log viewer for all chat based models.
        prompt = Anthropic.convert_history_to_claude(messages)
        return {"prompt": prompt, "stop_sequences": [HUMAN_PROMPT], **merged_hparams}

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        request = self.text_request(prompt, hparams)

        #
        # Log a request which conforms wiht OpenAI.
        #
        # Anthropic prompts have to start with HUMAN_PROMPT <request> AI_PROMPT.
        # We don't store this, to make it possible to rerun completions with other LLMs.
        original_prompt = request["prompt"]
        request["prompt"] = prompt
        completion_id = self.log_start(request, Kind.text)
        request["pompt"] = original_prompt

        start_time = time.perf_counter()
        completion = self.client.completions.create(
            **request
        )
        duration = time.perf_counter() - start_time

        text = completion.completion

        #
        # Imitate OpenAI response format.
        #
        reason = "stop"
        if completion.stop_reason == "stop_sequence":
            reason = "stop"
        elif completion.stop_reason == "max_tokens":
            reason = "length"
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
        self.log_end(completion_id, response, duration)

        return TextCompletion(text=text, response=response)

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
