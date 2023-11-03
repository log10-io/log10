import time
import uuid

from copy import deepcopy
from log10.llm import LLM, Kind, Log10Config, TextCompletion
from mcli import predict


class MosaicML(LLM):
    """
    MosaicML models list: https://docs.mosaicml.com/en/latest/inference.html#text-completion-request-endpoint
    Example:
        >>> from log10.llm import Log10Config
        >>> from log10.mosaicml import MosaicML
        >>> llm = MosaicML({"model": "llama2-70b-chat/v1"}, log10_config=Log10Config())
        >>> response = llm.text("Hello, how are you?", {"temperature": 0.3, "max_new_tokens": 10})
        >>> print(response)
    """

    mosaicml_host_url = "https://models.hosted-on.mosaicml.hosting/"

    def __init__(self, hparams: dict = None, log10_config: Log10Config = None):
        super().__init__(hparams, log10_config)

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        request = self.text_request(prompt, hparams)
        self.model = request.get("model")
        openai_request = {
            "prompt": prompt,
            **request,
            "model": f"mosaicml/{self.model}",
        }

        start_time = time.perf_counter()
        self.completion_id = self.log_start(openai_request, Kind.text)
        completion = predict(
            f"{self.mosaicml_host_url}{self.model}",
            {
                "inputs": [prompt],
                "parameters": request,
            },
        )

        # Imitate OpenAI reponse format.
        response = {
            "id": str(uuid.uuid4()),
            "object": "text_completion",
            "model": f"mosaicml/{self.model}",
            "choices": [
                {
                    "index": 0,
                    "text": completion["outputs"][0],
                    "logprobs": None,
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

        return TextCompletion(text=response["choices"][0]["text"], response=response)

    def text_request(self, prompt: str, hparams: dict = None) -> dict:
        merged_hparams = deepcopy(self.hparams)
        if hparams:
            for hparam in hparams:
                merged_hparams[hparam] = hparams[hparam]
        return {"prompt": prompt, **merged_hparams}

    def _prepare_response(self, completion) -> dict:
        return completion["outputs"][0]
