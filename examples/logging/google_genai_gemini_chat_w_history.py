import google.generativeai as genai

from log10.load import log10


log10(genai)


model = genai.GenerativeModel(
    "gemini-1.5-pro-latest",
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

print(response.text)
