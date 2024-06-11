import base64

import anthropic
import httpx
import pytest
from anthropic import NOT_GIVEN

from log10._httpx_utils import finalize
from log10.load import log10
from tests.utils import _LogAssertion


log10(anthropic)


@pytest.mark.completion
def test_completions_create(session, anthropic_legacy_model):
    client = anthropic.Anthropic()

    completion = client.completions.create(
        model=anthropic_legacy_model,
        prompt=f"\n\nHuman:Help me create some similes to describe a person's laughter that is joyful and contagious?{anthropic.AI_PROMPT}",
        temperature=0,
        max_tokens_to_sample=1024,
        top_p=1,
        top_k=0,
    )

    text = completion.completion
    assert isinstance(text, str)
    _LogAssertion(completion_id=session.last_completion_id(), text=text).assert_text_response()


@pytest.mark.chat
def test_messages_create(session, anthropic_model):
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
    _LogAssertion(completion_id=session.last_completion_id(), message_content=text).assert_chat_response()


@pytest.mark.chat
@pytest.mark.async_client
@pytest.mark.asyncio(scope="module")
async def test_messages_create_async(session, anthropic_model):
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

    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), message_content=text).assert_chat_response()


@pytest.mark.chat
@pytest.mark.stream
def test_messages_create_stream(session, anthropic_model):
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

    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.vision
def test_messages_image(session, anthropic_model):
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
    _LogAssertion(completion_id=session.last_completion_id(), message_content=text).assert_chat_response()


@pytest.mark.chat
def test_chat_not_given(session, anthropic_model):
    client = anthropic.Anthropic()

    message = client.messages.create(
        model=anthropic_model,
        messages=[
            {
                "role": "user",
                "content": "tell a short joke.",
            },
        ],
        max_tokens=1000,
        tools=NOT_GIVEN,
        tool_choice=NOT_GIVEN,
    )

    content = message.content[0].text
    assert isinstance(content, str)
    assert content, "No output from the model."
    _LogAssertion(completion_id=session.last_completion_id(), message_content=content).assert_chat_response()


@pytest.mark.chat
@pytest.mark.stream
@pytest.mark.context_manager
def test_messages_stream_context_manager(session, anthropic_model):
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
        for message in stream:
            if message.type == "content_block_delta":
                if message.delta:
                    if hasattr(message.delta, "text"):
                        output += message.delta.text

    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.chat
@pytest.mark.stream
@pytest.mark.context_manager
@pytest.mark.async_client
@pytest.mark.asyncio(scope="module")
async def test_messages_stream_context_manager_async(session, anthropic_model):
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

    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.tools
@pytest.mark.stream
@pytest.mark.context_manager
def test_tools_messages_stream_context_manager(session, anthropic_model):
    client = anthropic.Anthropic()
    full_content = ""
    with client.messages.stream(
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
            if message.type == "message_stop":
                message = message.message
                contents = message.content
                for content in contents:
                    if isinstance(content, anthropic.types.TextBlock):
                        full_content = content.text
                    if isinstance(content, anthropic.types.ToolUseBlock):
                        arguments = str(content.input)
                        function_name = content.name

    function_args = [{"name": function_name, "arguments": arguments}]
    _LogAssertion(
        completion_id=session.last_completion_id(), function_args=function_args
    ).assert_anthropic_tool_calls_response(full_content)


@pytest.mark.tools
def test_tools_create(session, anthropic_model):
    from anthropic.types import MessageParam, ToolParam

    client = anthropic.Anthropic()

    user_message: MessageParam = {
        "role": "user",
        "content": "What is the weather in SF?",
    }
    tools: list[ToolParam] = [
        {
            "name": "get_weather",
            "description": "Get the weather for a specific location",
            "input_schema": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
            },
        }
    ]

    message = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1024,
        messages=[user_message],
        tools=tools,
    )

    full_content = ""
    function_name = ""
    arguments = ""
    for c in message.content:
        if isinstance(c, anthropic.types.TextBlock):
            full_content = c.text
        if isinstance(c, anthropic.types.ToolUseBlock):
            arguments = str(c.input)
            function_name = c.name

    function_args = [{"name": function_name, "arguments": arguments}]

    _LogAssertion(
        completion_id=session.last_completion_id(), function_args=function_args
    ).assert_anthropic_tool_calls_response(full_content)

    tool = next(c for c in message.content if c.type == "tool_use")
    response = client.messages.create(
        model=anthropic_model,
        max_tokens=1024,
        messages=[
            user_message,
            {"role": message.role, "content": message.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool.id,
                        "content": [{"type": "text", "text": "The weather is 73f"}],
                    }
                ],
            },
        ],
        tools=tools,
    )

    for c in response.content:
        if isinstance(c, anthropic.types.TextBlock):
            full_content = c.text

    _LogAssertion(completion_id=session.last_completion_id(), message_content=full_content).assert_chat_response()


@pytest.mark.tools
@pytest.mark.stream
@pytest.mark.context_manager
@pytest.mark.async_client
@pytest.mark.asyncio(scope="module")
async def test_tools_messages_stream_context_manager_async(session, anthropic_model):
    client = anthropic.AsyncAnthropic()
    full_content = ""
    arguments = ""
    function_name = ""
    async with client.messages.stream(
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
        async for message in stream:
            if message.type == "message_stop":
                message = message.message
                contents = message.content
                for content in contents:
                    if isinstance(content, anthropic.types.TextBlock):
                        full_content = content.text
                    if isinstance(content, anthropic.types.ToolUseBlock):
                        arguments = str(content.input)
                        function_name = content.name

    await finalize()

    function_args = [{"name": function_name, "arguments": arguments}]
    _LogAssertion(
        completion_id=session.last_completion_id(), function_args=function_args
    ).assert_anthropic_tool_calls_response(full_content)
