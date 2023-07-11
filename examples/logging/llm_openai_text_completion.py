import logging

logging.basicConfig(level=logging.DEBUG)

from log10.llm import Log10Config, Message
from log10.openai import OpenAI


llm = OpenAI({"model": "gpt-3.5-turbo"}, log10_config=Log10Config())
completion = llm.chat(
    [
        Message(role="user", content="Hello, how are you?"),
    ]
)
print(completion.to_dict())
