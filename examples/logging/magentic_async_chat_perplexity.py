import asyncio

import openai
from magentic import UserMessage, chatprompt
from magentic.chat_model.litellm_chat_model import LitellmChatModel

from log10._httpx_utils import finalize
from log10.load import log10


log10(openai)


async def main(topic: str) -> str:
    @chatprompt(
        UserMessage(f"Tell me a joke about {topic}"),
        model=LitellmChatModel(model="perplexity/llama-3.1-sonar-small-128k-chat"),
    )
    async def tell_joke(topic: str) -> str: ...

    print(await tell_joke(topic))
    await finalize()


asyncio.run(main("cats"))
