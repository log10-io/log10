
import os
from log10.load import log10
from log10.evals import compile
from log10.tools import code_extractor
from log10.utils import convert_history_to_claude

# Select one of OpenAI or Anthropic models
model = "gpt-3.5-turbo"
#model = "claude-1"

if 'claude' in model:
    import anthropic
    log10(anthropic)
    anthropicClient = anthropic.Client(os.environ["ANTHROPIC_API_KEY"])
    module = anthropicClient
    hparams = {'max_tokens_to_sample': 1024}
    extraction_model = "claude-1-100k"
    completion_func = anthropicClient.completion
else:  # openai
    import openai
    log10(openai)
    openai.api_key = os.getenv("OPENAI_API_KEY")
    hparams = {}
    module = openai
    extraction_model = "gpt-4"
    completion_func = openai.ChatCompletion.create

# First, write a hello world program
messages = [
    {"role": "system", "content": "You are an expert C programmer."},
    {"role": "user", "content": "Write a hello world program. Insert a null character after the hello world"}
]

if 'claude' in model:
    prompt = convert_history_to_claude(messages)
    completion = anthropicClient.completion(prompt=prompt, model=model, **hparams)
    full_response = completion['completion']
else:
    completion = openai.ChatCompletion.create(model=model, messages=messages, temperature=0.2, **hparams)
    full_response = completion.choices[0].message.content
print(f"Full response\n###\n{full_response}")

# Next extract just the C code
code = code_extractor(full_response, "C", completion_func, extraction_model, hparams)
print(f"Extracted code\n###\n{code}")

# Evaluate if the code compiles
result = compile(code)
if result is True:
    print("Compilation successful")
else:
    print("Compilation failed with error:")
    print(result[1])
