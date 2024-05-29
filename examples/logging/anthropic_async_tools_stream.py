import asyncio

import anthropic
from anthropic import AsyncAnthropic

from log10.load import log10


log10(anthropic)

client = AsyncAnthropic()


async def run_conversation():
    tools = [
        {
            "name": "get_weather",
            "description": "Get the weather in a given location",
            "input_schema": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "The city and state, e.g. San Francisco, CA"},
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": 'The unit of temperature, either "celsius" or "fahrenheit"',
                    },
                },
                "required": ["location"],
            },
        }
    ]
    async with client.beta.tools.messages.stream(
        model="claude-3-haiku-20240307",
        tools=tools,
        messages=[
            {
                "role": "user",
                "content": "What's the weather like in San Francisco?",
            }
        ],
        max_tokens=1024,
    ) as stream:
        await stream.until_done()


asyncio.run(run_conversation())
