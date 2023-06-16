import os
from log10.load import log10
from log10.evals import compile
from log10.agents.camel import camel_agent
from log10.tools import code_extractor

# Select one of OpenAI or Anthropic models
#model = "gpt-3.5-turbo-16k"
model = "claude-1"
maxTurns = 10

if 'claude' in model:
    import anthropic
    log10(anthropic)
    anthropicClient = anthropic.Client(os.environ["ANTHROPIC_API_KEY"])
    module = anthropicClient
    hparams = {'max_tokens_to_sample': 1024}
    summary_model = "claude-1-100k"
    extraction_model = "claude-1-100k"
    completion_func = anthropicClient.completion
else:  # openai
    import openai
    log10(openai)
    openai.api_key = os.getenv("OPENAI_API_KEY")
    hparams = {}
    module = openai
    summary_model = "gpt-3.5-turbo-16k"
    extraction_model = "gpt-4"
    completion_func = openai.ChatCompletion.create

# example calls from playground (select 1)
user_messages, assistant_messages = camel_agent(userRole='C developer', assistantRole='Cybersecurity expert',
                                                taskPrompt="Correct the following code.\n\n#include <stdio.h>\n#include <string.h>\n\nint main() {\n    char password[8];\n    int granted = 0;\n\n    printf(\"Enter password: \");\n    scanf(\"%s\", password);\n\n    if (strcmp(password, \"password\") == 0) {\n        granted = 1;\n    }\n\n    if (granted) {\n        printf(\"Access granted.\\n\");\n    } else {\n        printf(\"Access denied.\\n\");\n    }\n\n    return 0;\n}",
                                                model=model, summary_model=summary_model, maxTurns=maxTurns,
                                                module=module, hparams=hparams)

full_response = assistant_messages[-1]['content']

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
