import openai
from magentic import prompt

from log10.load import log10


log10(openai, USE_ASYNC_=True)


@prompt("Tell me a joke")
def llm() -> str: ...


print(llm())
