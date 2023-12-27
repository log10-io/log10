import os
import time

import together

from log10.llm import LLM, Kind, Log10Config, TextCompletion
from log10.utils import merge_hparams


together.api_key = os.environ.get("TOGETHER_API_KEY")


def llama_2_70b_chat(prompt: str, hparams: dict = None, log10_config: Log10Config = None) -> str:
    """
    Example:
        >>> from log10.llm import Log10Config
        >>> from log10.together import llama_2_70b_chat
        >>> response = llama_2_70b_chat("Hello, how are you?", {"temperature": 0.3, "max_tokens": 10}, log10_config=Log10Config())
        >>> print(response)
    """
    return Together({"model": "togethercomputer/llama-2-70b-chat"}, log10_config).text(prompt, hparams)


class Together(LLM):
    """
    Example:
        >>> from log10.llm import Log10Config
        >>> from log10.together import Together
        >>> llm = Together({"model": "togethercomputer/llama-2-70b-chat"}, log10_config=Log10Config())
        >>> response = llm.text("Hello, how are you?", {"temperature": 0.3, "max_tokens": 10})
        >>> print(response)

    For more information on Together Complete, see https://docs.together.ai/reference/complete-1
    """

    def __init__(self, hparams: dict = None, log10_config: Log10Config = None):
        super().__init__(hparams, log10_config)

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        request = self.text_request(prompt, hparams)
        openai_request = {
            **request,
        }

        start_time = time.perf_counter()
        self.completion_id = self.log_start(openai_request, Kind.text)
        completion = together.Complete.create(**request)

        response = self._prepare_response(completion)

        self.log_end(
            self.completion_id,
            response,
            time.perf_counter() - start_time,
        )

        return TextCompletion(text=response["choices"][0]["text"], response=response)

    def text_request(self, prompt: str, hparams: dict = None) -> dict:
        merged_hparams = merge_hparams(hparams, self.hparams)
        return {"prompt": prompt, **merged_hparams}

    def _prepare_response(self, completion: dict) -> dict:
        response = {
            "id": completion["id"],
            "object": "text_completion",
            "model": completion["model"],
            "choices": [
                {
                    "index": 0,
                    "text": completion["output"]["choices"][0]["text"],
                    "logprobs": completion["args"]["logprobs"],
                    "finish_reason": None,
                }
            ],
            "usage": None,
        }
        return response
