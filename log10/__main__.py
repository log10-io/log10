import click
from log10.completions.completions import list_completions

from log10.feedback.feedback import create_feedback
from log10.feedback.feedback_task import create_feedback_task


@click.group()
def cli():
    pass


@click.group()
def completions():
    """
    Manage logs from completions i.e. logs from users
    """
    pass


@click.group()
def feedback():
    """
    Manage feedback for completions i.e. capturing feedback from users
    """
    pass


@click.group()
def feedback_task():
    """
    Manage tasks for feedback i.e. instructions and schema for feedback
    """
    pass


cli.add_command(completions)
completions.add_command(list_completions, "list")

cli.add_command(feedback)
feedback.add_command(create_feedback, "create")
cli.add_command(feedback_task)
feedback_task.add_command(create_feedback_task, "create")

if __name__ == "__main__":
    cli()
