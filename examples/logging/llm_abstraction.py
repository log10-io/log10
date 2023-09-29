from log10.llm import LLM, Message
from log10.openai import OpenAI
from log10.anthropic import Anthropic
from log10.llm import Log10Config

llm = OpenAI({"model": "gpt-3.5-turbo"}, log10_config=Log10Config())
response = llm.chat([Message(role="user", content="Hello, how are you?")])
print(response)
print(f"Duration: {llm.last_duration()}")

llm = OpenAI({"model": "text-davinci-003"}, log10_config=Log10Config())
response = llm.text("Hello, how are you?")
print(response)
print(f"Duration: {llm.last_duration()}")

llm = Anthropic({"model": "claude-2"}, log10_config=Log10Config())
response = llm.chat([Message(role="user", content="Hello, how are you?")])
print(response)
print(f"Duration: {llm.last_duration()}")

response = llm.text("Foobarbaz")
print(response)
print(f"Duration: {llm.last_duration()}")
