import openai
from magentic import SystemMessage, chatprompt
from magentic.vision import UserImageMessage

from log10.load import log10


log10(openai)

with open("./examples/logging/large_image.png", "rb") as f:
    image_bytes = f.read()


@chatprompt(SystemMessage("What's in the following screenshot?"), UserImageMessage(image_bytes))
def _llm() -> str: ...


_llm()
