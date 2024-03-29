import os

import anthropic

from log10.load import log10


log10(anthropic, DEBUG_=False)
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

response = client.completions.create(
    model="claude-instant-1.2",
    prompt=f"\n\nHuman:Write the names of all Star Wars movies and spinoffs along with the time periods in which they were set?{anthropic.AI_PROMPT}",
    temperature=0,
    max_tokens_to_sample=1024,
    top_p=1,
    top_k=0,
)

print(response)
