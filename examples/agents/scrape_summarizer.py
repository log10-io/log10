import os
from log10.agents.scrape_summarizer import scrape_summarizer
from log10.llm import Anthropic, NoopLLM, OpenAI
from log10.load import log10


# Select one of OpenAI or Anthropic models
# model = "gpt-3.5-turbo-16k"
# model = "claude-1"
model = "noop"

llm = None
if "claude" in model:
    llm = Anthropic({"model": model})
elif model == "noop":
    llm = NoopLLM()
else:
    llm = OpenAI({"model": model})

url = "https://nytimes.com"
print(scrape_summarizer(url, llm))
