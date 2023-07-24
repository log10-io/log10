"""Example of a biochemist agent using the camel agent framework."""

import anthropic
import openai
from dotenv import load_dotenv

from log10.agents.camel import camel_agent
from log10.anthropic import Anthropic
from log10.llm import NoopLLM
from log10.load import log10
from log10.openai import OpenAI

load_dotenv()

# Select one of OpenAI or Anthropic models with "claude-1" or "gpt-3.5-turbo"
model = 'gpt-3.5-turbo-16k'
max_turns = 30

llm = None
summary_model = None
if 'claude' in model:
    log10(anthropic)
    summary_model = 'claude-1-100k'
    llm = Anthropic({'model': model})
elif model == 'noop':
    summary_model = model
    llm = NoopLLM()
else:
    log10(openai)
    summary_model = 'gpt-3.5-turbo-16k'
    llm = OpenAI({'model': model})

# example calls from playground (select 1)
camel_agent(
    user_role='Poor PhD Student',
    assistant_role='Experienced Computational Chemist',
    task_prompt="""
Perform a molecular dynamics solution of a molecule: CN1CCC[C@H]1c2cccnc2.
Design and conduct a 100 ns molecular dynamics simulation of the molecule
CN1CCC[C@H]1c2cccnc2 in an explicit solvent environment using the CHARMM
force field and analyze the conformational changes and hydrogen bonding
patterns over time""",
    summary_model=summary_model,
    max_turns=max_turns,
    llm=llm,
)
