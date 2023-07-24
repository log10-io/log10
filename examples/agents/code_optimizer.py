"""Code optimizer agent example."""
# flake8: noqa

import anthropic
import openai

from log10.agents.camel import camel_agent
from log10.anthropic import Anthropic
from log10.evals import compile
from log10.llm import NoopLLM
from log10.load import log10
from log10.openai import OpenAI
from log10.tools import code_extractor

# Select one of OpenAI or Anthropic models with "claude-1" or "gpt-3.5-turbo"
model = 'gpt-3.5-turbo-16k'
max_turns = 10

llm = None
summary_model = None
extraction_model = None
if 'claude' in model:
    log10(anthropic)
    summary_model = 'claude-1-100k'
    extraction_model = 'claude-1-100k'
    llm = Anthropic({'model': model})
elif model == 'noop':
    summary_model = model
    extraction_model = model
    llm = NoopLLM()
else:
    log10(openai)
    summary_model = 'gpt-3.5-turbo-16k'
    extraction_model = 'gpt-4'
    llm = OpenAI({'model': model})

# example calls from playground (select 1)
user_messages, assistant_messages = camel_agent(
    user_role='C developer',
    assistant_role='Cybersecurity expert',
    # noqa: WPS323 WPS342
    task_prompt="""
Correct the following code.

#include <stdio.h>
#include <string.h>

int main() {
    char password[8];
    int granted = 0;

    printf("Enter password: ");
    scanf("%s", password);
    if (strcmp(password, "password") == 0) {
        granted = 1;
    }

    if (granted) {
        printf("Access granted.\\n");
    } else {
        printf("Access denied.\\n");
    }

    return 0;
}
""",
    summary_model=summary_model,
    max_turns=max_turns,
    llm=llm,
)

full_response = assistant_messages[-1].content

# Next extract just the C code
code = code_extractor(full_response, 'C', extraction_model, llm=llm)
print(f'Extracted code\n###\n{code}')

# Evaluate if the code compiles
result = compile(code)
if result is True:
    print('Compilation successful')
else:
    print('Compilation failed with error:')
    print(result[1])
