import asyncio

import openai
from magentic import AsyncStreamedStr, OpenaiChatModel, prompt

from log10.load import log10, log10_session


log10(openai)


@prompt("What is {a} * {b}?", model=OpenaiChatModel(model="gpt-4-turbo-preview"))
async def do_math_with_llm_async(a: int, b: int) -> AsyncStreamedStr:  # ruff: ignore
    ...  # ruff: ignore


async def main():
    with log10_session(tags=["test_tag_a"]):
        result = await do_math_with_llm_async(2, 2)
        async for chunk in result:
            print(chunk, end="", flush=True)

    result = await do_math_with_llm_async(2.5, 2.5)
    async for chunk in result:
        print(chunk, end="", flush=True)

    with log10_session(tags=["test_tag_b"]):
        result = await do_math_with_llm_async(3, 3)
        async for chunk in result:
            print(chunk, end="", flush=True)


asyncio.run(main())
