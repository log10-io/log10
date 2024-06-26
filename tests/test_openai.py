import base64
import json

import httpx
import openai
import pytest
from openai import NOT_GIVEN, AsyncOpenAI

from log10._httpx_utils import finalize
from log10.load import log10
from tests.utils import _LogAssertion, format_function_args


log10(openai)
client = openai.OpenAI()


@pytest.mark.chat
def test_chat(session, openai_model):
    completion = client.chat.completions.create(
        model=openai_model,
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
def test_chat_not_given(session, openai_model):
    completion = client.chat.completions.create(
        model=openai_model,
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
async def test_chat_async(session, openai_model):
    client = AsyncOpenAI()
    completion = await client.chat.completions.create(
        model=openai_model,
        messages=[{"role": "user", "content": "Say this is a test"}],
    )

    content = completion.choices[0].message.content
    assert isinstance(content, str)
    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), message_content=content).assert_chat_response()


@pytest.mark.chat
@pytest.mark.stream
def test_chat_stream(session, openai_model):
    response = client.chat.completions.create(
        model=openai_model,
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
async def test_chat_async_stream(session, openai_model):
    client = AsyncOpenAI()

    output = ""
    stream = await client.chat.completions.create(
        model=openai_model,
        messages=[{"role": "user", "content": "Count to 8"}],
        stream=True,
    )
    async for chunk in stream:
        output += chunk.choices[0].delta.content or ""

    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.vision
def test_chat_image(session, openai_vision_model):
    image1_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
    image1_media_type = "image/jpeg"
    image1_data = base64.b64encode(httpx.get(image1_url).content).decode("utf-8")

    response = client.chat.completions.create(
        model=openai_vision_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What are in these image?",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{image1_media_type};base64,{image1_data}"},
                    },
                ],
            }
        ],
        max_tokens=300,
    )

    content = response.choices[0].message.content
    assert isinstance(content, str)
    _LogAssertion(completion_id=session.last_completion_id(), message_content=content).assert_chat_response()


def get_current_weather(location, unit="fahrenheit"):
    """Get the current weather in a given location"""
    if "tokyo" in location.lower():
        return json.dumps({"location": "Tokyo", "temperature": "10", "unit": unit})
    elif "san francisco" in location.lower():
        return json.dumps({"location": "San Francisco", "temperature": "72", "unit": unit})
    elif "paris" in location.lower():
        return json.dumps({"location": "Paris", "temperature": "22", "unit": unit})
    else:
        return json.dumps({"location": location, "temperature": "unknown"})


def setup_tools_messages() -> dict:
    messages = [
        {
            "role": "user",
            "content": "What's the weather like in San Francisco, Tokyo, and Paris?",
        }
    ]
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_current_weather",
                "description": "Get the current weather in a given location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g. San Francisco, CA",
                        },
                        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                    },
                    "required": ["location"],
                },
            },
        }
    ]

    return {
        "messages": messages,
        "tools": tools,
    }


@pytest.mark.tools
def test_tools(session, openai_model):
    # Step 1: send the conversation and available functions to the model
    result = setup_tools_messages()
    messages = result["messages"]
    tools = result["tools"]

    response = client.chat.completions.create(
        model=openai_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",  # auto is default, but we'll be explicit
    )

    first_completion_id = session.last_completion_id()
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    function_args = format_function_args(tool_calls)
    _LogAssertion(completion_id=first_completion_id, function_args=function_args).assert_tool_calls_response()
    # Step 2: check if the model wanted to call a function
    if tool_calls:
        # Step 3: call the function
        # Note: the JSON response may not always be valid; be sure to handle errors
        available_functions = {
            "get_current_weather": get_current_weather,
        }  # only one function in this example, but you can have multiple
        # extend conversation with assistant's reply
        messages.append(response_message)
        # Step 4: send the info for each function call and function response to the model
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)
            function_response = function_to_call(
                location=function_args.get("location"),
                unit=function_args.get("unit"),
            )
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
            )  # extend conversation with function response
        second_response = client.chat.completions.create(
            model=openai_model,
            messages=messages,
        )  # get a new response from the model where it can see the function response
        content = second_response.choices[0].message.content
        assert isinstance(content, str)

        tool_call_completion_id = session.last_completion_id()
        assert tool_call_completion_id != first_completion_id, "Completion IDs should be different."
        _LogAssertion(completion_id=tool_call_completion_id, message_content=content).assert_chat_response()


@pytest.mark.stream
@pytest.mark.tools
def test_tools_stream(session, openai_model):
    # Step 1: send the conversation and available functions to the model
    result = setup_tools_messages()
    messages = result["messages"]
    tools = result["tools"]
    response = client.chat.completions.create(
        model=openai_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",  # auto is default, but we'll be explicit
        stream=True,
    )
    tool_calls = []
    for chunk in response:
        if chunk.choices[0].delta:
            if tc := chunk.choices[0].delta.tool_calls:
                if tc[0].id:
                    tool_calls.append(tc[0])
                else:
                    tool_calls[-1].function.arguments += tc[0].function.arguments

    function_args = format_function_args(tool_calls)
    assert len(function_args) == 3

    _LogAssertion(completion_id=session.last_completion_id(), function_args=function_args).assert_tool_calls_response()


@pytest.mark.tools
@pytest.mark.stream
@pytest.mark.async_client
@pytest.mark.asyncio(scope="module")
async def test_tools_stream_async(session, openai_model):
    client = AsyncOpenAI()
    # Step 1: send the conversation and available functions to the model
    result = setup_tools_messages()
    messages = result["messages"]
    tools = result["tools"]

    response = await client.chat.completions.create(
        model=openai_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",  # auto is default, but we'll be explicit
        stream=True,
    )

    tool_calls = []
    async for chunk in response:
        if chunk.choices[0].delta:
            if tc := chunk.choices[0].delta.tool_calls:
                if tc[0].id:
                    tool_calls.append(tc[0])
                else:
                    tool_calls[-1].function.arguments += tc[0].function.arguments

    function_args = format_function_args(tool_calls)
    assert len(function_args) == 3

    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), function_args=function_args).assert_tool_calls_response()
