from log10.load import OpenAI, log10_session


client = OpenAI()
response = client.completions.create(
    model="gpt-3.5-turbo-instruct",
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
        model="gpt-3.5-turbo-instruct",
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
        model="gpt-3.5-turbo-instruct",
        prompt="Where is the statue of liberty?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    print(response)

response = client.completions.create(
    model="gpt-3.5-turbo-instruct",
    prompt="Where is machu picchu?",
    temperature=0,
    max_tokens=1024,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
)
print(response)
