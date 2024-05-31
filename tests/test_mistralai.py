import mistralai
import pytest
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from log10.load import log10
from tests.utils import _LogAssertion


log10(mistralai)
client = MistralClient()


@pytest.mark.chat
def test_chat(session, mistralai_model):
    chat_response = client.chat(
        model=mistralai_model,
        messages=[ChatMessage(role="user", content="10 + 2 * 3=?")],
    )

    content = chat_response.choices[0].message.content
    _LogAssertion(completion_id=session.last_completion_id(), message_content=content).assert_chat_response()


@pytest.mark.chat
@pytest.mark.stream
def test_chat_stream(session, mistralai_model):
    response = client.chat_stream(
        model=mistralai_model,
        messages=[ChatMessage(role="user", content="Count the odd numbers from 1 to 20.")],
    )

    output = ""
    for chunk in response:
        content = chunk.choices[0].delta.content
        if chunk.choices[0].delta.content is not None:
            output += content

    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()
