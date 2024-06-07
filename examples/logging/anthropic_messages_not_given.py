import anthropic
from anthropic import NOT_GIVEN, Anthropic

from log10.load import log10


log10(anthropic)

client = Anthropic()

completion = client.messages.create(
    model="claude-3-haiku-20240307",
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

print(completion.content[0].text)
