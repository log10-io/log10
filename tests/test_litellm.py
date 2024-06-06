import base64
import time

import httpx
import litellm
import pytest

from log10._httpx_utils import finalize
from log10.litellm import Log10LitellmLogger
from tests.utils import _LogAssertion


### litellm seems allowing to use multiple callbacks
### which causes some previous tags to be added to the next callback
### when running multiple tests at the same time

log10_handler = Log10LitellmLogger(tags=["litellm_test"])
litellm.callbacks = [log10_handler]


@pytest.mark.chat
@pytest.mark.stream
def test_completion_stream(session, openai_model):
    response = litellm.completion(
        model=openai_model, messages=[{"role": "user", "content": "Count to 6."}], stream=True
    )

    output = ""
    for chunk in response:
        if chunk.choices[0].delta.content:
            output += chunk.choices[0].delta.content

    time.sleep(1)

    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.async_client
@pytest.mark.chat
@pytest.mark.stream
@pytest.mark.asyncio(scope="module")
async def test_completion_async_stream(anthropic_model):
    response = await litellm.acompletion(
        model=anthropic_model, messages=[{"role": "user", "content": "count to 8"}], stream=True
    )

    output = ""
    async for chunk in response:
        if chunk.choices[0].delta.content:
            output += chunk.choices[0].delta.content

    ## This test doesn't get completion_id from the session
    ## and logged a couple times during debug mode, punt this for now
    await finalize()
    assert output, "No output from the model."


@pytest.mark.vision
def test_image(session, openai_vision_model):
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

    # Wait for the completion to be logged
    time.sleep(3)
    _LogAssertion(completion_id=session.last_completion_id(), message_content=content).assert_chat_response()


@pytest.mark.stream
@pytest.mark.vision
def test_image_stream(session, anthropic_model):
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

    time.sleep(3)
    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.async_client
@pytest.mark.stream
@pytest.mark.vision
@pytest.mark.asyncio(scope="module")
async def test_image_async_stream(session, anthropic_model):
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

    time.sleep(3)
    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()
