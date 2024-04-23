import google.generativeai as genai

from log10.load import log10


log10(genai)


model = genai.GenerativeModel("gemini-1.5-pro-latest", system_instruction="You are a cat. Your name is Neko.")
chat = model.start_chat(
    history=[
        {"role": "user", "parts": [{"text": "please say yes."}]},
        {"role": "model", "parts": [{"text": "Yes yes yes?"}]},
    ]
)

prompt = "please say no."
response = chat.send_message(prompt)

print(response.text)
