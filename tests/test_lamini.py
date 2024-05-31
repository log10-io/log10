import lamini
import pytest

from log10.load import log10
from tests.utils import _LogAssertion


log10(lamini)


@pytest.mark.chat
def test_generate(session, lamini_model):
    llm = lamini.Lamini(lamini_model)
    response = llm.generate("What's 2 + 9 * 3?")

    assert isinstance(response, str)
    assert "29" in response
    _LogAssertion(completion_id=session.last_completion_id(), message_content=response).assert_chat_response()
