import base64

import httpx
import openai

from log10.load import log10


log10(openai)

client = openai.OpenAI()


image1_url = "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
image1_media_type = "image/jpeg"
image1_data = base64.b64encode(httpx.get(image1_url).content).decode("utf-8")


response = client.chat.completions.create(
    model="gpt-4-vision-preview",
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "What are in these image?",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image1_media_type};base64,{image1_data}"},
                },
            ],
        }
    ],
    max_tokens=300,
)
print(response.choices[0])
