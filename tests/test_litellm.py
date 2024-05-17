import base64
import re

import httpx
import litellm
import pytest

from log10.litellm import Log10LitellmLogger


@pytest.mark.chat
@pytest.mark.stream
def test_completion_stream(openai_model):
    log10_handler = Log10LitellmLogger(tags=["litellm_completion", "stream"])
    litellm.callbacks = [log10_handler]
    response = litellm.completion(
        model=openai_model, messages=[{"role": "user", "content": "Count to 10."}], stream=True
    )

    output = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            output += chunk.choices[0].delta.content

    results = re.split("[,.]", output)
    filter_output = [s for s in results if s]

    assert len(filter_output) == 10


@pytest.mark.async_client
@pytest.mark.chat
@pytest.mark.stream
@pytest.mark.asyncio
async def test_completion_async_stream(anthropic_model):
    log10_handler = Log10LitellmLogger(tags=["litellm_acompletion"])
    litellm.callbacks = [log10_handler]

    response = await litellm.acompletion(
        model=anthropic_model, messages=[{"role": "user", "content": "count to 10"}], stream=True
    )

    output = ""
    async for chunk in response:
        if chunk.choices[0].delta.content:
            output += chunk.choices[0].delta.content.strip()

    results = re.split("[,.]", output)
    filter_output = [r for r in results if r]
    assert len(filter_output) == 10


@pytest.mark.vision
def test_image(openai_vision_model):
    log10_handler = Log10LitellmLogger(tags=["litellm_image"])
    litellm.callbacks = [log10_handler]

    image_url = "https://upload.wikimedia.org/wikipedia/commons/e/e8/Log10.png"
    image_media_type = "image/png"
    image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")

    resp = litellm.completion(
        model=openai_vision_model,
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

    content = resp.choices[0].message.content
    assert isinstance(content, str)
    assert "log10" in content.lower()


@pytest.mark.stream
@pytest.mark.vision
def test_image_stream(anthropic_model):
    log10_handler = Log10LitellmLogger(tags=["litellm_image", "stream"])
    litellm.callbacks = [log10_handler]

    image_url = "https://upload.wikimedia.org/wikipedia/commons/e/e8/Log10.png"
    image_media_type = "image/png"
    image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")

    resp = litellm.completion(
        model=anthropic_model,
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
        stream=True,
    )

    output = ""
    for chunk in resp:
        if chunk.choices[0].delta.content:
            output += chunk.choices[0].delta.content

    assert "The red curve in the figure" in output
    assert "log10" in output


@pytest.mark.async_client
@pytest.mark.stream
@pytest.mark.vision
@pytest.mark.asyncio
async def test_image_async_stream(anthropic_model):
    log10_handler = Log10LitellmLogger(tags=["litellm_image", "stream", "async"])
    litellm.callbacks = [log10_handler]

    image_url = "https://upload.wikimedia.org/wikipedia/commons/e/e8/Log10.png"
    image_media_type = "image/png"
    image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")

    resp = litellm.completion(
        model=anthropic_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{image_media_type};base64,{image_data}"},
                    },
                    {
                        "type": "text",
                        "text": "What's the red curve in the figure, is it log2 or log10? Be concise.",
                    },
                ],
            }
        ],
        stream=True,
    )

    output = ""
    for chunk in resp:
        if chunk.choices[0].delta.content:
            output += chunk.choices[0].delta.content

    assert "The red curve in the figure" in output
    assert "log10" in output
