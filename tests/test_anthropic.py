import base64

import anthropic
import httpx
import pytest
from anthropic import NOT_GIVEN
from anthropic.lib.streaming.beta import AsyncToolsBetaMessageStream
from typing_extensions import override

from log10.load import log10


log10(anthropic)


@pytest.mark.chat
def test_messages_create(anthropic_model):
    client = anthropic.Anthropic()

    message = client.messages.create(
        model=anthropic_model,
        max_tokens=1000,
        temperature=0.0,
        system="Respond only in Yoda-speak.",
        messages=[{"role": "user", "content": "How are you today?"}],
    )

    text = message.content[0].text
    assert isinstance(text, str)
    assert text, "No output from the model."


@pytest.mark.chat
@pytest.mark.async_client
@pytest.mark.asyncio
async def test_messages_create_async(anthropic_model):
    client = anthropic.AsyncAnthropic()

    message = await client.messages.create(
        model=anthropic_model,
        max_tokens=1000,
        temperature=0.0,
        system="Respond only in Yoda-speak.",
        messages=[{"role": "user", "content": "Say hello!"}],
    )

    text = message.content[0].text
    assert isinstance(text, str)
    assert text, "No output from the model."


@pytest.mark.chat
@pytest.mark.stream
def test_messages_create_stream(anthropic_model):
    client = anthropic.Anthropic()

    stream = client.messages.create(
        model=anthropic_model,
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

    output = ""
    for event in stream:
        if event.type == "content_block_delta":
            text = event.delta.text
            output += text
            if text.isdigit():
                assert int(text) <= 10

    assert output, "No output from the model."


@pytest.mark.chat
@pytest.mark.stream
@pytest.mark.async_client
@pytest.mark.asyncio
async def test_messages_create_stream_async(anthropic_model):
    client = anthropic.AsyncAnthropic()

    stream = await client.messages.create(
        model=anthropic_model,
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

    output = ""
    for event in stream:
        if event.type == "content_block_delta":
            text = event.delta.text
            output += text
            if text.isdigit():
                assert int(text) <= 10

    assert output, "No output from the model."


@pytest.mark.vision
def test_messages_image(anthropic_model):
    client = anthropic.Anthropic()

    image1_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
    image1_media_type = "image/jpeg"
    image1_data = base64.b64encode(httpx.get(image1_url).content).decode("utf-8")

    message = client.messages.create(
        model=anthropic_model,
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


@pytest.mark.chat
def test_chat_not_given(anthropic_model):
    client = anthropic.Anthropic()

    message = client.beta.tools.messages.stream(
        model=anthropic_model,
        messages=[
            {
                "role": "user",
                "content": "tell a short joke.",
            },
        ],
        tools=NOT_GIVEN,
        tool_choice=NOT_GIVEN,
    )

    content = message.content[0].text
    assert isinstance(content, str)
    assert content, "No output from the model."


@pytest.mark.chat
def test_beta_tools_messages_create(anthropic_model):
    client = anthropic.Anthropic()

    message = client.beta.tools.messages.create(
        model=anthropic_model,
        max_tokens=1000,
        messages=[{"role": "user", "content": "Say hello!"}],
    )

    text = message.content[0].text
    assert text, "No output from the model."


@pytest.mark.chat
@pytest.mark.async_client
@pytest.mark.asyncio
async def test_beta_tools_messages_create_async(anthropic_model):
    client = anthropic.AsyncAnthropic()

    message = await client.beta.tools.messages.create(
        model=anthropic_model,
        max_tokens=1000,
        messages=[{"role": "user", "content": "Say hello!"}],
    )

    text = message.content[0].text
    assert text, "No output from the model."


@pytest.mark.chat
@pytest.mark.async_client
@pytest.mark.asyncio
async def test_beta_tools_messages_stream_async(anthropic_model):
    client = anthropic.AsyncAnthropic()

    message = await client.beta.tools.messages.stream(
        model=anthropic_model,
        max_tokens=1000,
        messages=[{"role": "user", "content": "Say hello!"}],
    )

    text = message.content[0].text
    assert text, "No output from the model."


@pytest.mark.chat
@pytest.mark.stream
@pytest.mark.context_manager
def test_messages_stream_context_manager(anthropic_model):
    client = anthropic.Anthropic()

    output = ""
    with client.messages.stream(
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": "Say hello there!",
            }
        ],
        model=anthropic_model,
    ) as stream:
        for text in stream.text_stream:
            output += text

    assert output, "No output from the model."


@pytest.mark.chat
@pytest.mark.stream
@pytest.mark.context_manager
@pytest.mark.async_client
@pytest.mark.asyncio
async def test_messages_stream_context_manager_async(anthropic_model):
    client = anthropic.AsyncAnthropic()

    output = ""
    async with client.messages.stream(
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": "Say hello there!",
            }
        ],
        model=anthropic_model,
    ) as stream:
        async for text in stream.text_stream:
            output += text

    assert output, "No output from the model."


@pytest.mark.tools
@pytest.mark.stream
@pytest.mark.context_manager
def test_tools_messages_stream_context_manager(anthropic_model):
    client = anthropic.Anthropic()
    output = ""
    with client.beta.tools.messages.stream(
        model=anthropic_model,
        tools=[
            {
                "name": "get_weather",
                "description": "Get the weather at a specific location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "The city and state, e.g. San Francisco, CA"},
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Unit for the output",
                        },
                    },
                    "required": ["location"],
                },
            }
        ],
        messages=[{"role": "user", "content": "What is the weather in SF?"}],
        max_tokens=1024,
    ) as stream:
        for message in stream:
            if message.type == "content_block_delta":
                if message.delta:
                    if hasattr(message.delta, "text"):
                        output += message.delta.text
                    if hasattr(message.delta, "partial_json"):
                        output += message.delta.partial_json

    assert output, "No output from the model."


@pytest.mark.tools
@pytest.mark.stream
@pytest.mark.context_manager
@pytest.mark.async_client
@pytest.mark.asyncio
async def test_tools_messages_stream_context_manager_async(anthropic_model):
    client = anthropic.AsyncAnthropic()
    output = None

    class MyHandler(AsyncToolsBetaMessageStream):
        @override
        async def on_input_json(self, snapshot: object) -> None:
            nonlocal output
            output = snapshot

    async with client.beta.tools.messages.stream(
        model=anthropic_model,
        tools=[
            {
                "name": "get_weather",
                "description": "Get the weather at a specific location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "The city and state, e.g. San Francisco, CA"},
                        "unit": {
                            "type": "string",
                            "enum": ["celsius", "fahrenheit"],
                            "description": "Unit for the output",
                        },
                    },
                    "required": ["location"],
                },
            }
        ],
        messages=[{"role": "user", "content": "What is the weather in SF?"}],
        max_tokens=1024,
        event_handler=MyHandler,
    ) as stream:
        await stream.until_done()

    assert output, "No output from the model."
