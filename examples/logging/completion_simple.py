from log10.load import OpenAI


client = OpenAI()

response = client.completions.create(
    model="gpt-3.5-turbo-instruct",
    prompt="What is 2+2?",
    temperature=0,
    max_tokens=1024,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
)

print(response)
