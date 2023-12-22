from log10.llm import Log10Config
from log10.mosaicml import MosaicML, llama_2_70b_chat


llm = MosaicML({"model": "llama2-70b-chat/v1"}, log10_config=Log10Config())
response = llm.text("Hello, how are you?", {"temperature": 0.3, "max_new_tokens": 10})
print(response)

response = llama_2_70b_chat(
    "Hello, how are you?",
    {"temperature": 0.3, "max_new_tokens": 10},
    log10_config=Log10Config(),
)
print(response)
