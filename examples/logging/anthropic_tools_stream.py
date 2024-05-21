import anthropic

from log10.load import log10


log10(anthropic)


client = anthropic.Anthropic()

with client.beta.tools.messages.stream(
    model="claude-instant-1.2",
    messages=[
        {
            "role": "user",
            "content": "Howdy",
        }
    ],
    max_tokens=1024,
) as stream:
    for message in stream:
        print(message)
