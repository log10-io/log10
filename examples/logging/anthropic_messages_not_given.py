from log10.load import Anthropic


client = Anthropic()

completion = client.messages.create(
    model="claude-instant-1.2",
    messages=[
        {
            "role": "user",
            "content": "tell a short joke.",
        },
    ],
    max_tokens=1000,
)

print(completion.content[0].text)
