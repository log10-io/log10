import lamini

from log10.load import log10


log10(lamini)

llm = lamini.Lamini("meta-llama/Llama-2-7b-chat-hf")
response = llm.generate("What's 2 + 9 * 3?")

print(response)
