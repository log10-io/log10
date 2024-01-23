import json
import logging

import httpx
from dotenv import load_dotenv

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
        res = self._post_request(self.convert_url, {"prompt": prompt})
        converted = res.json()
        return converted

    def _report(self, last_prompt: dict, current_prompt: dict, suggestions: dict) -> dict:
        json_payload = {
            "base_prompt": json.dumps(last_prompt),
            "new_prompt": json.dumps(current_prompt),
            "suggestions": json.dumps(suggestions),
        }
        res = self._post_request(self.report_url, json_payload)
        report = res.json()
        return report

    def _suggest(self, prompt_json: json, report: dict | None = None) -> dict:
        if report is None or report == {}:
            report = "[{}]"
        else:
            report = json.dumps(report)

        json_payload = {
            "base_prompt": prompt_json,
            "report": report,
        }
        res = self._post_request(self.suggestions_url, json_payload)
        suggestion = res.json()
        return suggestion

    def analyze(self, prompt: str) -> dict:
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

            return suggestions_dict
        except Exception as e:
            logger.error(e)
