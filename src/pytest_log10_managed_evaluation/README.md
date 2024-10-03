# Pytest Log10 Managed Evaluation

A pytest plugin for managing evaluation in Log10 platform.

[TODO]: add link to the evaluation doc

## Installation
After [configuring the Log10 environment variables](https://docs.log10.io/observability/advanced/logging#configuration),
```bash
pip install 'log10-io[pytest]'
```

## Options

| Option | Type | Description |
|--------|------|-------------|
| `--eval-session-name` | Command-line | Set name for the evaluation session |
| `--local` | Command-line | Run pytest locally without showing the session in Log10. A JSON report file will be saved locally. |
| `--pretty-print` | Command-line | Pretty-print the JSON report with indentation. |
| `eval_session_name` | INI | Set name for the evaluation session. Set in `pytest.ini` or `setup.cfg`. |

## Usage

Once installed, the plugin is automatically enabled when you run pytest. Simply execute your tests as you normally would, e.g.:
```bash
pytest tests
```

This will run your tests and upload the results to the Log10 platform for managed evaluation.

### Running Tests Locally

If you prefer to run tests locally without uploading results to Log10, use the `--local` option:

```bash
pytest tests --local
```

When using the `--local` option, a JSON report will be generated and saved in the `.pytest_log10_eval_reports` folder in your project directory. This is useful for:

- Debugging and local development
- Reviewing test results before uploading to Log10
- Running tests in environments without Log10 access

### Customizing the Evaluation Session
This helps in organizing and identifying specific test runs in the Log10 platform.
To assign a custom name to your evaluation session, use the `--eval-session-name` option:

```bash
pytest tests --eval-session-name <your-test-session-name>
```

Use `eval_session_name` in INI file

You can set a default evaluation session name in your pytest configuration file. This will be used if the `--eval-session-name` command-line option is not provided.

Example in `pytest.ini`:

```ini
[pytest]
eval_session_name = <your-test-session-name>
```

### Pretty-Printing JSON Reports

For improved readability of local JSON reports, use the `--pretty-print` option:

```bash
pytest tests --local --pretty-print
```

This will format the JSON report with proper indentation, making it easier to read and analyze.


## Acknowledgments
This project is based on [pytest-json-report](https://github.com/numirias/pytest-json-report), licensed under the MIT License. We've modified and extended it to integrate with the Log10 platform and add additional features.