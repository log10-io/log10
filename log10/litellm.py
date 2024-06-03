import logging
from typing import List, Optional

from log10.llm import LLM, Kind, Log10Config
from log10.load import last_completion_response_var


try:
    from litellm.integrations.custom_logger import CustomLogger
except ImportError as error:
    msg = "To use Log10LitellmLogger to log LiteLLM completions, please install litellm using 'pip install log10-io[litellm]'"
    raise ImportError(msg) from error

logging.basicConfig()
logger = logging.getLogger("log10")


class Log10LitellmLogger(CustomLogger, LLM):
    """
    Example:
        >>> import litellm
        >>> from log10.litellm import Log10LitellmLogger
        >>> log10_handler = Log10LitellmLogger()
        >>> litellm.callbacks = [log10_handler]
        >>> response = litellm.completion(model="gpt-3.5-turbo", messages=[{ "role": "user", "content": "Count to 10."}], stream=True)
        >>> for chunk in response:
        >>>     if chunk.choices[0].delta.content:
        >>>          print(chunk.choices[0].delta.content, end="", flush=True)
    Example:
        >>> import litellm
        >>> from log10.litellm import Log10LitellmLogger
        >>> log10_handler = Log10LitellmLogger()
        >>> litellm.callbacks = [log10_handler]
        >>> response = litellm.completion(model="gpt-3.5-turbo", messages=[{ "role": "user", "content": "What's the next number, 1, 3, 5, 7? Say the number only."}])
        >>> print(response.choices[0].message.content)
    """

    runs = {}
    tags = []

    def __init__(self, log10_config: Optional[dict] = None, tags: List[str] = []) -> None:
        CustomLogger.__init__(self)

        log10_config = log10_config or Log10Config()
        self.tags = tags
        LLM.__init__(self, log10_config=log10_config, hparams=None)
        if log10_config.DEBUG:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    def log_pre_api_call(self, model, messages, kwargs):
        logger.debug(
            f"**\n**log_pre_api_call**\n**\n: model:\n {model} \n\n messages:\n {messages} \n\n rest: {kwargs}"
        )

        request = kwargs.get("additional_args").get("complete_input_dict").copy()
        request["messages"] = messages.copy()
        completion_id = self.log_start(request, Kind.chat, self.tags)
        last_completion_response_var.set({"completionID": completion_id})
        litellm_call_id = kwargs.get("litellm_call_id")
        self.runs[litellm_call_id] = {
            "kind": Kind.chat,
            "completion_id": completion_id,
            "model": model,
        }

    def log_post_api_call(self, kwargs, response_obj, start_time, end_time):
        pass

    def log_stream_event(self, kwargs, response_obj, start_time, end_time):
        pass

    def log_success_event(self, kwargs, response_obj, start_time, end_time):
        logger.debug(
            f"**\n**log_success_event**\n**\n: response_obj:\n {response_obj} \n\n start_time:\n {start_time} \n\n end_time: {end_time}"
        )
        litellm_call_id = kwargs.get("litellm_call_id")
        run = self.runs.get(litellm_call_id, None)
        duration = (end_time - start_time).total_seconds()

        completion_id = run["completion_id"]
        last_completion_response_var.set({"completionID": completion_id})
        self.log_end(completion_id, response_obj.dict(), duration)

    def log_failure_event(self, kwargs, response_obj, start_time, end_time):
        update_log_row = {
            "status": "failed",
            "failure_kind": type(kwargs["exception"]).__name__,
            "failure_reason": kwargs["exception"].message,
        }

        litellm_call_id = kwargs.get("litellm_call_id")
        run = self.runs.get(litellm_call_id, None)
        self.api_request(
            f"/api/completions/{run['completion_id']}",
            "POST",
            update_log_row,
        )

    #### ASYNC #### - for acompletion/aembeddings

    async def async_log_stream_event(self, kwargs, response_obj, start_time, end_time):
        pass

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        if kwargs["call_type"] == "completion":
            return

        logger.debug(
            f"**\n**async_log_success_event**\n**\n: kwargs:\n {kwargs} response_obj:\n {response_obj} \n\n {start_time} \n\n duration: {end_time - start_time}"
        )
        self.log_success_event(kwargs, response_obj, start_time, end_time)

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        if kwargs["call_type"] == "completion":
            return

        self.log_failure_event(kwargs, response_obj, start_time, end_time)
