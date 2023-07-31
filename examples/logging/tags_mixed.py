import os
from log10.load import log10, log10_session
import openai
from langchain import OpenAI

log10(openai)

with log10_session(tags=["foo", "bar"]):
    response = openai.Completion.create(
        model="text-ada-001",
        prompt="Where is the Eiffel Tower?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    print(response)

    llm = OpenAI(model_name="text-ada-001", temperature=0.5)
    response = llm.predict("You are a ping pong machine.\nPing?\n")
    print(response)
