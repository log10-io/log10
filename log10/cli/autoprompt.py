import json
from pathlib import Path

import click

from log10.prompt_analyzer import PromptAnalyzer, display_prompt_analyzer_suggestions


@click.command()
@click.option("--prompt", "-p", help="The prompt to analyze. Provide a string or a file containing the prompt.")
@click.option(
    "--messages", "-m", help="The messages to analyze. Provide a JSON or JSON file of openai style messages."
)
def autoprompt(prompt, messages):
    """
    Analyze a prompt or messages and provide suggestions on how to improve it.
    """
    if prompt and messages:
        raise click.UsageError("You can only provide either a prompt or messages, not both.")
    if not prompt and not messages:
        click.echo("Enter the prompt to analyze (end with Ctrl+D):")
        prompt = click.get_text_stream("stdin").read()
        # prompt = click.prompt("Enter the prompt to analyze", type=str)

    # prompt could be a string or a file path, if it's a file path, read the file load into a string
    if prompt:
        prompt_file = Path(prompt)
        if prompt_file.exists():
            with open(prompt_file, "r") as f:
                prompt = f.read()
                click.echo(f"Prompt loaded from {prompt_file}:")
    elif messages:
        messages_file = Path(messages)
        if messages_file.exists():
            # check message_file extension is json
            if messages_file.suffix.lower() != ".json":
                raise click.UsageError("Only .json extension is supported for the messages file.")
            with open(messages_file, "r") as f:
                # load messages_file to json, then extract the content of each message
                messages = f.read()

            try:
                messages = json.loads(messages)
            except json.JSONDecodeError:
                raise click.UsageError("Invalid JSON format for messages file.")
            click.echo(f"Messages loaded from {messages_file}:")
        prompt = "\n\n".join([m.get("content", "") for m in messages])

    click.echo(prompt)
    analyzer = PromptAnalyzer()
    suggestions = analyzer.analyze(prompt)
    display_prompt_analyzer_suggestions(suggestions)
