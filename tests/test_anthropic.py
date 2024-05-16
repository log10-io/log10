import base64

import anthropic
import httpx
import pytest

from log10.load import log10


log10(anthropic)
client = anthropic.Anthropic()


@pytest.mark.chat
def test_messages(anthropic_model):
    model_name = anthropic_model or "claude-3-opus-20240229"
    message = client.messages.create(
        model=model_name,
        max_tokens=1000,
        temperature=0.0,
        system="Respond only in Yoda-speak.",
        messages=[{"role": "user", "content": "How are you today?"}],
    )

    text = message.content[0].text
    assert isinstance(text, str)
    assert text, "No output from the model."


@pytest.mark.chat
@pytest.mark.stream
def test_messages_stream(anthropic_model):
    model_name = anthropic_model or "claude-3-haiku-20240307"
    stream = client.messages.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": "Count to 10",
            }
        ],
        max_tokens=128,
        temperature=0.9,
        stream=True,
    )

    for event in stream:
        if event.type == "content_block_delta":
            text = event.delta.text
            if text.isdigit():
                assert int(text) <= 10


@pytest.mark.vision
def test_messages_image(anthropic_model):
    client = anthropic.Anthropic()

    image1_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
    image1_media_type = "image/jpeg"
    image1_data = base64.b64encode(httpx.get(image1_url).content).decode("utf-8")

    model_name = anthropic_model or "claude-3-haiku-20240307"
    message = client.messages.create(
        model=model_name,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": image1_media_type,
                            "data": image1_data,
                        },
                    },
                    {"type": "text", "text": "Describe this image."},
                ],
            }
        ],
    )

    text = message.content[0].text
    assert text, "No output from the model."
    assert "ant" in text
