import os

import anthropic

from log10.load import Anthropic


client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], tags=["test", "load_anthropic"])

response = client.completions.create(
    model="claude-3-haiku-20240307",
    prompt=f"\n\nHuman:Write the names of all Star Wars movies and spinoffs along with the time periods in which they were set?{anthropic.AI_PROMPT}",
    temperature=0,
    max_tokens_to_sample=1024,
    top_p=1,
    top_k=0,
)

print(response)
