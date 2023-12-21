import time
import uuid

from mcli import predict

from log10.llm import LLM, Kind, Log10Config, TextCompletion
from log10.utils import merge_hparams


def llama_2_70b_chat(prompt: str, hparams: dict = None, log10_config: Log10Config = None) -> str:
    """
    Example:
        >>> from log10.llm import Log10Config
        >>> from log10.mosaicml import llama_2_70b_chat
        >>> response = llama_2_70b_chat("Hello, how are you?", {"temperature": 0.3, "max_new_tokens": 10}, log10_config=Log10Config())
        >>> print(response)
    """
    return MosaicML({"model": "llama2-70b-chat/v1"}, log10_config).text(prompt, hparams)


class MosaicML(LLM):
    """
    Example:
        >>> from log10.llm import Log10Config
        >>> from log10.mosaicml import MosaicML
        >>> llm = MosaicML({"model": "llama2-70b-chat/v1"}, log10_config=Log10Config())
        >>> response = llm.text("Hello, how are you?", {"temperature": 0.3, "max_new_tokens": 10})
        >>> print(response)

    For more information on MosaicML Complete, see https://docs.mosaicml.com/en/latest/inference.html#text-completion-request-endpoint
    """

    mosaicml_host_url = "https://models.hosted-on.mosaicml.hosting/"

    def __init__(self, hparams: dict = None, log10_config: Log10Config = None):
        super().__init__(hparams, log10_config)

    def text(self, prompt: str, hparams: dict = None) -> TextCompletion:
        request = self.text_request(prompt, hparams)
        self.model = request.get("model")
        openai_request = {
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
        return response
