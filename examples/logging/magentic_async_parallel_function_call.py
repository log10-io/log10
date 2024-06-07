import asyncio

import openai
from magentic import AsyncParallelFunctionCall, prompt

from log10._httpx_utils import finalize
from log10.load import log10


log10(openai)


def plus(a: int, b: int) -> int:
    return a + b


async def minus(a: int, b: int) -> int:
    return a - b


@prompt("Sum {a} and {b}. Also subtract {a} from {b}.", functions=[plus, minus])
async def plus_and_minus(a: int, b: int) -> AsyncParallelFunctionCall[int]: ...


async def main():
    output = await plus_and_minus(2, 3)
    async for chunk in output:
        print(chunk)
    await finalize()


asyncio.run(main())
