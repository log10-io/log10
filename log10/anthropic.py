import time
from copy import deepcopy
from typing import List
from log10.llm import LLM, ChatCompletion, Kind, Message, TextCompletion


from anthropic import HUMAN_PROMPT, AI_PROMPT
import anthropic

import uuid

import logging


class Anthropic(LLM):
    def __init__(
        self, hparams: dict = None, skip_initialization: bool = False, log10_config=None
    ):
        super().__init__(hparams, log10_config)

        if not skip_initialization:
            self.client = anthropic.Anthropic()
        self.hparams = hparams

        if "max_tokens_to_sample" not in self.hparams:
            self.hparams["max_tokens_to_sample"] = 1024

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        chat_request = self.chat_request(messages, hparams)

        openai_request = {
            "messages": [message.to_dict() for message in messages],
            **chat_request,
        }

        completion_id = self.log_start(openai_request, Kind.chat)

        start_time = time.perf_counter()
        completion = self.client.completions.create(**chat_request)
        content = completion.completion

        reason = "stop"
        if completion.stop_reason == "stop_sequence":
            reason = "stop"
        elif completion.stop_reason == "max_tokens":
            reason = "length"

        tokens_usage = self.create_tokens_usage(chat_request["prompt"], content)

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
            "usage": tokens_usage,
        }

        self.log_end(
            completion_id,
            response,
            time.perf_counter() - start_time,
        )

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
        text_request = self.text_request(prompt, hparams)

        openai_request = {
            **text_request,
            "prompt": prompt,
        }

        start_time = time.perf_counter()
        completion_id = self.log_start(openai_request, Kind.text)
        completion = self.client.completions.create(**text_request)
        text = completion.completion

        # Imitate OpenAI reponse format.
        reason = "stop"
        if completion.stop_reason == "stop_sequence":
            reason = "stop"
        elif completion.stop_reason == "max_tokens":
            reason = "length"

        tokens_usage = self.create_tokens_usage(text_request["prompt"], text)

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
            "usage": tokens_usage,
        }

        self.log_end(
            completion_id,
            response,
            time.perf_counter() - start_time,
        )

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

    def create_tokens_usage(self, prompt: str, completion: str):
        prompt_tokens = self.client.count_tokens(prompt)
        completion_tokens = self.client.count_tokens(completion)
        total_tokens = prompt_tokens + completion_tokens

        # Imitate OpenAI usage format.
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
