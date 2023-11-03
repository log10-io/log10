import os
import time
import together

from copy import deepcopy
from log10.llm import LLM, Kind, Log10Config, TextCompletion

together.api_key = os.environ.get("TOGETHER_API_KEY")

class Together(LLM):
    """
    Example:
        >>> from log10.together import Together
        >>> llm = Together({"model": "togethercomputer/llama-2-70b-chat"})
        >>> response = llm.text("Hello, how are you?", {"temperature": 0.3, "max_tokens": 10})
        >>> print(response)
    """
    def __init__(self, hparams: dict = None, log10_config: Log10Config = None):
        super().__init__(hparams, log10_config)

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        request = self.text_request(prompt, hparams)
        openai_request = {
            "prompt": prompt,
            **request,
        }

        start_time = time.perf_counter()
        self.completion_id = self.log_start(openai_request, Kind.text)
        completion = together.Complete.create(**request)
        if completion['status'] != 'finished':
            raise Exception("Completion failed.")

        # Imitate OpenAI reponse format.
        response = {
            "id": completion['output']['request_id'],
            "object": "text_completion",
            "model": completion['model'],
            "choices": [
                {
                    "index": 0,
                    "text": completion['output']['choices'][0]['text'],
                    "logprobs": completion['args']['logprobs'],
                    "finish_reason": None,
                }
            ],
            "usage": None,
        }

        self.log_end(
            self.completion_id,
            response,
            time.perf_counter() - start_time,
        )

        return TextCompletion(text=response['choices'][0]['text'], response=response)

    def text_request(self, prompt: str, hparams: dict = None) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]
        return {"prompt": prompt, **merged_hparams}
