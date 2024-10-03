import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from langchain.callbacks.base import BaseCallbackHandler
from langchain.schema import AgentAction, AgentFinish, AIMessage, BaseMessage, HumanMessage, LLMResult, SystemMessage

from log10.llm import LLM, Kind, Message


logging.basicConfig()
logger = logging.getLogger("log10")


def kwargs_to_hparams(kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """Convert kwargs to hparams."""
    hparams = {}
    if "temperature" in kwargs:
        hparams["temperature"] = kwargs["temperature"]
    if "top_p" in kwargs:
        hparams["top_p"] = kwargs["top_p"]
    if "top_k" in kwargs:
        hparams["top_k"] = kwargs["top_k"]
    if "max_tokens" in kwargs:
        hparams["max_tokens"] = kwargs["max_tokens"]
    if "max_tokens_to_sample" in kwargs:
        hparams["max_tokens"] = kwargs["max_tokens_to_sample"]
    if "frequency_penalty" in kwargs:
        hparams["frequency_penalty"] = kwargs["frequency_penalty"]
    if "presence_penalty" in kwargs:
        hparams["presence_penalty"] = kwargs["presence_penalty"]
    return hparams


def get_log10_messages(langchain_messages: List[BaseMessage]) -> List[Message]:
    role_map = {AIMessage: "assistant", HumanMessage: "user", SystemMessage: "system"}

    for m in langchain_messages:
        logger.debug(f"message: {m}")
        if type(m) not in role_map:
            raise BaseException(f"Unsupported message type {type(m)}. Supported types: {list(role_map.values())}")

    return [Message(role=role_map[type(m)], content=m.content) for m in langchain_messages]


class Log10Callback(BaseCallbackHandler, LLM):
    """Callback Handler that prints to std out."""

    def __init__(self, log10_config: Optional[dict] = None) -> None:
        """Initialize callback handler."""
        super().__init__(log10_config=log10_config, hparams=None)
        self.runs = {}

        if log10_config.DEBUG:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        """Print out the prompts."""
        logger.debug(
            f"**\n**on_llm_start**\n**\n: serialized:\n {serialized} \n\n prompts:\n {prompts} \n\n rest: {kwargs}"
        )
        kwargs = serialized.get("kwargs", {})
        hparams = kwargs_to_hparams(kwargs)

        model = kwargs.get("model_name", None)
        if model is None:
            model = kwargs.get("model", None)
        if model is None:
            raise BaseException("No model found in serialized or kwargs")

        if len(prompts) != 1:
            raise BaseException("Only support one prompt at a time")

        request = {"model": model, "prompt": prompts[0], **hparams}

        logger.debug(f"request: {request}")

        completion_id = self.log_start(request, Kind.text, tags)

        self.runs[run_id] = {
            "kind": Kind.text,
            "completion_id": completion_id,
            "start_time": time.perf_counter(),
            "model": model,
        }

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        logger.debug(
            f"**\n**on_chat_model_start**\n**\n: run_id:{run_id}\nserialized:\n{serialized}\n\nmessages:\n{messages}\n\nkwargs: {kwargs}"
        )

        #
        # Find model string
        #
        kwargs = serialized.get("kwargs", {})
        model = kwargs.get("model_name", None)
        if model is None:
            model = kwargs.get("model", None)
        if model is None:
            raise BaseException("No model found in serialized or kwargs")

        hparams = kwargs_to_hparams(kwargs)
        hparams["model"] = model

        logger.debug(f"hparams: {hparams}")

        if len(messages) != 1:
            raise BaseException("Only support one message at a time")

        # Convert messages to log10 format
        log10_messages = get_log10_messages(messages[0])

        request = {
            "messages": [message.to_dict() for message in log10_messages],
            **hparams,
        }
        logger.debug(f"request: {request}")

        completion_id = self.log_start(
            request,
            Kind.chat,
            tags,
        )

        self.runs[run_id] = {
            "kind": Kind.chat,
            "completion_id": completion_id,
            "start_time": time.perf_counter(),
            "model": model,
        }

        logger.debug(f"logged start with completion_id: {completion_id}")

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> None:
        """Do nothing."""
        # Find run in runs.
        run = self.runs.get(run_id, None)
        if run is None:
            raise BaseException("Could not find run in runs")

        if run["kind"] != Kind.chat and run["kind"] != Kind.text:
            raise BaseException("Only support chat kind")

        duration = time.perf_counter() - run["start_time"]

        # Log end
        if len(response.generations) != 1:
            raise BaseException("Only support one message at a time")
        if len(response.generations[0]) != 1:
            raise BaseException("Only support one message at a time")

        content = response.generations[0][0].text

        log10response = {}
        if run["kind"] == Kind.chat:
            log10response = {
                "id": str(uuid.uuid4()),
                "object": "chat.completion",
                "model": run["model"],
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
            }
        elif run["kind"] == Kind.text:
            log10response = {
                "id": str(uuid.uuid4()),
                "object": "text_completion",
                "model": run["model"],
                "choices": [
                    {
                        "index": 0,
                        "text": content,
                        "logprobs": None,
                        "finish_reason": "stop",
                    }
                ],
            }

        # Determine if we can provide usage metrics (token count).
        logger.debug(f"**** response: {response}")
        if response.llm_output is not None:
            token_usage = response.llm_output.get("token_usage")
            if token_usage is not None:
                log10response["usage"] = token_usage
                logger.debug(f"usage: {log10response['usage']}")

        logger.debug(f"**\n**on_llm_end**\n**\n: response:\n {log10response} \n\n rest: {kwargs}")
        self.log_end(run["completion_id"], log10response, duration)

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Do nothing."""
        logger.debug(f"token:\n {token} \n\n rest: {kwargs}")

    def on_llm_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Do nothing."""
        logger.debug(f"error:\n {error} \n\n rest: {kwargs}")

    def on_chain_start(self, serialized: Dict[str, Any], inputs: Dict[str, Any], **kwargs: Any) -> None:
        """Print out that we are entering a chain."""
        pass

    def on_chain_end(self, outputs: Dict[str, Any], **kwargs: Any) -> None:
        """Print out that we finished a chain."""
        pass

    def on_chain_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Do nothing."""
        pass

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any,
    ) -> None:
        """Do nothing."""
        pass

    def on_agent_action(self, action: AgentAction, color: Optional[str] = None, **kwargs: Any) -> Any:
        """Run on agent action."""
        pass

    def on_tool_end(
        self,
        output: str,
        color: Optional[str] = None,
        observation_prefix: Optional[str] = None,
        llm_prefix: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """If not the final action, print out observation."""
        pass

    def on_tool_error(self, error: Union[Exception, KeyboardInterrupt], **kwargs: Any) -> None:
        """Do nothing."""
        pass

    def on_text(
        self,
        text: str,
        color: Optional[str] = None,
        end: str = "",
        **kwargs: Any,
    ) -> None:
        """Run when agent ends."""
        pass

    def on_agent_finish(self, finish: AgentFinish, color: Optional[str] = None, **kwargs: Any) -> None:
        """Run on agent end."""
        pass
