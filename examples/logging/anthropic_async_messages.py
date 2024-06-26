import asyncio

from log10._httpx_utils import finalize
from log10.load import AsyncAnthropic


client = AsyncAnthropic()


async def main() -> None:
    message = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": "Generate complex and creative tongue twisters. Aim to create tongue twisters that are not only challenging to say but also engaging, entertaining, and potentially humorous. Consider incorporating wordplay, rhyme, and alliteration to enhance the difficulty and enjoyment of the tongue twisters.",
            }
        ],
    )

    print(message)
    await finalize()


asyncio.run(main())
