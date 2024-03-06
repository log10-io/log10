import openai
from magentic import AsyncStreamedStr, FunctionCall, prompt

from log10.load import log10


log10(openai)


def add(x: int, y: int) -> int:
    """Add together two numbers."""
    return x + y


@prompt("What is 1+1? Use tools", functions=[add])
async def agent() -> AsyncStreamedStr:  # ruff: ignore
    ...


# Define an async main function
async def main():
    response = await agent()
    if isinstance(response, FunctionCall):
        print(response)
    else:
        async for chunk in response:
            print(chunk, end="", flush=True)


# Running the main function using asyncio
if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
