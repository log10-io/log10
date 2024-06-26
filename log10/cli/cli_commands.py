try:
    import click
    import pandas  # noqa: F401
    import rich  # noqa: F401
    import tabulate  # noqa: F401
except ImportError:
    print(
        "To use log10 cli you must install optional modules. Please install them with `pip install 'log10-io[cli]'`."
    )
    exit(1)

from log10.cli.autofeedback import auto_feedback_icl, get_autofeedback_cli
from log10.cli.completions import benchmark_models, download_completions, get_completion, list_completions
from log10.cli.feedback import create_feedback, download_feedback, get_feedback, list_feedback
from log10.cli.feedback_task import create_feedback_task, get_feedback_task, list_feedback_task


@click.group()
def cli():
    pass


@click.group()
def completions():
    """
    Manage logs from completions i.e. logs from users
    """
    pass


@click.group(name="feedback")
def feedback():
    """
    Manage feedback for completions i.e. capturing feedback from users
    """
    pass


@click.group(name="auto_feedback")
def auto_feedback():
    """
    Manage auto feedback for completions i.e. capturing feedback from users
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
completions.add_command(benchmark_models, "benchmark_models")

cli.add_command(feedback)
feedback.add_command(create_feedback, "create")
feedback.add_command(list_feedback, "list")
feedback.add_command(get_feedback, "get")
feedback.add_command(download_feedback, "download")
feedback.add_command(auto_feedback_icl, "predict")
feedback.add_command(auto_feedback, "autofeedback")
# Subcommands for auto_feedback under feedback command
auto_feedback.add_command(get_autofeedback_cli, "get")

cli.add_command(feedback_task)
feedback_task.add_command(create_feedback_task, "create")
feedback_task.add_command(list_feedback_task, "list")
feedback_task.add_command(get_feedback_task, "get")
