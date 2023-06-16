import os
from log10.load import log10
import openai

log10(openai, DEBUG_=True, USE_ASYNC_=False)

openai.api_key = os.getenv("OPENAI_API_KEY")

response = openai.Completion.create(
    model="text-ada-001",
    prompt="What is 2+2?",
    temperature=0,
    max_tokens=1024,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
)

print(response)
