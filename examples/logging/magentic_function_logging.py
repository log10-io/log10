# taken from Magentic README
# https://github.com/jackmpcollins/magentic/blob/2493419f2db3a3be58fb308d7df51a51bf1989c1/README.md#usage

from typing import Literal

import openai
from magentic import FunctionCall, prompt

from log10.load import global_tags, log10


log10(openai)
global_tags = ["magentic", "function", "example"]  # noqa: F811


def activate_oven(temperature: int, mode: Literal["broil", "bake", "roast"]) -> str:
    """Turn the oven on with the provided settings."""
    return f"Preheating to {temperature} F with mode {mode}"


@prompt(
    "Prepare the oven so I can make {food}",
    functions=[activate_oven],
)
def configure_oven(food: str) -> FunctionCall[str]:
    ...


output = configure_oven("cookies!")
# FunctionCall(<function activate_oven at 0x1105a6200>, temperature=350, mode='bake')
print(output())
# 'Preheating to 350 F with mode bake'
