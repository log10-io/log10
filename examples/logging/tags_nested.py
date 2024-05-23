from log10.load import OpenAI, log10_session


client = OpenAI()
response = client.completions.create(
    model="gpt-3.5-turbo-instruct",
    prompt="I am demonstrating nested tags. Write a test case for this. This is the outer most call without any tags.",
    temperature=0,
    max_tokens=1024,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
)
print(response)

with log10_session(tags=["outer_tag"]):
    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt="I am demonstrating nested tags. Write a test case for this. This is a inner call with tags.",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    print(response)

    with log10_session(tags=["inner_tag"]):
        response = client.completions.create(
            model="gpt-3.5-turbo-instruct",
            prompt="I am demonstrating nested tags. Write a test case for this. This is the inner most call with tags.",
            temperature=0,
            max_tokens=1024,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )
        print(response)

    response = client.completions.create(
        model="gpt-3.5-turbo-instruct",
        prompt="I am demonstrating nested tags. Write a test case for this. This is a inner call which should have outer tag.",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    print(response)

response = client.completions.create(
    model="gpt-3.5-turbo-instruct",
    prompt="I am demonstrating nested tags. Write a test case for this. This is the outer most call without any tags (final call)",
    temperature=0,
    max_tokens=1024,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
)
print(response)
