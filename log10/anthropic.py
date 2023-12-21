import logging
import time
from typing import List

import anthropic
from anthropic import AI_PROMPT, HUMAN_PROMPT

from log10.llm import LLM, ChatCompletion, Kind, Message, TextCompletion
from log10.utils import merge_hparams


class Anthropic(LLM):
    def __init__(self, hparams: dict = None, skip_initialization: bool = False, log10_config=None):
        super().__init__(hparams, log10_config)

        if not skip_initialization:
            self.client = anthropic.Anthropic()
        self.hparams = hparams

        if "max_tokens_to_sample" not in self.hparams:
            self.hparams["max_tokens_to_sample"] = 1024

    def chat(self, messages: List[Message], hparams: dict = None) -> ChatCompletion:
        """
        Example:
            >>> from log10.llm import Log10Config, Message
            >>> from log10.anthropic import Anthropic
            >>> llm = Anthropic({"model": "claude-1"}, log10_config=Log10Config())
            >>> response = llm.chat([Message(role="user", content="Hello, how are you?")])
            >>> print(response)
            >>> print(f"Duration: {llm.last_duration()}")
        """
        chat_request = self.chat_request(messages, hparams)

        openai_request = {
            "messages": [message.to_dict() for message in messages],
            **chat_request,
        }

        completion_id = self.log_start(openai_request, Kind.chat)

        start_time = time.perf_counter()
        completion = self.client.completions.create(**chat_request)
        content = completion.completion

        response = Anthropic.prepare_response(chat_request["prompt"], completion, "chat")

        self.log_end(
            completion_id,
            response,
            time.perf_counter() - start_time,
        )

        return ChatCompletion(role="assistant", content=content, response=response)

    def chat_request(self, messages: List[Message], hparams: dict = None) -> dict:
        merged_hparams = merge_hparams(hparams, self.hparams)

        # NOTE: That we may have to convert this to openai messages, if we want
        #       to use the same log viewer for all chat based models.
        prompt = Anthropic.convert_history_to_claude(messages)
        return {"prompt": prompt, "stop_sequences": [HUMAN_PROMPT], **merged_hparams}

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        """
        Example:
            >>> from log10.llm import Log10Config
            >>> from log10.anthropic import Anthropic
            >>> llm = Anthropic({"model": "claude-1"}, log10_config=Log10Config())
            >>> response = llm.text("Foobarbaz")
            >>> print(response)
            >>> print(f"Duration: {llm.last_duration()}")
        """
        text_request = self.text_request(prompt, hparams)

        openai_request = {
            **text_request,
            "prompt": prompt,
        }

        start_time = time.perf_counter()
        completion_id = self.log_start(openai_request, Kind.text)
        completion = self.client.completions.create(**text_request)
        text = completion.completion

        response = Anthropic.prepare_response(text_request["prompt"], completion, "text")

        self.log_end(
            completion_id,
            response,
            time.perf_counter() - start_time,
        )

        logging.info("Returning text completion")
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

    def convert_claude_to_messages(prompt: str):
        pass

    @staticmethod
    def create_tokens_usage(prompt: str, completion: str):
        client = anthropic.Anthropic()
        prompt_tokens = client.count_tokens(prompt)
        completion_tokens = client.count_tokens(completion)
        total_tokens = prompt_tokens + completion_tokens

        # Imitate OpenAI usage format.
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    @staticmethod
    def prepare_response(prompt: str, completion: anthropic.types.Completion, type: str = "text") -> dict:
        if completion.stop_reason == "stop_sequence":
            reason = "stop"
        elif completion.stop_reason == "max_tokens":
            reason = "length"

        tokens_usage = Anthropic.create_tokens_usage(prompt, completion.completion)
        response = {
            "id": completion.model_extra["log_id"],
            "object": "completion",
            "model": completion.model,
            "choices": [
                {
                    "index": 0,
                    "finish_reason": reason,
                }
            ],
            "usage": tokens_usage,
        }
        if type == "text":
            response["choices"][0]["text"] = completion.completion
        elif type == "chat":
            response["choices"][0]["message"] = {
                "role": "assistant",
                "content": completion.completion,
            }
        return response
