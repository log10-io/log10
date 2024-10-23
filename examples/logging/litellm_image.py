import base64

import httpx
import litellm

from log10.litellm import Log10LitellmLogger


log10_handler = Log10LitellmLogger(tags=["litellm_image"])
litellm.callbacks = [log10_handler]

image_url = "https://upload.wikimedia.org/wikipedia/commons/e/e8/Log10.png"
image_media_type = "image/png"
image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")


model_name = "claude-3-haiku-20240307"
resp = litellm.completion(
    model=model_name,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image_media_type};base64,{image_data}"},
                },
                {"type": "text", "text": "What's the red curve in the figure, is it log2 or log10? Be concise."},
            ],
        }
    ],
)
print(resp.choices[0].message.content)
