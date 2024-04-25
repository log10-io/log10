import openai
from magentic import StreamedStr, prompt

from log10.load import log10


log10(openai, USE_ASYNC_=True)


@prompt("Tell me a joke")
def llm() -> StreamedStr: ...


response = llm()
for chunk in response:
    print(chunk, end="", flush=True)
