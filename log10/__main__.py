import click

from log10.completions.completions import download_completions, get_completion, list_completions
from log10.feedback.autofeedback import auto_feedback_icl
from log10.feedback.feedback import create_feedback, download_feedback, get_feedback, list_feedback
from log10.feedback.feedback_task import create_feedback_task, get_feedback_task, list_feedback_task


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
completions.add_command(get_completion, "get")
completions.add_command(download_completions, "download")

cli.add_command(feedback)
feedback.add_command(create_feedback, "create")
feedback.add_command(list_feedback, "list")
feedback.add_command(get_feedback, "get")
feedback.add_command(download_feedback, "download")
feedback.add_command(auto_feedback_icl, "predict")

cli.add_command(feedback_task)
feedback_task.add_command(create_feedback_task, "create")
feedback_task.add_command(list_feedback_task, "list")
feedback_task.add_command(get_feedback_task, "get")

if __name__ == "__main__":
    cli()
