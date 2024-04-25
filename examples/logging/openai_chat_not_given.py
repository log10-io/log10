from openai import NOT_GIVEN

from log10.load import OpenAI


client = OpenAI()

completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {
            "role": "user",
            "content": "tell a joke.",
        },
    ],
    tools=NOT_GIVEN,
    tool_choice=NOT_GIVEN,
)

print(completion.choices[0].message.content)
