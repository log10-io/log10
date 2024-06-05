from __future__ import annotations

import anthropic
from anthropic import Anthropic
from anthropic.types import MessageParam, ToolParam

from log10.load import log10


log10(anthropic)
client = Anthropic()

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
print(f"Initial response: {message.model_dump_json(indent=2)}")

assert message.stop_reason == "tool_use"

tool = next(c for c in message.content if c.type == "tool_use")
response = client.messages.create(
    model="claude-3-haiku-20240307",
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
print(f"\nFinal response: {response.model_dump_json(indent=2)}")
