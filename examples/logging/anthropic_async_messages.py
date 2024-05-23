import asyncio

import anthropic

from log10.load import log10


log10(anthropic)

client = anthropic.AsyncAnthropic()


async def main() -> None:
    message = await client.beta.tools.messages.create(
        model="claude-instant-1.2",
        max_tokens=1000,
        messages=[{"role": "user", "content": "Say hello!"}],
    )

    print(message)


asyncio.run(main())
