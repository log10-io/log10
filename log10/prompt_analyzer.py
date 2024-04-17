import json
import logging

import httpx
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from log10.llm import Log10Config


load_dotenv()

logging.basicConfig(
    format="[%(asctime)s - %(name)s - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger("LOG10")
logger.setLevel(logging.INFO)


class PromptAnalyzer:
    convert_url = "/api/experimental/autoprompt/convert"
    report_url = "/api/experimental/autoprompt/report"
    suggestions_url = "/api/experimental/autoprompt/suggestions"

    def __init__(self, log10_config: Log10Config = None):
        self._prompt_history: list[str] = []
        self._converted_prompt_history: list[dict] = []
        self._suggestions_history: list[dict] = []
        self._report_history: list[dict] = []

        self._log10_config = log10_config or Log10Config()
        self._http_client = httpx.Client()

        # Set by `_convert`.
        self.__session_id = None

    def _post_request(self, url: str, json_payload: dict) -> httpx.Response:
        headers = {"x-log10-token": self._log10_config.token, "Content-Type": "application/json"}
        json_payload["organization_id"] = self._log10_config.org_id
        try:
            timeout = httpx.Timeout(timeout=5, connect=5, read=5 * 60, write=5)
            res = self._http_client.post(
                self._log10_config.url + url, headers=headers, json=json_payload, timeout=timeout
            )
            res.raise_for_status()
            return res
        except Exception as e:
            logger.error(e)
            raise

    def _convert(self, prompt: str) -> dict:
        json_payload = {"prompt": prompt}

        # Pass session ID if it has already been set.
        if self.__session_id:
            json_payload["session_id"] = self.__session_id

        res = self._post_request(self.convert_url, json_payload)
        res_json = res.json()
        converted = res_json.get("output")

        # The convert API returns a session ID we can use to link together a session.
        if not self.__session_id:
            self.__session_id = res_json.get("session_id")

        return converted

    def _report(self, last_prompt: dict, current_prompt: dict, suggestions: dict) -> dict:
        json_payload = {
            "base_prompt": json.dumps(last_prompt),
            "new_prompt": json.dumps(current_prompt),
            "suggestions": json.dumps(suggestions),
            "session_id": self.__session_id,
        }
        res = self._post_request(self.report_url, json_payload)
        report = res.json().get("output")
        return report

    def _suggest(self, prompt_json: json, report: dict | None = None) -> dict:
        if report is None or report == {}:
            report = "[{}]"
        else:
            report = json.dumps(report)

        json_payload = {
            "base_prompt": json.dumps(prompt_json),
            "report": report,
            "session_id": self.__session_id,
        }
        res = self._post_request(self.suggestions_url, json_payload)
        suggestion = res.json().get("output")
        return suggestion

    def analyze(self, prompt: str) -> dict:
        """
        Analyze prompt and return suggestions. You can make multiple calls to this method by
        making changes to the prompt. This function keeps track of the prompt history and generate
        suggestions based on the prompt history.

        Example:
        >>> from log10.prompt_analyzer import PromptAnalyzer
        >>> analyzer = PromptAnalyzer()
        >>> prompt = "You are an assistant communicating with XYZ users on their support line."
        >>> suggestions = analyzer.analyze(prompt)
        >>> print(suggestions)
        """
        total_steps = 3 if self._suggestions_history else 2
        step = 0
        try:
            step += 1
            logger.info(f"[Step {step}/{total_steps}] Analyzing prompt...")

            self._prompt_history.append(prompt)
            converted_prompt = self._convert(prompt)
            self._converted_prompt_history.append(converted_prompt)

            logger.debug(f"converted prompt: {converted_prompt}")

            if self._suggestions_history:
                assert self._converted_prompt_history, "Prompt history is empty."
                assert self._suggestions_history, "Suggestions history is empty."

                step += 1
                logger.info(f"[Step {step}/{total_steps}] Generating report...")

                last_converted_prompt = self._converted_prompt_history[-1]
                last_suggestions = self._suggestions_history[-1]
                report_dict = self._report(last_converted_prompt, converted_prompt, last_suggestions)
                self._report_history.append(report_dict)

                logger.debug(f"report: {report_dict}")

            step += 1
            logger.info(f"[Step {step}/{total_steps}] Generating suggestions...")

            last_report = self._report_history[-1] if self._report_history else {}
            suggestions_dict = self._suggest(converted_prompt, last_report)
            self._suggestions_history.append(suggestions_dict)

            logger.debug(f"suggestions: {suggestions_dict}")
            logger.info("Done analyzing.")

            return suggestions_dict
        except Exception as e:
            logger.error(e)


def convert_suggestion_to_markdown(suggestion):
    markdown_text = ""

    markdown_text += "| Category | Recommendation |\n"
    markdown_text += "| --- | --- |\n"
    for category, contents in suggestion.items():
        for subcategory, details in contents.items():
            color = details["color"]  # Assuming 'color' is always provided
            recommendation = details["recommendation"]

            # Using HTML to colorize the subcategory title if 'color' is specified
            colored_subcategory = (
                f'<span style="color:{color};">{subcategory}</span> <br> <span style="color:{color};"></span>'
            )

            # Add each subcategory and its recommendation to the table
            markdown_text += f"| **{colored_subcategory}** | {recommendation} |\n"

        # markdown_text += "\n"  # Add a newline for spacing before the next section

    return markdown_text


def display_prompt_analyzer_suggestions(data, title=""):
    console = Console()
    console.print(f"[bold magenta]{title}[/bold magenta]")
    for key, value in data.items():
        for sub_key, sub_value in value.items():
            text = Text(justify="left")
            text.append(f"Recommendation: {sub_value['recommendation']}", style="white")
            console.print(
                Panel(
                    text, title=f"[bold {sub_value['color']}]{sub_key}[/]", border_style=f"bold {sub_value['color']}"
                )
            )
