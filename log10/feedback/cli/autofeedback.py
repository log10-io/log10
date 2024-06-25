import json

import click
import rich
from rich.console import Console

from log10.feedback.autofeedback import AutoFeedbackICL, get_autofeedback


@click.command()
@click.option("--task_id", help="Feedback task ID")
@click.option("--content", help="Completion content")
@click.option("--file", "-f", help="File containing completion content")
@click.option("--completion_id", help="Completion ID")
@click.option("--num_samples", default=5, help="Number of samples to use for few-shot learning")
def auto_feedback_icl(task_id: str, content: str, file: str, completion_id: str, num_samples: int):
    """
    Generate feedback with existing human feedback based on in context learning
    """
    options_count = sum([1 for option in [content, file, completion_id] if option])
    if options_count > 1:
        click.echo("Only one of --content, --file, or --completion_id should be provided.")
        return

    console = Console()
    auto_feedback_icl = AutoFeedbackICL(task_id, num_samples=num_samples)
    if completion_id:
        results = auto_feedback_icl.predict(completion_id=completion_id)
        console.print_json(results)
        return

    if file:
        with open(file, "r") as f:
            content = f.read()
    results = auto_feedback_icl.predict(text=content)
    console.print_json(results)


@click.command()
@click.option("--completion-id", required=True, help="Completion ID")
def get_autofeedback_cli(completion_id: str):
    """
    Get an auto feedback by completion id
    """
    res = get_autofeedback(completion_id)
    if res:
        rich.print_json(json.dumps(res["data"], indent=4))
