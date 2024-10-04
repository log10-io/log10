# Pytest Log10 Managed Evaluation

A pytest plugin for managing evaluation in Log10 platform.

## Installation
After [configuring the Log10 environment variables](https://docs.log10.io/observability/advanced/logging#configuration),
```bash
pip install log10-io
```

## Options

| Option | Type | Description |
|--------|------|-------------|
| `--log10` | Command-line | Enable Log10 managed evaluation reporting |
| `--eval-session-name` | Command-line | Set name for the evaluation session |
| `--local` | Command-line | Run pytest locally without showing the session in Log10. A JSON report file will be saved locally. |
| `--pretty-print` | Command-line | Pretty-print the JSON report with indentation. |
| `log10` | INI | Enable Log10 managed evaluation reporting. Set in `pytest.ini` or `setup.cfg`. |
| `eval_session_name` | INI | Set name for the evaluation session. Set in `pytest.ini` or `setup.cfg`. |

## Usage

To enable the Log10 managed evaluation reporting, you need to use the `--log10` option or set `log10 = true` in your pytest configuration file. Once enabled, execute your tests as you normally would:

```bash
pytest tests --log10
```

This will run your tests and upload the results to the Log10 platform for managed evaluation.

### Enabling Log10 Reporting in Configuration

You can enable Log10 reporting by default in your pytest configuration file:

Example in `pytest.ini`:

```ini
[pytest]
log10 = true
```

### Running Tests Locally

If you prefer to run tests locally without uploading results to Log10, use the `--local` option:

```bash
pytest tests --log10 --local
```

When using the `--local` option, a JSON report will be generated and saved in the `.pytest_log10_eval_reports` folder in your project directory. This is useful for:

- Debugging and local development
- Reviewing test results before uploading to Log10
- Running tests in environments without Log10 access

### Customizing the Evaluation Session
This helps in organizing and identifying specific test runs in the Log10 platform.
To assign a custom name to your evaluation session, use the `--eval-session-name` option:

```bash
pytest tests --log10 --eval-session-name <your-test-session-name>
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
pytest tests --log10 --local --pretty-print
```

This will format the JSON report with proper indentation, making it easier to read and analyze.


## Acknowledgments
This project is based on [pytest-json-report](https://github.com/numirias/pytest-json-report), licensed under the MIT License. We've modified and extended it to integrate with the Log10 platform and add additional features.