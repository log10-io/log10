import vertexai
from vertexai.preview.generative_models import GenerationConfig, GenerativeModel

from log10.load import log10


log10(vertexai)

# change these to your own project and location
project_id = "YOUR_PROJECT_ID"
location = "YOUR_LOCATION"
vertexai.init(project=project_id, location=location)

model = GenerativeModel("gemini-1.0-pro")
chat = model.start_chat()

prompt = "What's the top 5 largest constellations you can find in North American during March?"
generation_config = GenerationConfig(
    temperature=0.9,
    max_output_tokens=512,
)
response = chat.send_message(prompt, generation_config=generation_config)
print(response.text)
