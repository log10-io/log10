import click

from log10.feedback.feedback import create_feedback
from log10.feedback.feedback_task import create_feedback_task


@click.group()
def cli():
    pass


@click.group()
def feedback():
    pass


@click.group()
def feedback_task():
    pass


cli.add_command(feedback)
feedback.add_command(create_feedback, "create")
cli.add_command(feedback_task)
feedback_task.add_command(create_feedback_task, "create")

if __name__ == "__main__":
    cli()
