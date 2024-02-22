import asyncio

import openai
from openai import AsyncOpenAI

from log10.load import log10


log10(openai)

client = AsyncOpenAI()


async def main():
    stream = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": "Count to 50."}],
        stream=True,
    )
    async for chunk in stream:
        print(chunk.choices[0].delta.content or "", end="", flush=True)


asyncio.run(main())
