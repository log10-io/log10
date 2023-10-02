from langchain import OpenAI
from langchain.chat_models import ChatAnthropic
from langchain.chat_models import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage

from log10.langchain import Log10Callback
from log10.llm import Log10Config


log10_callback = Log10Callback(log10_config=Log10Config())


messages = [
    SystemMessage(content="You are a ping pong machine"),
    HumanMessage(content="Ping?"),
    AIMessage(content="Pong"),
    HumanMessage(content="Ping ping"),
]

llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    callbacks=[log10_callback],
    temperature=0.5,
    tags=["test"],
)
completion = llm.predict_messages(messages, tags=["foobar"])
print(completion)

llm = ChatAnthropic(
    model="claude-2", callbacks=[log10_callback], temperature=0.7, tags=["baz"]
)
llm.predict_messages(messages)
print(completion)

llm = OpenAI(model_name="text-davinci-003", callbacks=[log10_callback], temperature=0.5)
completion = llm.predict("You are a ping pong machine.\nPing?\n")
print(completion)
