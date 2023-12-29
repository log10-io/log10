import openai

from log10.load import log10


log10(openai)

client = openai.OpenAI()
response = client.completions.create(
    model="text-davinci-003",
    prompt="Write the names of all Star Wars movies and spinoffs along with the time periods in which they were set?",
    temperature=0,
    max_tokens=1024,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
)

print(response)
