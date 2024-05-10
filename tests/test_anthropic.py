import base64
import httpx
import pytest
from log10.load import log10

import anthropic

log10(anthropic)
client = anthropic.Anthropic()

@pytest.mark.chat
def test_messages():

    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        temperature=0.0,
        system="Respond only in Yoda-speak.",
        messages=[{"role": "user", "content": "How are you today?"}],
    )

    assert isinstance(message.content[0].text, str)

@pytest.mark.chat_stream
def test_messages_stream(capfd):
    stream = client.messages.create(
        model="claude-3-opus-20240229",
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
            print(event.delta.text, end="", flush=True)
    

    out, err = capfd.readouterr()
    assert err == ''
    out_array = out.split('\n')
    assert len(out_array) == 10

@pytest.mark.chat_image
def test_messages_image():
    client = anthropic.Anthropic()

    image1_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
    image1_media_type = "image/jpeg"
    image1_data = base64.b64encode(httpx.get(image1_url).content).decode("utf-8")

    message = client.messages.create(
        model="claude-3-haiku-20240307",
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
    assert isinstance(message.content[0].text, str)
