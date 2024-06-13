import google.generativeai as genai
import pytest

from log10.load import log10
from tests.utils import _LogAssertion


log10(genai)


@pytest.mark.chat
def test_genai_chat(session, google_model):
    model = genai.GenerativeModel(google_model)
    chat = model.start_chat()

    prompt = "Say this is a test"
    generation_config = genai.GenerationConfig(
        temperature=0.9,
        max_output_tokens=512,
    )
    response = chat.send_message(prompt, generation_config=generation_config)

    text = response.text
    assert isinstance(text, str)
    _LogAssertion(completion_id=session.last_completion_id(), message_content=text).assert_chat_response()


@pytest.mark.chat
def test_genai_chat_w_history(session, google_model):
    model = genai.GenerativeModel(
        google_model,
        system_instruction="You will be provided with statements, and your task is to convert them to standard English.",
    )
    chat = model.start_chat(
        history=[
            {"role": "user", "parts": [{"text": "He no went to the market."}]},
            {"role": "model", "parts": [{"text": "He did not go to the market."}]},
        ]
    )

    prompt = "She no went to the market."
    response = chat.send_message(prompt)

    text = response.text
    assert isinstance(text, str)
    _LogAssertion(completion_id=session.last_completion_id(), message_content=text).assert_chat_response()
