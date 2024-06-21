import anthropic
from anthropic import Anthropic

from log10.load import log10


log10(anthropic)


client = Anthropic()

stream = client.messages.create(
    model="claude-3-5-sonnet-20240620",
    messages=[
        {
            "role": "user",
            "content": "Tell a 50 words joke.",
        }
    ],
    max_tokens=128,
    temperature=0.9,
    stream=True,
)
for event in stream:
    if event.type == "content_block_delta":
        print(event.delta.text, end="", flush=True)
