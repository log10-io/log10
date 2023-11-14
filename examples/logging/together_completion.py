from log10.together import llama_2_70b_chat, Together
from log10.llm import Log10Config

config = Log10Config()
llm = Together({"model": "togethercomputer/llama-2-70b-chat"}, log10_config=config)
response = llm.text("Hello, how are you?", {"temperature": 0.3, "max_tokens": 10})
print(response)

response = llama_2_70b_chat(
    "Hello, how are you?",
    {"temperature": 0.3, "max_tokens": 10},
    log10_config=Log10Config(),
)
print(response)
