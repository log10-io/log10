import os
from log10.load import log10
import openai

log10(openai)

openai.api_key = os.getenv("OPENAI_API_KEY")
MAX_TOKENS = 512
TOOLS_DEFAULT_LIST =  ['llm-math', 'wikipedia']

from langchain.llms import OpenAI
from langchain.agents import load_tools, initialize_agent
import wikipedia

llm = OpenAI(temperature=0, model_name="text-davinci-003", max_tokens=MAX_TOKENS)

# Set up Langchain
tools = load_tools(TOOLS_DEFAULT_LIST, llm=llm)
chain = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)

inp = "How many years elapsed between the founding of Apple and Google?"
print(chain.run(inp))