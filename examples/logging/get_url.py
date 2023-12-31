import os

import openai
from langchain.llms import OpenAI

from log10.load import log10, log10_session


log10(openai)

openai.api_key = os.getenv("OPENAI_API_KEY")

llm = OpenAI(temperature=0.9, model_name="gpt-3.5-turbo-instruct")

with log10_session() as session:
    print(session.last_completion_url())

    response = openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Why did the chicken cross the road?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    print(session.last_completion_url())

    response = openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
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
        model="gpt-3.5-turbo-instruct",
        prompt="Why did the frog cross the road?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    print(session.last_completion_url())

    response = openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Why did the scorpion cross the road?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    print(session.last_completion_url())
