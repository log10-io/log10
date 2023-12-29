import openai

from log10.load import log10, log10_session


log10(openai)

client = openai.OpenAI()
response = client.completions.create(
    model="text-ada-001",
    prompt="Where are the pyramids?",
    temperature=0,
    max_tokens=1024,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
)
print(response)

with log10_session(tags=["foo", "bar"]):
    response = client.completions.create(
        model="text-ada-001",
        prompt="Where is the Eiffel Tower?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    print(response)

with log10_session(tags=["bar", "baz"]):
    response = client.completions.create(
        model="text-ada-001",
        prompt="Where is the statue of liberty?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    print(response)

response = client.completions.create(
    model="text-ada-001",
    prompt="Where is machu picchu?",
    temperature=0,
    max_tokens=1024,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
)
print(response)
