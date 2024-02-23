import asyncio

import openai
from openai import AsyncOpenAI

from log10.load import log10


log10(openai)

client = AsyncOpenAI()


async def main():
    completion = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Say this is a test"}],
    )
    print(completion.choices[0].message.content)


asyncio.run(main())
