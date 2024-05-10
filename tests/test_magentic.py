import asyncio
from pydantic import BaseModel
import pytest

import openai
from typing import Literal

from magentic import AsyncParallelFunctionCall, AsyncStreamedStr, OpenaiChatModel, prompt, FunctionCall, StreamedStr
from log10.load import log10, log10_session

log10(openai)


@pytest.mark.chat
def test_prompt():
    @prompt("Tell me a short joke")
    def llm() -> str: ...

    output = llm()
    assert isinstance(output, str)


@pytest.mark.chat
@pytest.mark.stream
def test_prompt_stream(capfd):
    @prompt("Tell me a short joke")
    def llm() -> StreamedStr: ...

    response = llm()
    for chunk in response:
        print(chunk, end="", flush=True)

    out, err = capfd.readouterr()
    assert err == ""
    assert isinstance(out, str)


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
    assert isinstance(output(), str)


@pytest.mark.async_client
@pytest.mark.stream
def test_async_stream_logging(capfd):
    @prompt("Tell me a 50-word story about {topic}")
    async def tell_story(topic: str) -> AsyncStreamedStr:  # ruff: ignore
        ...

    async def main():
        with log10_session(tags=["async_tag"]):
            output = await tell_story("Europe.")
            async for chunk in output:
                print(chunk, end="", flush=True)

    asyncio.run(main())

    out, err = capfd.readouterr()
    assert err == ""
    assert isinstance(out, str)


@pytest.mark.async_client
@pytest.mark.tools
def test_async_parallel_stream_logging(capfd):
    def plus(a: int, b: int) -> int:
        return a + b

    async def minus(a: int, b: int) -> int:
        return a - b

    @prompt("Sum {a} and {b}. Also subtract {a} from {b}.", functions=[plus, minus])
    async def plus_and_minus(a: int, b: int) -> AsyncParallelFunctionCall[int]: ...

    async def main():
        output = await plus_and_minus(2, 3)
        async for chunk in output:
            print(chunk)

    asyncio.run(main())

    out, err = capfd.readouterr()
    assert err == ""
    assert isinstance(out, str)


@pytest.mark.async_client
@pytest.mark.stream
def test_async_multi_session_tags(capfd):
    @prompt("What is {a} * {b}?", model=OpenaiChatModel(model="gpt-4-turbo-preview"))
    async def do_math_with_llm_async(a: int, b: int) -> AsyncStreamedStr:  # ruff: ignore
        ...

    async def main():
        with log10_session(tags=["test_tag_a"]):
            result = await do_math_with_llm_async(2, 2)
            async for chunk in result:
                print(chunk, end="", flush=True)

        result = await do_math_with_llm_async(2.5, 2.5)
        async for chunk in result:
            print(chunk, end="", flush=True)

        with log10_session(tags=["test_tag_b"]):
            result = await do_math_with_llm_async(3, 3)
            async for chunk in result:
                print(chunk, end="", flush=True)

    asyncio.run(main())
    out, err = capfd.readouterr()
    assert err == ""
    assert isinstance(out, str)
    assert "4" in out
    assert "6.25" in out
    assert "9" in out


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
