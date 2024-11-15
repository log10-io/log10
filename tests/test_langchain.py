import anthropic
import openai
import pytest
from langchain.schema import HumanMessage, SystemMessage
from langchain_community.chat_models import ChatAnthropic, ChatOpenAI

from log10.load import log10
from tests.utils import _LogAssertion


@pytest.mark.chat
def test_chat_openai_messages(session, openai_model):
    log10(openai)
    llm = ChatOpenAI(
        model_name=openai_model,
        temperature=0.5,
    )
    messages = [SystemMessage(content="You are a ping pong machine"), HumanMessage(content="Ping?")]
    completion = llm.predict_messages(messages)

    content = completion.content
    assert isinstance(content, str)
    assert content, "No output from the model."
    _LogAssertion(completion_id=session.last_completion_id(), message_content=content).assert_chat_response()


@pytest.mark.skip(reason="Anthropic API removed count_tokens in 0.39.0, langchain_community not updated")
@pytest.mark.chat
def test_chat_anthropic_messages(session, anthropic_model):
    log10(anthropic)
    llm = ChatAnthropic(model=anthropic_model, temperature=0.7)
    messages = [SystemMessage(content="You are a ping pong machine"), HumanMessage(content="Ping?")]
    completion = llm.predict_messages(messages)

    content = completion.content
    assert isinstance(content, str)
    _LogAssertion(completion_id=session.last_completion_id(), text=content).assert_text_response()
