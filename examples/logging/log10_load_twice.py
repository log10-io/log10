import openai
from openai import OpenAI

from log10.load import log10


# log10 load twice should not expect to log the completion twice
log10(openai)
log10(openai)


client = OpenAI()

completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {
            "role": "system",
            "content": "You are the most knowledgable Star Wars guru on the planet",
        },
        {
            "role": "user",
            "content": "Write the time period of all the Star Wars movies and spinoffs?",
        },
    ],
)

print(completion.choices[0].message)
