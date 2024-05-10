import asyncio
import base64
import json
import httpx
import pytest


from log10.load import log10
import openai
from openai import NOT_GIVEN
from openai import AsyncOpenAI


log10(openai)
client = openai.OpenAI()

@pytest.mark.chat
def test_chat():
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
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

    assert isinstance(completion.choices[0].message.content, str)

@pytest.mark.chat
def test_chat_not_given():
    completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {
            "role": "user",
            "content": "tell a short joke.",
        },
    ],
    tools=NOT_GIVEN,
    tool_choice=NOT_GIVEN,
    )

    assert isinstance(completion.choices[0].message.content, str)

@pytest.mark.chat
def test_chat_async():
    client = AsyncOpenAI()

    async def main():
        completion = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Say this is a test"}],
        )
        assert isinstance(completion.choices[0].message.content, str)

    asyncio.run(main())

@pytest.mark.chat_stream
def test_chat_stream(capfd):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Count to 10"}],
        temperature=0,
        stream=True,
    )

    for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
    print("")

    out, err = capfd.readouterr()
    assert err == ''
    assert out == '1, 2, 3, 4, 5, 6, 7, 8, 9, 10\n'

@pytest.mark.chat_stream
def test_chat_async_stream(capfd):
    client = AsyncOpenAI()

    async def main():
        stream = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Count to 10"}],
            stream=True,
        )
        async for chunk in stream:
            print(chunk.choices[0].delta.content or "", end="", flush=True)

    asyncio.run(main())

    out, err = capfd.readouterr()
    assert err == ''
    out_array = out.split(',')
    assert len(out_array) == 10

@pytest.mark.chat_image
def test_chat_image():
    image1_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
    image1_media_type = "image/jpeg"
    image1_data = base64.b64encode(httpx.get(image1_url).content).decode("utf-8")


    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
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
    assert isinstance(response.choices[0].message.content, str)

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
def test_tools():
    # Step 1: send the conversation and available functions to the model
    result = setup_tools_messages()
    messages = result["messages"]
    tools = result["tools"]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=messages,
        tools=tools,
        tool_choice="auto",  # auto is default, but we'll be explicit
    )
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls
    # Step 2: check if the model wanted to call a function
    if tool_calls:
        # Step 3: call the function
        # Note: the JSON response may not always be valid; be sure to handle errors
        available_functions = {
            "get_current_weather": get_current_weather,
        }  # only one function in this example, but you can have multiple
        messages.append(response_message)  # extend conversation with assistant's reply
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
            model="gpt-3.5-turbo-0125",
            messages=messages,
        )  # get a new response from the model where it can see the function response
        assert isinstance(second_response.choices[0].message.content, str)

@pytest.mark.tools_stream
def test_tools_stream():
    # Step 1: send the conversation and available functions to the model
    result = setup_tools_messages()
    messages = result["messages"]
    tools = result["tools"]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
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
    function_args = [{"function": t.function.name, "arguments": t.function.arguments} for t in tool_calls]
    assert len(function_args) == 3

@pytest.mark.tools_stream
def test_tools_stream_async():
    client = AsyncOpenAI()

    # Step 1: send the conversation and available functions to the model
    result = setup_tools_messages()
    messages = result["messages"]
    tools = result["tools"]

    async def main():
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
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
        
        function_args = [{"function": t.function.name, "arguments": t.function.arguments} for t in tool_calls]
        assert len(function_args) == 3

    asyncio.run(main())
