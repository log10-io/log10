import time

import litellm
import pytest
from magentic import StreamedStr, prompt
from magentic.chat_model.litellm_chat_model import LitellmChatModel

from log10.litellm import Log10LitellmLogger
from tests.utils import _LogAssertion


log10_handler = Log10LitellmLogger(tags=["litellm_perplexity"])
litellm.callbacks = [log10_handler]


@pytest.mark.skip("Unstable, will be fixed in a separate PR")
@pytest.mark.chat
def test_prompt(session, openai_compatibility_model):
    @prompt("What is 3 - 3?", model=LitellmChatModel(model=openai_compatibility_model))
    def llm() -> str: ...

    output = llm()
    assert isinstance(output, str)

    time.sleep(3)

    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.skip("Unstable, will be fixed in a separate PR")
@pytest.mark.chat
@pytest.mark.stream
def test_prompt_stream(session, openai_compatibility_model):
    @prompt("What is 3 * 3?", model=LitellmChatModel(model=openai_compatibility_model))
    def llm() -> StreamedStr: ...

    response = llm()
    output = ""
    for chunk in response:
        output += chunk
    time.sleep(3)
    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()
