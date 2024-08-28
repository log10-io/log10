import os

import openai
import pytest
from openai import NOT_GIVEN, AsyncOpenAI

from log10._httpx_utils import finalize
from log10.load import log10
from tests.utils import _LogAssertion


log10(openai)


# Define a fixture that provides parameterized api_key and base_url
@pytest.fixture(
    params=[
        {
            "model_name": "llama-3.1-sonar-small-128k-chat",
            "api_key": "PERPLEXITYAI_API_KEY",
            "base_url": "https://api.perplexity.ai",
        },
        {"model_name": "open-mistral-nemo", "api_key": "MISTRAL_API_KEY", "base_url": "https://api.mistral.ai/v1"},
        {"model_name": "llama3.1-8b", "api_key": "CEREBRAS_API_KEY", "base_url": "https://api.cerebras.ai/v1"},
    ]
)
def config(request):
    api_environment_variable = request.param["api_key"]
    if api_environment_variable not in os.environ:
        raise ValueError(f"Please set the {api_environment_variable} environment variable.")

    return {
        "base_url": request.param["base_url"],
        "api_key": request.param["api_key"],
        "model_name": request.param["model_name"],
    }


@pytest.mark.chat
def test_chat(session, config):
    compatibility_config = {
        "base_url": config["base_url"],
        "api_key": os.environ.get(config["api_key"]),
    }
    model_name = config["model_name"]

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
def test_chat_not_given(session, config):
    compatibility_config = {
        "base_url": config["base_url"],
        "api_key": os.environ.get(config["api_key"]),
    }
    model_name = config["model_name"]

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
async def test_chat_async(session, config):
    compatibility_config = {
        "base_url": config["base_url"],
        "api_key": os.environ.get(config["api_key"]),
    }
    model_name = config["model_name"]

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
def test_chat_stream(session, config):
    compatibility_config = {
        "base_url": config["base_url"],
        "api_key": os.environ.get(config["api_key"]),
    }
    model_name = config["model_name"]

    client = openai.OpenAI(**compatibility_config)
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": "Count to 5"}],
        temperature=0,
        stream=True,
    )

    output = ""
    for chunk in response:
        output += chunk.choices[0].delta.content or ""

    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.async_client
@pytest.mark.stream
@pytest.mark.asyncio(scope="module")
async def test_chat_async_stream(session, config):
    compatibility_config = {
        "base_url": config["base_url"],
        "api_key": os.environ.get(config["api_key"]),
    }
    model_name = config["model_name"]

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
