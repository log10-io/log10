import logging

logging.basicConfig(level=logging.DEBUG)

from log10.llm import Log10Config, Message
from log10.anthropic import Anthropic


llm = Anthropic({"model": "claude-1"}, log10_config=Log10Config())
completion = llm.chat(
    [
        Message(role="user", content="Hello, how are you?"),
    ]
)
print(completion.to_dict())
