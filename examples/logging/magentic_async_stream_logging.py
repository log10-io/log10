import asyncio

import openai
from magentic import AsyncStreamedStr, prompt

from log10.load import log10, log10_session


log10(openai)


@prompt("Tell me a 200-word story about {topic}")
async def tell_story(topic: str) -> AsyncStreamedStr:  # ruff: ignore
    ...


async def main():
    with log10_session(tags=["async_tag"]):
        output = await tell_story("Europe.")
        async for chunk in output:
            print(chunk, end="", flush=True)


asyncio.run(main())
