import asyncio
import os

import openai
from openai import AsyncOpenAI

from log10._httpx_utils import finalize
from log10.load import log10


log10(openai)

client = AsyncOpenAI(base_url="https://api.perplexity.ai",  api_key=os.environ.get("PERPLEXITYAI_API_KEY"))


async def main():
    completion = await client.chat.completions.create(
        model="llama-3.1-sonar-small-128k-chat",
        messages=[{"role": "user", "content": "Say this is a test"}],
    )
    print(completion.choices[0].message.content)
    await finalize()


asyncio.run(main())
