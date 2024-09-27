import json

import click
from rich.console import Console
from rich.table import Table

from log10._httpx_utils import _get_time_diff
from log10.feedback.feedback_task import FeedbackTask


# create a cli interface for FeebackTask.create function
@click.command()
@click.option("--name", prompt="Enter feedback task name", help="Name of the task")
@click.option("--task_schema", prompt="Enter feedback task schema", help="Task schema")
@click.option("--instruction", help="Task instruction", default="")
@click.option(
    "--completion_tags_selector",
    help="Completion tags selector",
)
def create_feedback_task(name, task_schema, instruction, completion_tags_selector=None):
    click.echo("Creating feedback task")
    tags = []

    if completion_tags_selector:
        tags = completion_tags_selector.split(",")

    task_schema = json.loads(task_schema)
    task = FeedbackTask().create(
        name=name, task_schema=task_schema, completion_tags_selector=tags, instruction=instruction
    )
    click.echo(f"Use this task_id to add feedback: {task.json()['id']}")


@click.command()
@click.option("--limit", default=25, help="Number of feedback tasks to fetch")
@click.option("--offset", default=0, help="Offset for the feedback tasks")
def list_feedback_task(limit, offset):
    res = FeedbackTask().list(limit=limit, offset=offset)
    feedback_tasks = res.json()

    data_for_table = []

    for task in feedback_tasks["data"]:
        data_for_table.append(
            {
                "id": task["id"],
                "created_at": _get_time_diff(task["created_at"]),
                "name": task["name"],
                "required": task["json_schema"]["required"],
                "instruction": task["instruction"],
            }
        )

    table = Table(title="Feedback Tasks")
    table.add_column("ID", style="dim")
    table.add_column("Created At")
    table.add_column("Name")
    table.add_column("Required")
    table.add_column("Instruction")
    for item in data_for_table:
        required = ", ".join(item["required"]) if item["required"] else ""
        table.add_row(item["id"], item["created_at"], item["name"], required, item["instruction"])

    console = Console()
    console.print(table)


@click.command()
@click.option("--id", help="Get feedback task by ID")
def get_feedback_task(id):
    try:
        res = FeedbackTask().get(id)
    except Exception as e:
        click.echo(f"Error fetching feedback task {e}")
        if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
            click.echo(e.response.json()["error"])
        return
    task = json.dumps(res.json())
    console = Console()
    console.print_json(task)
