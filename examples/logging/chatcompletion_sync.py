from log10.load import OpenAI, log10_session


client = OpenAI()

with log10_session(tags=["log10-io/examples"]):
    client = OpenAI()
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": "Hello?",
            },
        ],
    )
    print(completion.choices[0].message)

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": "Hello again, are you there?",
            },
        ],
    )
    print(completion.choices[0].message)
