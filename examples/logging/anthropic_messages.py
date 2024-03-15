import anthropic

from log10.load import log10


log10(anthropic)

client = anthropic.Anthropic()

message = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1000,
    temperature=0.0,
    system="Respond only in Yoda-speak.",
    messages=[{"role": "user", "content": "How are you today?"}],
)

print(message.content[0].text)
