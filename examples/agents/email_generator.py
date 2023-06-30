import os
from log10.llm import Anthropic, NoopLLM, OpenAI
from log10.load import log10
from log10.agents.camel import camel_agent
from dotenv import load_dotenv

load_dotenv()

# Select one of OpenAI or Anthropic models
model = "gpt-3.5-turbo-16k"
# model = "claude-1"
# model = "noop"
max_turns = 30

llm = None
summary_model = None
if "claude" in model:
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
    user_role="Sales email copyeditor",
    assistant_role="Sales email copywriter",
    task_prompt="Write a sales email to Pfizer about a new healthcare CRM",
    summary_model=summary_model,
    max_turns=max_turns,
    llm=llm,
)
