
import os
from log10.agents.scrape_summarizer import scrape_summarizer
from log10.load import log10


# Select one of OpenAI or Anthropic models
model = "gpt-3.5-turbo-16k"
# model = "claude-1"

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

url = "https://nytimes.com"
print(scrape_summarizer(url, model, module, hparams))
