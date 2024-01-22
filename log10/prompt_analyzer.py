import json
import logging
import os

import httpx
from dotenv import load_dotenv

from log10.llm import Log10Config


load_dotenv()

logging.basicConfig(
    format="[%(asctime)s - %(name)s - %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger: logging.Logger = logging.getLogger("LOG10")

convert_url = "/api/experimental/autoprompt/convert"
report_url = "/api/experimental/autoprompt/report"
suggestions_url = "/api/experimental/autoprompt/suggestions"

class PromptAnalyzer:
    def __init__(self, log10_config: Log10Config = None):
        self._prompts: list[str] = []
        self._suggestions: dict = None
        self._reports: dict = None
        self._log10_config = log10_config or Log10Config()
        self._http_client = httpx.Client()
        self._timeout = httpx.Timeout(timeout=5, connect=5, read=5 * 60, write=5)
        self._loading_analysis = False

    def _post_request(self, url: str, json_payload: dict) -> httpx.Response:
        headers = { "x-log10-token": self._log10_config.token, "Content-Type": "application/json"}
        json_payload["organization_id"] = self._log10_config.org_id

        res = self._http_client.post( self._log10_config.url + url, headers=headers, json=json_payload, timeout=self._timeout)
        return res

    def _convert(self, prompt: str) -> json:
        res = self._post_request(convert_url, {"prompt": prompt})
        converted = res.json()
        return converted

    def _report(self, last_prompt, current_prompt, suggestions) -> json:
        json_payload = {
            "base_prompt": json.dumps(last_prompt),
            "new_prompt": json.dumps(current_prompt),
            "suggestions": json.dumps(suggestions),
        }
        res = self._post_request(report_url, json_payload)
        report = res.json()
        return report

    def _suggest(self, prompt_json: json, report: dict | None = None) -> json:
        if report is None:
            report = "[{}]"

        json_payload = {
            "base_prompt": prompt_json,
            "report": report,
        }
        res = self._post_request(suggestions_url, json_payload)
        suggestion = res.json()
        return suggestion

    def analyze(self, prompt: str) -> json | None:
        """
        prompt: str - The prompt to analyze
        returns: json - suggestion
        """
        if self._loading_analysis:
            logger.warning("Please wait for the current analysis to finish.")
            return

        try:
            logger.info("Analyzing prompts...")
            self._loading_analysis = True
            self._prompts.append(prompt)
            converted_prompt = self._convert(prompt)
            logger.debug(converted_prompt)

            logger.info("Generating suggestions...")

            if self._suggestions:
                logger.info("Running report step")
                last_prompt = self._prompts[-1]
                report_json = self._report(last_prompt, prompt, self._suggestions)
                logger.debug(report_json)
                self._report = report_json

            suggestions_json = self._suggest(converted_prompt, self._report)
            self._suggestions = suggestions_json
        except Exception as e:
            logger.error(e)
        finally:
            self._loading_analysis = False
            return self._suggestions



