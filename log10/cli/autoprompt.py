import json
from pathlib import Path

import click

from log10.prompt_analyzer import PromptAnalyzer, display_prompt_analyzer_suggestions


# ignor "tool" and "funciton" roles
ALLOWED_ROLES = {"system", "user", "assistant"}


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
        if not prompt:
            raise click.BadParameter("No prompt provided.")

    # check if prompt is a file path
    prompt_file = Path(prompt)
    if prompt_file.exists():
        with open(prompt_file, "r") as f:
            click.echo(f"Prompt loaded from {prompt_file}:")
            prompt = f.read()

    # try to parse the prompt as a json
    try:
        prompt_json = json.loads(prompt)

        if isinstance(prompt_json, list) and all("role" in item and "content" in item for item in prompt_json):
            # prompt is a list of messages
            prompt = "\n\n".join([f"{m["role"]}: {m["content"]}" for m in prompt_json if m["role"] in ALLOWED_ROLES])
        elif isinstance(prompt_json, dict) and "request" in prompt_json and "messages" in prompt_json["request"]:
            # prompt is a log10 completion
            prompt = "\n\n".join(
                [
                    f"{m["role"]}: {m["content"]}"
                    for m in prompt_json["request"]["messages"]
                    if m["role"] in ALLOWED_ROLES
                ]
            )
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

    click.echo(prompt)
    analyzer = PromptAnalyzer()
    suggestions = analyzer.analyze(prompt)
    display_prompt_analyzer_suggestions(suggestions)
