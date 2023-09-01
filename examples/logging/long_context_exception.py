import os
from log10.load import log10
import openai

log10(openai)

openai.api_key = os.getenv("OPENAI_API_KEY")

text_to_repeat = "What is the meaning of life?" * 1000

response = openai.Completion.create(
    model="text-davinci-003",
    prompt=text_to_repeat,
    temperature=0,
    max_tokens=1024,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
)

print(response)
