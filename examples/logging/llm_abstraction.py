from log10.llm import LLM, Message
from log10.openai import OpenAI
from log10.anthropic import Anthropic

llm = OpenAI({"model": "gpt-3.5-turbo"})
response = llm.chat([Message(role="user", content="Hello, how are you?")])
print(response)

llm = OpenAI({"model": "text-davinci-003"})
response = llm.text("Hello, how are you?")
print(response)

llm = Anthropic({"model": "claude-2"})
response = llm.chat([Message(role="user", content="Hello, how are you?")])
print(response)