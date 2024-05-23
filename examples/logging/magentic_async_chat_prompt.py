import asyncio

import anthropic
from magentic import UserMessage, chatprompt
from magentic.chat_model.anthropic_chat_model import AnthropicChatModel

from log10.load import log10


log10(anthropic)


async def main(topic: str) -> str:
    @chatprompt(
        UserMessage(f"Tell me a joke about {topic}"),
        model=AnthropicChatModel("claude-3-opus-20240229"),
    )
    async def tell_joke(topic: str) -> str: ...

    print(await tell_joke(topic))


asyncio.run(main("cats"))
