import anthropic

from log10.load import log10


log10(anthropic)


client = anthropic.Anthropic()

with client.beta.tools.messages.stream(
    model="claude-3-haiku-20240307",
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
        print(message)
