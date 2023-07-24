import os

from dotenv import load_dotenv

from log10.agents.camel import camel_agent
from log10.anthropic import Anthropic
from log10.llm import NoopLLM
from log10.load import log10
from log10.openai import OpenAI

load_dotenv()

# Select one of OpenAI or Anthropic models
model = 'gpt-3.5-turbo-16k'
# model = "claude-1"
# model = "noop"
max_turns = 30

llm = None
summary_model = None
if 'claude' in model:
    import anthropic

    log10(anthropic)
    summary_model = 'claude-1-100k'
    llm = Anthropic({'model': model})
elif model == 'noop':
    summary_model = model
    llm = NoopLLM()
else:
    import openai

    log10(openai)
    summary_model = 'gpt-3.5-turbo-16k'
    llm = OpenAI({'model': model})

# example calls from playground (select 1)
camel_agent(
    user_role='Sales email copyeditor',
    assistant_role='Sales email copywriter',
    task_prompt='Write a sales email to Pfizer about a new healthcare CRM',
    summary_model=summary_model,
    max_turns=max_turns,
    llm=llm,
)
