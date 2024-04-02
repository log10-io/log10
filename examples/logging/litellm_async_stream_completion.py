import asyncio

import litellm

from log10.litellm import Log10LitellmLogger


log10_handler = Log10LitellmLogger(tags=["litellm_acompletion"])
litellm.callbacks = [log10_handler]

model_name = "claude-3-haiku-20240307"


async def completion():
    response = await litellm.acompletion(
        model=model_name, messages=[{"role": "user", "content": "count to 10"}], stream=True
    )
    async for chunk in response:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)


asyncio.run(completion())
