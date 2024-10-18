import os
from typing import Literal

import anthropic
import openai
import pytest
from magentic import (
    AsyncParallelFunctionCall,
    AsyncStreamedStr,
    FunctionCall,
    OpenaiChatModel,
    StreamedStr,
    SystemMessage,
    chatprompt,
    prompt,
)
from magentic.chat_model.anthropic_chat_model import AnthropicChatModel
from magentic.chat_model.litellm_chat_model import LitellmChatModel
from magentic.vision import UserImageMessage
from pydantic import BaseModel

from log10._httpx_utils import finalize
from log10.load import log10, log10_session
from tests.utils import _LogAssertion, format_magentic_function_args


def _get_model_obj(llm_provider, model, params):
    provider_map = {
        "openai": (OpenaiChatModel, (log10, {"module": openai})),
        "anthropic": (AnthropicChatModel, (log10, {"module": anthropic})),
        "litellm": (LitellmChatModel, (log10, {"module": openai})),
    }

    if llm_provider not in provider_map:
        raise ValueError("Invalid model provider.")

    model_class, log10_func_and_args = provider_map[llm_provider]
    log10_func, log10_args = log10_func_and_args
    log10_func(**log10_args)

    params["model"] = model
    return model_class(**params)


@pytest.fixture
def _magentic_model_obj(llm_provider, magentic_models, request):
    """
    This fixture is used to get the model object for the magentic tests.
    For openai:
        * When a test has marker for vision, the vision_model is used.
        * When a test does not have marker for vision, the chat_model is used.
    For anthropic:
        * When a test has marker for vision, the test is skipped because magentic does not support anthropic images.
        * When a test does not have marker for vision, the chat_model is used.
    """
    params = request.param.copy() if hasattr(request, "param") else {}
    is_vision = "vision" in request.keywords
    if llm_provider == "anthropic" and is_vision:
        pytest.skip("Skipping due to magentic not supported for anthropic vision models.")

    model_type = "vision_model" if is_vision else "chat_model"
    model = magentic_models.get(model_type, "")

    return _get_model_obj(llm_provider, model, params)


@pytest.mark.chat
def test_prompt(session, _magentic_model_obj):
    @prompt("Tell me a short joke", model=_magentic_model_obj)
    def llm() -> str: ...

    output = llm()
    assert isinstance(output, str)

    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.chat
@pytest.mark.stream
def test_prompt_stream(session, _magentic_model_obj):
    @prompt("Tell me a short joke", model=_magentic_model_obj)
    def llm() -> StreamedStr: ...

    response = llm()
    output = ""
    for chunk in response:
        output += chunk

    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.tools
def test_function_logging(session, _magentic_model_obj):
    def activate_oven(temperature: int, mode: Literal["broil", "bake", "roast"]) -> str:
        """Turn the oven on with the provided settings."""
        return f"Preheating to {temperature} F with mode {mode}"

    @prompt("Prepare the oven so I can make {food}", functions=[activate_oven], model=_magentic_model_obj)
    def configure_oven(food: str) -> FunctionCall[str]:  # ruff: ignore
        ...

    output = configure_oven("cookies!")
    function_args = format_magentic_function_args([output])
    _LogAssertion(completion_id=session.last_completion_id(), function_args=function_args).assert_tool_calls_response()


@pytest.mark.chat
@pytest.mark.async_client
@pytest.mark.stream
@pytest.mark.asyncio(scope="module")
async def test_async_stream_logging(session, _magentic_model_obj):
    @prompt("Tell me a 50-word story about {topic}", model=_magentic_model_obj)
    async def tell_story(topic: str) -> AsyncStreamedStr:  # ruff: ignore
        ...

    output = await tell_story("Europe.")
    result = ""
    async for chunk in output:
        result += chunk

    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), message_content=result).assert_chat_response()


@pytest.mark.async_client
@pytest.mark.tools
@pytest.mark.asyncio(scope="module")
async def test_async_parallel_stream_logging(session, _magentic_model_obj):
    def plus(a: int, b: int) -> int:
        return a + b

    async def minus(a: int, b: int) -> int:
        return a - b

    @prompt(
        "Sum {a} and {b}. Also subtract {a} from {b}.",
        functions=[plus, minus],
        model=_magentic_model_obj,
    )
    async def plus_and_minus(a: int, b: int) -> AsyncParallelFunctionCall[int]: ...

    result = []
    output = await plus_and_minus(2, 3)
    async for chunk in output:
        result.append(chunk)

    function_args = format_magentic_function_args(result)
    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), function_args=function_args).assert_tool_calls_response()


@pytest.mark.chat
@pytest.mark.async_client
@pytest.mark.stream
@pytest.mark.asyncio(scope="module")
async def test_async_multi_session_tags(_magentic_model_obj):
    @prompt("What is {a} * {b}?", model=_magentic_model_obj)
    async def do_math_with_llm_async(a: int, b: int) -> AsyncStreamedStr:  # ruff: ignore
        ...

    final_output = ""

    with log10_session(tags=["test_tag_a"]) as session:
        result = await do_math_with_llm_async(2, 2)
        output = ""
        async for chunk in result:
            output += chunk

        await finalize()
        _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()

    final_output += output
    with log10_session(tags=["test_tag_b"]) as session:
        output = ""
        result = await do_math_with_llm_async(2.5, 2.5)
        async for chunk in result:
            output += chunk

        await finalize()
        _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()

    final_output += output
    with log10_session(tags=["test_tag_c"]) as session:
        output = ""
        result = await do_math_with_llm_async(3, 3)
        async for chunk in result:
            output += chunk

        await finalize()
        _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.async_client
@pytest.mark.widget
@pytest.mark.asyncio(scope="module")
@pytest.mark.parametrize(
    "_magentic_model_obj", [{"temperature": 0.1, "max_tokens": 1000}], indirect=["_magentic_model_obj"]
)
async def test_async_widget(session, _magentic_model_obj):
    class WidgetInfo(BaseModel):
        title: str
        description: str

    @prompt(
        """
        Generate a descriptive title and short description for a widget, given the user's query and the data contained in the widget.

        Data: {widget_data}
        Query: {query}
        """,  # noqa: E501
        model=_magentic_model_obj,
    )
    async def _generate_title_and_description(query: str, widget_data: str) -> WidgetInfo: ...

    r = await _generate_title_and_description(query="Give me a summary of AAPL", widget_data="<the summary>")

    assert isinstance(r, WidgetInfo)
    assert isinstance(r.title, str)
    assert isinstance(r.description, str)
    assert r.title, "No title generated."
    assert r.description, "No description generated."

    arguments = {"title": r.title, "description": r.description}

    function_args = [{"name": "return_widgetinfo", "arguments": str(arguments)}]

    await finalize()
    _LogAssertion(completion_id=session.last_completion_id(), function_args=function_args).assert_tool_calls_response()


@pytest.mark.vision
def test_large_image_upload(session, _magentic_model_obj):
    # If large_image.png doesn't exist, download it from https://log10py-public.s3.us-east-2.amazonaws.com/large_image.png
    if not os.path.exists("./tests/large_image.png"):
        import requests

        # 10MB image from https://github.com/ckenst/images-catalog/blob/master/size/medium_size/aldrin-looks-back-at-tranquility-base_9457418581_o.jpg
        url = "https://raw.githubusercontent.com/ckenst/images-catalog/master/size/medium_size/aldrin-looks-back-at-tranquility-base_9457418581_o.jpg"
        response = requests.get(url)
        with open("./tests/large_image.png", "wb") as f:
            f.write(response.content)

    with open("./tests/large_image.png", "rb") as f:
        image_bytes = f.read()

    @chatprompt(
        SystemMessage("What's in the following screenshot?"),
        UserImageMessage(image_bytes),
        model=_magentic_model_obj,
    )
    def _llm() -> str: ...

    output = _llm()
    assert isinstance(output, str)
    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()
