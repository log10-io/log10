from log10.load import OpenAI


client = OpenAI()

text_to_repeat = "What is the meaning of life?" * 1000

response = client.completions.create(
    model="gpt-3.5-turbo-instruct",
    prompt=text_to_repeat,
    temperature=0,
    max_tokens=1024,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0,
)

print(response)
