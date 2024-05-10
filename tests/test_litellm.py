import asyncio
import base64
import httpx
import pytest

import litellm
from log10.litellm import Log10LitellmLogger


@pytest.mark.chat
@pytest.mark.stream
def test_completion_stream(capfd):
    log10_handler = Log10LitellmLogger(tags=["litellm_completion", "stream"])
    litellm.callbacks = [log10_handler]
    response = litellm.completion(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": "Count to 10."}], stream=True
    )
    for chunk in response:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)

    out, err = capfd.readouterr()
    assert err == ""
    out_array = out.split(",")
    assert len(out_array) == 10


@pytest.mark.async_client
@pytest.mark.chat
@pytest.mark.stream
def test_completion_async_stream(capfd):
    log10_handler = Log10LitellmLogger(tags=["litellm_acompletion"])
    litellm.callbacks = [log10_handler]

    model_name = "claude-3-haiku-20240307"

    async def completion():
        response = await litellm.acompletion(
            model=model_name, messages=[{"role": "user", "content": "count to 10"}], stream=True
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)

    asyncio.run(completion())

    out, err = capfd.readouterr()
    assert err == ""
    assert isinstance(out, str)


@pytest.mark.vision
def test_image():
    log10_handler = Log10LitellmLogger(tags=["litellm_image"])
    litellm.callbacks = [log10_handler]

    image_url = "https://upload.wikimedia.org/wikipedia/commons/e/e8/Log10.png"
    image_media_type = "image/png"
    image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")

    model_name = "gpt-4-vision-preview"
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
    assert isinstance(resp.choices[0].message.content, str)


@pytest.mark.stream
@pytest.mark.vision
def test_image_stream(capfd):
    log10_handler = Log10LitellmLogger(tags=["litellm_image", "stream"])
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
        stream=True,
    )
    for chunk in resp:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)

    out, err = capfd.readouterr()
    assert err == ""
    assert isinstance(out, str)


@pytest.mark.async_client
@pytest.mark.stream
@pytest.mark.vision
def test_image_async_stream(capfd):
    log10_handler = Log10LitellmLogger(tags=["litellm_image", "stream", "async"])
    litellm.callbacks = [log10_handler]

    image_url = "https://upload.wikimedia.org/wikipedia/commons/e/e8/Log10.png"
    image_media_type = "image/png"
    image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")

    model_name = "claude-3-haiku-20240307"

    async def completion():
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
                        {
                            "type": "text",
                            "text": "What's the red curve in the figure, is it log2 or log10? Be concise.",
                        },
                    ],
                }
            ],
            stream=True,
        )
        for chunk in resp:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)

    asyncio.run(completion())

    out, err = capfd.readouterr()
    assert err == ""
    assert isinstance(out, str)
