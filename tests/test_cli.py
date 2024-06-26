import pytest
from click.testing import CliRunner

from log10.cli.cli_commands import cli


completion_id = "fb891d4e-f99c-4d8d-a95c-24d2ed7a0807"
feedback_id = "0e43b537-5f0c-4f47-ba83-4938514477c3"
feedback_task_id = "1c84079e-a7bb-47e1-86c7-e32b51045e8e"


@pytest.fixture
def runner():
    return CliRunner()


def test_list_completions(runner):
    result = runner.invoke(cli, ["completions", "list"])
    print(result.output)
    assert result.exit_code == 0
    assert "total_completions=" in result.output


def test_get_completion(runner):
    result = runner.invoke(cli, ["completions", "get", "--id", completion_id])
    assert result.exit_code == 0
    assert completion_id in result.output


def test_download_completions(runner):
    result = runner.invoke(cli, ["completions", "download", "--limit", "1", "--tags", "log10/summary-grading"])
    assert result.exit_code == 0
    assert "Download total completions: 1/" in result.output


def test_list_feedback(runner):
    result = runner.invoke(cli, ["feedback", "list"])
    assert result.exit_code == 0
    assert "Total feedback:" in result.output


def test_get_feedback(runner):
    result = runner.invoke(cli, ["feedback", "get", "--id", feedback_id])
    assert result.exit_code == 0
    assert feedback_id in result.output


def test_download_feedback(runner):
    result = runner.invoke(cli, ["feedback", "download", "--limit", "1"])
    assert result.exit_code == 0


def test_get_autofeedback(runner):
    result = runner.invoke(cli, ["feedback", "autofeedback", "get", "--completion-id", completion_id])
    assert result.exit_code == 0
    assert completion_id in result.output


def test_list_feedback_task(runner):
    result = runner.invoke(cli, ["feedback-task", "list"])
    assert result.exit_code == 0


def test_get_feedback_task(runner):
    result = runner.invoke(cli, ["feedback-task", "get", "--id", feedback_task_id])
    assert result.exit_code == 0
