import asyncio
import os

from anthropic import AI_PROMPT

from log10._httpx_utils import finalize
from log10.load import AsyncAnthropic


client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"], tags=["test", "async_anthropic"])


async def main():
    response = await client.completions.create(
        model="claude-3-haiku-20240307",
        prompt=f"\n\nHuman:Write the names of all Star Wars movies and spinoffs along with the time periods in which they were set?{AI_PROMPT}",
        temperature=0,
        max_tokens_to_sample=1024,
        top_p=1,
        top_k=0,
    )

    print(response)
    await finalize()


asyncio.run(main())
