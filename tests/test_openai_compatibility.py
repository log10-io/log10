import os

import openai
import pytest
from openai import NOT_GIVEN, AsyncOpenAI

from log10._httpx_utils import finalize
from log10.load import log10
from tests.utils import _LogAssertion


log10(openai)

model_name = "llama-3.1-sonar-small-128k-chat"

if "PERPLEXITYAI_API_KEY" not in os.environ:
    raise ValueError("Please set the PERPLEXITYAI_API_KEY environment variable.")

compatibility_config = {
    "base_url": "https://api.perplexity.ai",
    "api_key": os.environ.get("PERPLEXITYAI_API_KEY"),
}


@pytest.mark.chat
def test_chat(session):
    client = openai.OpenAI(**compatibility_config)
    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "You will be provided with statements, and your task is to convert them to standard English.",
            },
            {
                "role": "user",
                "content": "He no went to the market.",
            },
        ],
    )

    content = completion.choices[0].message.content
    assert isinstance(content, str)
    assert session.last_completion_url() is not None, "No completion URL found."
    _LogAssertion(completion_id=session.last_completion_id(), message_content=content).assert_chat_response()


@pytest.mark.chat
def test_chat_not_given(session):
    client = openai.OpenAI(**compatibility_config)
    completion = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": "tell a short joke.",
            },
        ],
        tools=NOT_GIVEN,
        tool_choice=NOT_GIVEN,
    )

    content = completion.choices[0].message.content
    assert isinstance(content, str)
    assert session.last_completion_url() is not None, "No completion URL found."
    _LogAssertion(completion_id=session.last_completion_id(), message_content=content).assert_chat_response()


@pytest.mark.chat
@pytest.mark.async_client
@pytest.mark.asyncio(scope="module")
async def test_chat_async(session):
    client = AsyncOpenAI(**compatibility_config)
    completion = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": "Say this is a test"}],
    )

    content = completion.choices[0].message.content
    assert isinstance(content, str)
    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), message_content=content).assert_chat_response()


@pytest.mark.chat
@pytest.mark.async_client
@pytest.mark.asyncio(scope="module")
async def test_perplexity_chat_async(session):
    client = AsyncOpenAI(**compatibility_config)
    completion = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": "Say this is a test"}],
    )

    content = completion.choices[0].message.content
    assert isinstance(content, str)
    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), message_content=content).assert_chat_response()


@pytest.mark.chat
@pytest.mark.stream
def test_chat_stream(session):
    client = openai.OpenAI(**compatibility_config)
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": "Count to 5"}],
        temperature=0,
        stream=True,
    )

    output = ""
    for chunk in response:
        output += chunk.choices[0].delta.content

    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.async_client
@pytest.mark.stream
@pytest.mark.asyncio(scope="module")
async def test_chat_async_stream(session):
    client = AsyncOpenAI(**compatibility_config)

    output = ""
    stream = await client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": "Count to 8"}],
        stream=True,
    )
    async for chunk in stream:
        output += chunk.choices[0].delta.content or ""

    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()
