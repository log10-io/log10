import time

import litellm
import pytest
from magentic import StreamedStr, prompt
from magentic.chat_model.litellm_chat_model import LitellmChatModel

from log10.litellm import Log10LitellmLogger
from tests.utils import _LogAssertion


log10_handler = Log10LitellmLogger(tags=["litellm_perplexity"])
litellm.callbacks = [log10_handler]

PERPLEXITY_MODEL = "perplexity/llama-3.1-sonar-small-128k-chat"


@pytest.mark.chat
def test_prompt(session):
    @prompt("What happened on this day?", model=LitellmChatModel(model=PERPLEXITY_MODEL))
    def llm() -> str: ...

    output = llm()
    assert isinstance(output, str)

    time.sleep(3)

    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.chat
@pytest.mark.stream
def test_prompt_stream(session):
    @prompt("What happened on this day?", model=LitellmChatModel(model=PERPLEXITY_MODEL))
    def llm() -> StreamedStr: ...

    response = llm()
    output = ""
    for chunk in response:
        output += chunk
    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()
