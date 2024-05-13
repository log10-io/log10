import mistralai
import pytest
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from log10.load import log10


log10(mistralai)
model = "mistral-tiny"
client = MistralClient()


@pytest.mark.chat
def test_chat():
    chat_response = client.chat(
        model=model,
        messages=[ChatMessage(role="user", content="10 + 2 * 3=?")],
    )

    content = chat_response.choices[0].message.content
    assert content, "No output from the model."
    assert "16" in content

@pytest.mark.chat
@pytest.mark.stream
def test_chat_stream():
    response = client.chat_stream(
        model=model,
        messages=[ChatMessage(role="user", content="Count the odd numbers from 1 to 20.")],
    )

    output = ""
    for chunk in response:
        content = chunk.choices[0].delta.content
        if chunk.choices[0].delta.content is not None:
            output += content

    assert output, "No output from the model."
    assert "10 odd numbers" in output
