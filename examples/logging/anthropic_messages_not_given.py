from anthropic import NOT_GIVEN

from log10.load import Anthropic


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
