from langchain.chat_models import ChatAnthropic
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage, BaseMessage

from log10.langchain import Log10Callback
from log10.llm import Log10Config


log10_callback = Log10Callback(log10_config=Log10Config())

llm = ChatOpenAI(model_name="gpt-3.5-turbo", callbacks=[log10_callback], temperature=0.5)

prompt = "Alice has a parrot. What animal is Alice's pet?"
messages = [
    HumanMessage(content="You are a ping pong machine"),
    HumanMessage(content="Ping?"),
]
completion = llm.predict_messages(messages)
print(completion)

llm = ChatAnthropic(model="claude-2", callbacks=[log10_callback], temperature=0.7)
llm.predict_messages(messages)
print(completion)