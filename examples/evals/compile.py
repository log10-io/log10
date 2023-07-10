from log10.anthropic import Anthropic
from log10.llm import Message, NoopLLM
from log10.load import log10
from log10.evals import compile
from log10.openai import OpenAI
from log10.tools import code_extractor
from log10.utils import convert_history_to_claude

# Select one of OpenAI or Anthropic models
model = "gpt-3.5-turbo"
# model = "claude-1"


llm = None
if "claude" in model:
    llm = Anthropic({"model": model})
elif model == "noop":
    llm = NoopLLM()
else:
    llm = OpenAI({"model": model})


# First, write a hello world program
messages = [
    Message(role="system", content="You are an expert C programmer."),
    Message(
        role="user",
        content="Write a hello world program. Insert a null character after the hello world",
    ),
]

completion = llm.chat(messages, {"temperature": 0.2})
full_response = completion.content

print(f"Full response\n###\n{full_response}")

# Next extract just the C code
code = code_extractor(full_response, "C", llm)
print(f"Extracted code\n###\n{code}")

# Evaluate if the code compiles
result = compile(code)
if result is True:
    print("Compilation successful")
else:
    print("Compilation failed with error:")
    print(result[1])
