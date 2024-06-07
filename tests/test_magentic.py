from typing import Literal

import openai
import pytest
from magentic import AsyncParallelFunctionCall, AsyncStreamedStr, FunctionCall, OpenaiChatModel, StreamedStr, prompt
from pydantic import BaseModel

from log10.load import log10, log10_session
from tests.utils import _LogAssertion, format_magentic_function_args


log10(openai)


@pytest.mark.chat
def test_prompt(session, magentic_model):
    @prompt("Tell me a short joke", model=OpenaiChatModel(model=magentic_model))
    def llm() -> str: ...

    output = llm()
    assert isinstance(output, str)
    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.chat
@pytest.mark.stream
def test_prompt_stream(session, magentic_model):
    @prompt("Tell me a short joke", model=OpenaiChatModel(model=magentic_model))
    def llm() -> StreamedStr: ...

    response = llm()
    output = ""
    for chunk in response:
        output += chunk

    _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.tools
def test_function_logging(session, magentic_model):
    def activate_oven(temperature: int, mode: Literal["broil", "bake", "roast"]) -> str:
        """Turn the oven on with the provided settings."""
        return f"Preheating to {temperature} F with mode {mode}"

    @prompt(
        "Prepare the oven so I can make {food}", functions=[activate_oven], model=OpenaiChatModel(model=magentic_model)
    )
    def configure_oven(food: str) -> FunctionCall[str]:  # ruff: ignore
        ...

    output = configure_oven("cookies!")
    function_args = format_magentic_function_args([output])
    _LogAssertion(completion_id=session.last_completion_id(), function_args=function_args).assert_tool_calls_response()


@pytest.mark.async_client
@pytest.mark.stream
@pytest.mark.asyncio
async def test_async_stream_logging(session, magentic_model):
    @prompt("Tell me a 50-word story about {topic}", model=OpenaiChatModel(model=magentic_model))
    async def tell_story(topic: str) -> AsyncStreamedStr:  # ruff: ignore
        ...

    output = await tell_story("Europe.")
    result = ""
    async for chunk in output:
        result += chunk

    _LogAssertion(completion_id=session.last_completion_id(), message_content=result).assert_chat_response()


@pytest.mark.async_client
@pytest.mark.tools
@pytest.mark.asyncio
async def test_async_parallel_stream_logging(session, magentic_model):
    def plus(a: int, b: int) -> int:
        return a + b

    async def minus(a: int, b: int) -> int:
        return a - b

    @prompt(
        "Sum {a} and {b}. Also subtract {a} from {b}.",
        functions=[plus, minus],
        model=OpenaiChatModel(model=magentic_model),
    )
    async def plus_and_minus(a: int, b: int) -> AsyncParallelFunctionCall[int]: ...

    result = []
    output = await plus_and_minus(2, 3)
    async for chunk in output:
        result.append(chunk)

    function_args = format_magentic_function_args(result)
    _LogAssertion(completion_id=session.last_completion_id(), function_args=function_args).assert_tool_calls_response()


@pytest.mark.async_client
@pytest.mark.stream
@pytest.mark.asyncio
async def test_async_multi_session_tags(magentic_model):
    @prompt("What is {a} * {b}?", model=OpenaiChatModel(model=magentic_model))
    async def do_math_with_llm_async(a: int, b: int) -> AsyncStreamedStr:  # ruff: ignore
        ...

    final_output = ""

    with log10_session(tags=["test_tag_a"]) as session:
        result = await do_math_with_llm_async(2, 2)
        output = ""
        async for chunk in result:
            output += chunk

        _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()

    final_output += output
    with log10_session(tags=["test_tag_b"]) as session:
        output = ""
        result = await do_math_with_llm_async(2.5, 2.5)
        async for chunk in result:
            output += chunk

        _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()

    final_output += output
    with log10_session(tags=["test_tag_c"]) as session:
        output = ""
        result = await do_math_with_llm_async(3, 3)
        async for chunk in result:
            output += chunk

        _LogAssertion(completion_id=session.last_completion_id(), message_content=output).assert_chat_response()


@pytest.mark.async_client
@pytest.mark.widget
@pytest.mark.asyncio
async def test_async_widget(session, magentic_model):
    class WidgetInfo(BaseModel):
        title: str
        description: str

    @prompt(
        """
        Generate a descriptive title and short description for a widget, given the user's query and the data contained in the widget.

        Data: {widget_data}
        Query: {query}
        """,  # noqa: E501
        model=OpenaiChatModel(magentic_model, temperature=0.1, max_tokens=1000),
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
    _LogAssertion(completion_id=session.last_completion_id(), function_args=function_args).assert_tool_calls_response()
