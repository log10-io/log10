import pytest
import lamini
from log10.load import log10

log10(lamini)


@pytest.mark.chat
def test_generate():
    llm = lamini.Lamini("meta-llama/Llama-2-7b-chat-hf")
    response = llm.generate("What's 2 + 9 * 3?")

    assert isinstance(response, str)
    assert "29" in response
