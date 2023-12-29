import openai

from log10.load import log10


log10(openai)

MAX_TOKENS = 512
TOOLS_DEFAULT_LIST = ["llm-math", "wikipedia"]

from langchain.agents import initialize_agent, load_tools
from langchain.llms import OpenAI


llm = OpenAI(temperature=0, model_name="text-davinci-003", max_tokens=MAX_TOKENS)

# Set up Langchain
tools = load_tools(TOOLS_DEFAULT_LIST, llm=llm)
chain = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=True)

inp = "How many years elapsed between the founding of Apple and Google?"
print(chain.run(inp))
