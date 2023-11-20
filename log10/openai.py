import time
from copy import deepcopy

# for exponential backoff
import backoff
import openai
from openai import error

from log10.llm import LLM, ChatCompletion, Kind, Message, TextCompletion

RETRY_ERROR_TYPES = (
    error.APIConnectionError,
    error.APIError,
    error.RateLimitError,
    error.ServiceUnavailableError,
    error.Timeout,
)


class OpenAI(LLM):
    def __init__(self, hparams: dict, log10_config=None):
        super().__init__(hparams, log10_config)

    @backoff.on_exception(backoff.expo, RETRY_ERROR_TYPES)
    def chat(self, messages: list[Message], hparams: dict) -> ChatCompletion:
        request = self.chat_request(messages, hparams)

        start_time = time.perf_counter()
        completion = openai.ChatCompletion.create(**request)

        self.completion_id = self.log_start(request, Kind.chat)

        response = ChatCompletion(
            role=completion.choices[0]["message"]["role"],
            content=completion.choices[0]["message"]["content"],
            response=completion,
        )

        self.log_end(
            self.completion_id,
            completion,
            time.perf_counter() - start_time,
        )

        return response

    def chat_request(self, messages: list[Message], hparams: dict) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]

        return {
            "messages": [message.to_dict() for message in messages],
            **merged_hparams,
        }

    @backoff.on_exception(backoff.expo, RETRY_ERROR_TYPES)
    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        request = self.text_request(prompt, hparams)

        start_time = time.perf_counter()
        completion_id = self.log_start(request, Kind.text)

        completion = openai.Completion.create(**request)
        response = TextCompletion(text=completion.choices[0].text, response=completion)

        self.log_end(
            completion_id,
            completion,
            int(time.perf_counter() - start_time),
        )

        return response

    def text_request(self, prompt: str, hparams: dict) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]
        output = {"prompt": prompt, **merged_hparams}
        return output
