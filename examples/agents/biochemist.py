import os
from log10.load import log10
from log10.agents.camel import camel_agent
from dotenv import load_dotenv
load_dotenv()

# Select one of OpenAI or Anthropic models
model = "gpt-3.5-turbo-16k"
# model = "claude-1"
maxTurns = 30

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

# example calls from playground (select 1)
camel_agent(userRole='Poor PhD Student', assistantRole='Experienced Computational Chemist',
            taskPrompt='Perform a molecular dynamics solution of a molecule: CN1CCC[C@H]1c2cccnc2. Design and conduct a 100 ns molecular dynamics simulation of the molecule CN1CCC[C@H]1c2cccnc2 in an explicit solvent environment using the CHARMM force field and analyze the conformational changes and hydrogen bonding patterns over time',
            model=model, summary_model=summary_model, maxTurns=maxTurns,
            module=module, hparams=hparams)
