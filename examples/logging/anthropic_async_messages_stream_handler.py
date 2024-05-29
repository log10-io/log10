import asyncio

import anthropic
from anthropic import AsyncAnthropic, AsyncMessageStream
from anthropic.types import MessageStreamEvent
from typing_extensions import override

from log10.load import log10


log10(anthropic)

client = AsyncAnthropic()


class MyStream(AsyncMessageStream):
    @override
    async def on_stream_event(self, event: MessageStreamEvent) -> None:
        print("on_event fired with:", event)


async def main() -> None:
    async with client.messages.stream(
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": "Say hello there!",
            }
        ],
        model="claude-3-haiku-20240307",
        event_handler=MyStream,
    ) as stream:
        accumulated = await stream.get_final_message()
        print("accumulated message: ", accumulated.to_json())


asyncio.run(main())
