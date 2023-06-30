import os
from log10.llm import Anthropic, NoopLLM, OpenAI
from log10.load import log10
from log10.agents.camel import camel_agent
from dotenv import load_dotenv

load_dotenv()

# Select one of OpenAI or Anthropic models
# model = "noop"
model = "gpt-3.5-turbo-16k"
# model = "claude-1"
max_turns = 30

llm = None
summary_model = None
if "claude" == model:
    summary_model = "claude-1-100k"
    llm = Anthropic({"model": model})
elif model == "noop":
    summary_model = model
    llm = NoopLLM()
else:
    summary_model = "gpt-3.5-turbo-16k"
    llm = OpenAI({"model": model})

# example calls from playground (select 1)
camel_agent(
    user_role="Poor PhD Student",
    assistant_role="Experienced Computational Chemist",
    task_prompt="Perform a molecular dynamics solution of a molecule: CN1CCC[C@H]1c2cccnc2. Design and conduct a 100 ns molecular dynamics simulation of the molecule CN1CCC[C@H]1c2cccnc2 in an explicit solvent environment using the CHARMM force field and analyze the conformational changes and hydrogen bonding patterns over time",
    summary_model=summary_model,
    max_turns=max_turns,
    llm=llm,
)
