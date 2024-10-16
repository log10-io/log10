import pytest

from log10.completions import Completions
from tests.utils import _LogAssertion


@pytest.mark.chat
@pytest.mark.parametrize("model", ["claude-3-haiku-20240307", "gpt-4o"])
def test_mock_chat_completions(model):
    cmpl = Completions()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What's the capital of France?"},
    ]
    response_content = "The capital of France is Paris."
    tags = ["pytest", "geography"]

    result = cmpl.mock_chat_completions(model=model, messages=messages, response_content=response_content, tags=tags)

    assert result.model == model
    assert result.choices[0].message.content == response_content
    assert result.choices[0].message.role == "assistant"
    assert result.object == "chat.completion"

    _LogAssertion(
        completion_id=result.id.replace("chatcmpl-", ""), message_content=response_content
    ).assert_chat_response()
