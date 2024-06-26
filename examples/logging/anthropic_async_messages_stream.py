import asyncio

import anthropic

from log10._httpx_utils import finalize
from log10.load import log10


log10(anthropic)

client = anthropic.AsyncAnthropic()


async def main() -> None:
    async with client.messages.stream(
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": "Help me create some similes to describe a person's laughter that is joyful and contagious?",
            }
        ],
        model="claude-3-haiku-20240307",
    ) as stream:
        async for text in stream.text_stream:
            print(text, end="", flush=True)
        print()

    # you can still get the accumulated final message outside of
    # the context manager, as long as the entire stream was consumed
    # inside of the context manager
    accumulated = await stream.get_final_message()
    print("accumulated message: ", accumulated.to_json())
    await finalize()


asyncio.run(main())
