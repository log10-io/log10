import asyncio
from typing import Literal

import openai
import pytest
from magentic import AsyncParallelFunctionCall, AsyncStreamedStr, FunctionCall, OpenaiChatModel, StreamedStr, prompt
from pydantic import BaseModel

from log10.load import log10, log10_session


log10(openai)


@pytest.mark.chat
def test_prompt():
    @prompt("Tell me a short joke")
    def llm() -> str: ...

    output = llm()
    assert isinstance(output, str)
    assert output, "No output from the model."

@pytest.mark.chat
@pytest.mark.stream
def test_prompt_stream():
    @prompt("Tell me a short joke")
    def llm() -> StreamedStr: ...

    response = llm()
    output = ""
    for chunk in response:
        output += chunk

    assert output, "No output from the model."


@pytest.mark.tools
def test_function_logging():
    def activate_oven(temperature: int, mode: Literal["broil", "bake", "roast"]) -> str:
        """Turn the oven on with the provided settings."""
        return f"Preheating to {temperature} F with mode {mode}"

    @prompt(
        "Prepare the oven so I can make {food}",
        functions=[activate_oven],
    )
    def configure_oven(food: str) -> FunctionCall[str]:  # ruff: ignore
        ...

    output = configure_oven("cookies!")
    assert output(), "No output from the model."

@pytest.mark.async_client
@pytest.mark.stream
def test_async_stream_logging():
    @prompt("Tell me a 50-word story about {topic}")
    async def tell_story(topic: str) -> AsyncStreamedStr:  # ruff: ignore
        ...

    async def main():
        with log10_session(tags=["async_tag"]):
            output = await tell_story("Europe.")
            result = ""
            async for chunk in output:
                result += chunk

            return result

    output = asyncio.run(main())
    assert output, "No output from the model."


@pytest.mark.async_client
@pytest.mark.tools
def test_async_parallel_stream_logging():
    def plus(a: int, b: int) -> int:
        return a + b

    async def minus(a: int, b: int) -> int:
        return a - b

    @prompt("Sum {a} and {b}. Also subtract {a} from {b}.", functions=[plus, minus])
    async def plus_and_minus(a: int, b: int) -> AsyncParallelFunctionCall[int]: ...

    async def main():
        output = await plus_and_minus(2, 3)
        async for chunk in output:
            assert isinstance(chunk, FunctionCall), "chunk is not an instance of FunctionCall"

    asyncio.run(main())

@pytest.mark.async_client
@pytest.mark.stream
def test_async_multi_session_tags():
    @prompt("What is {a} * {b}?", model=OpenaiChatModel(model="gpt-4-turbo-preview"))
    async def do_math_with_llm_async(a: int, b: int) -> AsyncStreamedStr:  # ruff: ignore
        ...

    async def main():
        output = ""

        with log10_session(tags=["test_tag_a"]):
            result = await do_math_with_llm_async(2, 2)
            async for chunk in result:
                output += chunk

        result = await do_math_with_llm_async(2.5, 2.5)
        async for chunk in result:
            output += chunk

        with log10_session(tags=["test_tag_b"]):
            result = await do_math_with_llm_async(3, 3)
            async for chunk in result:
                output += chunk
        return output

    output = asyncio.run(main())
    assert output, "No output from the model."
    assert "4" in output
    assert "6.25" in output
    assert "9" in output


@pytest.mark.async_client
@pytest.mark.widget
def test_async_widget():
    class WidgetInfo(BaseModel):
        title: str
        description: str

    @prompt(
        """
        Generate a descriptive title and short description for a widget, given the user's query and the data contained in the widget.

        Data: {widget_data}
        Query: {query}
        """,  # noqa: E501
        model=OpenaiChatModel("gpt-4-turbo", temperature=0.1, max_tokens=1000),
    )
    async def _generate_title_and_description(query: str, widget_data: str) -> WidgetInfo: ...

    async def main():
        r = await _generate_title_and_description(query="Give me a summary of AAPL", widget_data="<the summary>")

        assert isinstance(r, WidgetInfo)
        assert isinstance(r.title, str)
        assert "AAPL" in r.title
        assert isinstance(r.description, str)

    asyncio.run(main())
