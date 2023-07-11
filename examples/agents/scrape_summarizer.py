import os
from log10.agents.scrape_summarizer import scrape_summarizer
from log10.anthropic import Anthropic
from log10.llm import Log10Config, NoopLLM
from log10.openai import OpenAI


# Select one of OpenAI or Anthropic models
model = "gpt-3.5-turbo-16k"
# model = "claude-1"
# model = "noop"

llm = None
if "claude" in model:
    llm = Anthropic({"model": model}, log10_config=Log10Config())
elif model == "noop":
    llm = NoopLLM()
else:
    llm = OpenAI({"model": model}, log10_config=Log10Config())

url = "https://nytimes.com"
print(scrape_summarizer(url, llm))
