from langchain import OpenAI
from langchain.chat_models import ChatAnthropic
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

from log10.langchain import Log10Callback
from log10.llm import Log10Config


log10_callback = Log10Callback(log10_config=Log10Config())


messages = [
    HumanMessage(content="You are a ping pong machine"),
    HumanMessage(content="Ping?"),
]

llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    callbacks=[log10_callback],
    temperature=0.5,
    tags=["test"],
)
completion = llm.predict_messages(messages, tags=["foobar"])
print(completion)

print(log10_callback.last_completion_url())

llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    callbacks=[log10_callback],
    temperature=0.5,
    tags=["test"],
)
messages.append(HumanMessage(content="Pong!"))
completion = llm.predict_messages(messages, tags=["foobar"])
print(completion)

print(log10_callback.last_completion_url())
