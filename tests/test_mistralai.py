import pytest
from log10.load import log10
import mistralai
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

log10(mistralai)
model = "mistral-tiny"
client = MistralClient()


@pytest.mark.chat
def test_chat():
    chat_response = client.chat(
        model=model,
        messages=[ChatMessage(role="user", content="10 + 2 * 3=?")],
    )

    assert isinstance(chat_response.choices[0].message.content, str)


@pytest.mark.chat
@pytest.mark.stream
def test_chat_stream(capfd):
    response = client.chat_stream(
        model=model,
        messages=[ChatMessage(role="user", content="Count the odd numbers from 1 to 20.")],
    )
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end="")

    out, err = capfd.readouterr()
    assert err == ""
    assert isinstance(out, str)
