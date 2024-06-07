import asyncio

import openai
import rich
from magentic import OpenaiChatModel, prompt
from pydantic import BaseModel

from log10._httpx_utils import finalize
from log10.load import log10


log10(openai)


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
    rich.print(r)
    await finalize()


asyncio.run(main())
