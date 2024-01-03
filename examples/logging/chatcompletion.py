from log10.load import OpenAI


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
