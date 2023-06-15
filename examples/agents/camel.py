import os
from log10.load import log10
from log10.agents.camel import run_camel_agent
from dotenv import load_dotenv
load_dotenv()

#model = "gpt-3.5-turbo" # one of Anthropic or OpenAI models
model = "claude-1"
maxTurns = 2

if 'claude' in model:
    import anthropic
    log10(anthropic)
    anthropicClient = anthropic.Client(os.environ["ANTHROPIC_API_KEY"])
    module=anthropicClient
    hparams = {'max_tokens_to_sample': 1024}
else:  # openai
    import openai
    log10(openai)
    openai.api_key = os.getenv("OPENAI_API_KEY")
    hparams = {}
    module=openai

# example calls from playground (select 1)
run_camel_agent(userRole='Stock Trader', assistantRole='Python Programmer',
                taskPrompt='Develop a trading bot for the stock market', model=model, maxTurns=maxTurns,
                module=module, hparams=hparams)
