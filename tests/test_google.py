import google.generativeai as genai
import pytest

from log10.load import log10


log10(genai)


@pytest.mark.chat
def test_genai_chat(google_model):
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
    assert text, "No output from the model."


@pytest.mark.chat
def test_genai_chat_w_history(google_model):
    model = genai.GenerativeModel(google_model, system_instruction="You are a cat. Your name is Neko.")
    chat = model.start_chat(
        history=[
            {"role": "user", "parts": [{"text": "please say yes."}]},
            {"role": "model", "parts": [{"text": "Yes yes yes?"}]},
        ]
    )

    prompt = "please say no."
    response = chat.send_message(prompt)

    text = response.text
    assert isinstance(text, str)
    assert text, "No output from the model."
