import google.generativeai as genai

from log10.load import log10


log10(genai)


model = genai.GenerativeModel("gemini-1.0-pro")
chat = model.start_chat()

prompt = "What's the top 5 largest constellations you can find in North American during April? And describe each of them in 3 sentences."
generation_config = genai.GenerationConfig(
    temperature=0.9,
    max_output_tokens=512,
)
response = chat.send_message(prompt, generation_config=generation_config)
print(response.text)
