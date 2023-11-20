import os
from typing import Any, Optional

from dotenv import load_dotenv

from log10.agents.camel import camel_agent
from log10.anthropic import Anthropic
from log10.llm import NoopLLM
from log10.load import log10
from log10.openai import OpenAI

load_dotenv()

# Select one of OpenAI or Anthropic models
model = os.environ.get("LOG10_EXAMPLES_MODEL", "gpt-3.5-turbo-16k")
max_turns = 30

llm: Optional[Any] = None
summary_model = None
if "claude" in model:
    import anthropic

    log10(anthropic)
    summary_model = "claude-1-100k"
    llm = Anthropic({"model": model})
elif model == "noop":
    summary_model = model
    llm = NoopLLM()
else:
    import openai

    log10(openai)
    summary_model = "gpt-3.5-turbo-16k"
    llm = OpenAI({"model": model})

task_prompt = """Correct the following code.
```
#include <stdio.h>
#include <string.h>
int main() {
    i
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
}```"""
# example calls from playground (select 1)
camel_agent(
    user_role="C developer",
    assistant_role="Cybersecurity expert",
    task_prompt=task_prompt,
    summary_model=summary_model,
    max_turns=max_turns,
    llm=llm,
)
