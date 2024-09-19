from log10.load import OpenAI, log10_session, log10_tags, with_tags


client = OpenAI()


@with_tags(["decorator-tags", "decorator-tags-2"])
def completion_with_tags():
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": "Hello?",
            },
        ],
    )
    print(completion.choices[0].message)


with log10_session(tags=["log10-io/examples"]):
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

    with log10_tags(["extra_tag_1", "extra_tag_2"]):
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

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": "Hello again and again?",
            },
        ],
    )
    print(completion.choices[0].message)

    completion_with_tags()

# add a test with log10_tags and log10_session, where log10_session is nested inside log10_tags
with log10_tags(["outer-tag-1", "outer-tag-2"]):
    with log10_session(tags=["inner-tag-1", "inner-tag-2"]):
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": "Hello again and again?",
                },
            ],
        )
        print(completion.choices[0].message)
    completion_with_tags()
