import json
from pathlib import Path

import click

from log10.prompt_analyzer import PromptAnalyzer, display_prompt_analyzer_suggestions


# ignore "tool" and "funciton" roles
ALLOWED_ROLES = {"system", "user", "assistant"}


def _parse_messages_to_single_prompt(messages: list) -> str:
    """
    Parse a list of messages to a single prompt string.
    """
    return "\n\n".join(
        [
            f'{m.get("role")}: {m.get("content")}'
            for m in messages
            if m.get("role") in ALLOWED_ROLES and m.get("content")
        ]
    )


@click.command()
@click.option(
    "--prompt",
    "-p",
    help=(
        "The prompt to analyze. Provide a string or a file containing the prompt. "
        "We allow three formats:\n"
        '1) string prompt, e.g. "Summarize this article in 3 sentences."\n'
        '2) messages, e.g. [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]\n'
        '3) log10 completion, e.g. {..., "request": {..., "messages": [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}], ...}, "response": {...}}\n'
    ),
)
def autoprompt(prompt):
    """
    Analyze a prompt or messages and provide suggestions on how to improve it.
    """
    if not prompt:
        click.echo("Enter the prompt to analyze (end with Ctrl+D):")
        prompt = click.get_text_stream("stdin").read()

    # check if prompt is a file path
    prompt_file = Path(prompt)
    if prompt_file.exists():
        with open(prompt_file, "r") as f:
            click.echo(f"Prompt loaded from {prompt_file}:")
            prompt = f.read()

    if not prompt:
        raise click.BadParameter("No prompt provided.")

    # try to parse the prompt as a json
    try:
        prompt_json = json.loads(prompt)

        if isinstance(prompt_json, list) and all("role" in item and "content" in item for item in prompt_json):
            # prompt is a list of messages
            messages = [m for m in prompt_json if m["role"] in ALLOWED_ROLES]
            prompt = _parse_messages_to_single_prompt(messages)
        elif isinstance(prompt_json, dict) and "messages" in prompt_json.get("request", {}):
            # prompt is a log10 completion
            messages = [m for m in prompt_json["request"]["messages"] if m["role"] in ALLOWED_ROLES]
            prompt = _parse_messages_to_single_prompt(messages)
        elif isinstance(prompt_json, str):
            # prompt is a plain string
            prompt = prompt_json
        else:
            raise click.BadParameter(
                "Unsupported JSON format. Please provide a list of messages or a log10 completion."
            )
    except json.JSONDecodeError:
        # Input is a plain string
        prompt = prompt

    if not prompt:
        raise click.RuntimeError(
            "The prompt is empty after parsing the messages. Please provide messages with roles {ALLOWED_ROLES} and non-empty content."
        )

    click.echo(prompt)
    analyzer = PromptAnalyzer()
    suggestions = analyzer.analyze(prompt)
    display_prompt_analyzer_suggestions(suggestions)
