import os
from log10.agents.scrape_summarizer import scrape_summarizer
from log10.anthropic import Anthropic
from log10.llm import NoopLLM
from log10.load import log10
from log10.openai import OpenAI


# Select one of OpenAI or Anthropic models
model = os.environ.get("LOG10_EXAMPLES_MODEL", "gpt-3.5-turbo-16k")

llm = None
if "claude" in model:
    import anthropic

    log10(anthropic)
    llm = Anthropic({"model": model})
elif model == "noop":
    llm = NoopLLM()
else:
    import openai

    log10(openai)
    llm = OpenAI({"model": model})

url = "https://nytimes.com"
print(scrape_summarizer(url, llm))
