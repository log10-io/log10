import lamini
import pytest

from log10.load import log10


log10(lamini)


@pytest.mark.chat
def test_generate(lamini_model):
    model_name = lamini_model or "meta-llama/Llama-2-7b-chat-hf"
    llm = lamini.Lamini(model_name)
    response = llm.generate("What's 2 + 9 * 3?")

    assert isinstance(response, str)
    assert "29" in response
