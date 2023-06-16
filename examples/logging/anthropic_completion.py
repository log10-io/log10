import os
from log10.load import log10
import anthropic
import os

log10(anthropic, DEBUG_=False)
anthropicClient = anthropic.Client(os.environ["ANTHROPIC_API_KEY"])

response = anthropicClient.completion(
    model="claude-1",
    prompt=f"\n\nHuman:Write the names of all Star Wars movies and spinoffs along with the time periods in which they were set?{anthropic.AI_PROMPT}",
    temperature=0,
    max_tokens_to_sample=1024,
    top_p=1,
    top_k=0
)

print(response)
