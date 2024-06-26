import pytest
from click.testing import CliRunner

from log10.cli.cli_commands import cli


completion_id = "fe3c10f0-df31-4a42-b224-233adfe1eb7f"
feedback_id = "58b8d9b7-1d6a-4b7d-952e-bc97a649dc94"
feedback_task_id = "890bda39-2232-4cde-ba95-7c501afc4b95"


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
