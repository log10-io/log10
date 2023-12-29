import openai

from log10.load import log10, log10_session


log10(openai)

client = openai.OpenAI()

with log10_session() as session:
    print(session.last_completion_url())

    response = client.completions.create(
        model="text-ada-001",
        prompt="Why did the chicken cross the road?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    print(session.last_completion_url())

    response = client.completions.create(
        model="text-ada-001",
        prompt="Why did the cow cross the road?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    print(session.last_completion_url())

with log10_session() as session:
    print(session.last_completion_url())

    response = openai.Completion.create(
        model="text-ada-001",
        prompt="Why did the frog cross the road?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    print(session.last_completion_url())

    response = openai.Completion.create(
        model="text-ada-001",
        prompt="Why did the scorpion cross the road?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    print(session.last_completion_url())
