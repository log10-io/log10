import json

import click
from rich.console import Console
from rich.table import Table
from tqdm import tqdm

from log10.feedback.feedback import Feedback, _get_feedback_list, _get_feedback_list_graphql


@click.command()
@click.option("--task_id", prompt="Enter task id", help="Task ID")
@click.option("--values", prompt="Enter task values", help="Feedback in JSON format")
@click.option(
    "--completion_tags_selector",
    prompt="Enter completion tags selector",
    help="Completion tags selector",
)
@click.option("--comment", help="Comment", default="")
def create_feedback(task_id, values, completion_tags_selector, comment):
    """
    Add feedback to a group of completions associated with a task
    """
    click.echo("Creating feedback")
    tags = completion_tags_selector.split(",")
    values = json.loads(values)
    feedback = Feedback().create(task_id=task_id, values=values, completion_tags_selector=tags, comment=comment)
    click.echo(feedback.json())


@click.command()
@click.option(
    "--offset", default=0, type=int, help="The starting index from which to begin the feedback fetch. Defaults to 0."
)
@click.option(
    "--limit", default=25, type=int, help="The maximum number of feedback items to retrieve. Defaults to 25."
)
@click.option(
    "--task_id",
    default="",
    type=str,
    help="The specific Task ID to filter feedback. If not provided, feedback for all tasks will be fetched.",
)
@click.option(
    "--filter",
    default="",
    type=str,
    help="The filter applied to the feedback. If not provided, feedback will not be filtered. e.g. `log10 feedback list --filter 'Coverage <= 5'`.",
)
def list_feedback(offset, limit, task_id, filter):
    """
    List feedback based on the provided criteria. This command allows fetching feedback for a specific task or across all tasks,
    with control over the starting point and the number of items to retrieve.
    """
    feedback_data = (
        _get_feedback_list_graphql(task_id, filter, page=1, limit=limit)
        if filter
        else _get_feedback_list(offset, limit, task_id)
    )
    data_for_table = []
    for feedback in feedback_data:
        data_for_table.append(
            {
                "id": feedback["id"],
                "task_name": feedback["task_name"],
                "feedback": json.dumps(feedback["json_values"], ensure_ascii=False),
                "matched_completion_ids": ",".join(feedback["matched_completion_ids"]),
            }
        )
    table = Table(title="Feedback")
    table.add_column("ID")
    table.add_column("Task Name")
    table.add_column("Feedback")
    table.add_column("Completion ID")

    for item in data_for_table:
        table.add_row(item["id"], item["task_name"], item["feedback"], item["matched_completion_ids"])
    console = Console()
    console.print(table)
    console.print(f"Total feedback: {len(feedback_data)}")


@click.command()
@click.option("--id", required=True, help="Get feedback by ID")
def get_feedback(id):
    """
    Get feedback based on provided ID.
    """
    try:
        res = Feedback().get(id)
    except Exception as e:
        click.echo(f"Error fetching feedback {e}")
        if hasattr(e, "response") and hasattr(e.response, "json") and "error" in e.response.json():
            click.echo(e.response.json()["error"])
        return
    console = Console()
    feedback = json.dumps(res.json(), indent=4)
    console.print_json(feedback)


@click.command()
@click.option(
    "--offset",
    default=0,
    help="The starting index from which to begin the feedback fetch. Leave empty to start from the beginning.",
)
@click.option(
    "--limit", default="", help="The maximum number of feedback items to retrieve. Leave empty to retrieve all."
)
@click.option(
    "--task_id",
    default="",
    type=str,
    help="The specific Task ID to filter feedback. If not provided, feedback for all tasks will be fetched.",
)
@click.option(
    "--file",
    "-f",
    type=str,
    required=False,
    help="Path to the file where the feedback will be saved. The feedback data is saved in JSON Lines (jsonl) format. If not specified, feedback will be printed to stdout.",
)
def download_feedback(offset, limit, task_id, file):
    """
    Download feedback based on the provided criteria. This command allows fetching feedback for a specific task or across all tasks,
    with control over the starting point and the number of items to retrieve.
    """
    feedback_data = _get_feedback_list(offset, limit, task_id)

    console = Console()
    if not file:
        for feedback in feedback_data:
            console.print_json(json.dumps(feedback, indent=4))
        return

    with open(file, "w") as f:
        console.print(f"Saving feedback to {file}")
        for feedback in tqdm(feedback_data):
            f.write(json.dumps(feedback) + "\n")
