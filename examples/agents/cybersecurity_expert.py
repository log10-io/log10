import os
from log10.load import log10
from log10.agents.camel import camel_agent
from dotenv import load_dotenv
load_dotenv()

# Select one of OpenAI or Anthropic models
model = "gpt-3.5-turbo-16k"
# model = "claude-1"
maxTurns = 30

if 'claude' in model:
    import anthropic
    log10(anthropic)
    anthropicClient = anthropic.Client(os.environ["ANTHROPIC_API_KEY"])
    module = anthropicClient
    hparams = {'max_tokens_to_sample': 1024}
    summary_model = "claude-1-100k"
else:  # openai
    import openai
    log10(openai)
    openai.api_key = os.getenv("OPENAI_API_KEY")
    hparams = {}
    module = openai
    summary_model = "gpt-3.5-turbo-16k"

# example calls from playground (select 1)
camel_agent(userRole='C developer', assistantRole='Cybersecurity expert',
            taskPrompt="Correct the following code.\n\n#include <stdio.h>\n#include <string.h>\n\nint main() {\n    char password[8];\n    int granted = 0;\n\n    printf(\"Enter password: \");\n    scanf(\"%s\", password);\n\n    if (strcmp(password, \"password\") == 0) {\n        granted = 1;\n    }\n\n    if (granted) {\n        printf(\"Access granted.\\n\");\n    } else {\n        printf(\"Access denied.\\n\");\n    }\n\n    return 0;\n}",
            model=model, summary_model=summary_model, maxTurns=maxTurns,
            module=module, hparams=hparams)
