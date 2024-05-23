import anthropic
import openai
import pytest
from langchain.chat_models import ChatAnthropic, ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from log10.load import log10


@pytest.mark.chat
def test_chat_openai_messages(openai_model):
    log10(openai)
    llm = ChatOpenAI(
        model_name=openai_model,
        temperature=0.5,
    )
    messages = [SystemMessage(content="You are a ping pong machine"), HumanMessage(content="Ping?")]
    completion = llm.predict_messages(messages)

    assert isinstance(completion.content, str)
    assert "pong" in completion.content.lower()


@pytest.mark.chat
def test_chat_anthropic_messages(anthropic_legacy_model):
    log10(anthropic)
    llm = ChatAnthropic(model=anthropic_legacy_model, temperature=0.7)
    messages = [SystemMessage(content="You are a ping pong machine"), HumanMessage(content="Ping?")]
    completion = llm.predict_messages(messages)

    content = completion.content
    assert isinstance(content, str)
    assert content, "No output from the model."
