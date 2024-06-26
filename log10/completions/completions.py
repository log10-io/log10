import json
import time

import click
import httpx
import pandas as pd
import rich
from rich.console import Console
from rich.table import Table

from log10._httpx_utils import _get_time_diff, _try_get
from log10.llm import Log10Config


_log10_config = Log10Config()


def _get_completion(id: str) -> httpx.Response:
    url = f"{_log10_config.url}/api/completions/{id}?organization_id={_log10_config.org_id}"
    return _try_get(url)


def _get_tag_id(tag: str) -> str:
    url = f"{_log10_config.url}/api/tags/search?organization_id={_log10_config.org_id}&query={tag}"
    res = _try_get(url)
    data = res.json()["data"]
    if not data:
        return []

    if len(data) == 1:
        return data[0]["id"]
    else:
        for item in data:
            if item["name"] == tag:
                return item["id"]
        return []


def _get_tag_ids(tags):
    tag_ids = []
    for tag in [t for t in tags.split(",") if t]:
        tag_id = _get_tag_id(tag)
        if tag_id:
            tag_ids.append(tag_id)
        else:
            raise SystemExit(f"Cannot found tag: {tag}.")

    tag_ids_str = ",".join(tag_ids)
    return tag_ids_str


def _get_completions_url(limit, offset, tags, from_date, to_date, base_url, org_id, printout=True):
    tag_ids_str = _get_tag_ids(tags) if tags else ""
    if tag_ids_str and printout:
        rich.print(f"Filter with tags: {tags}")

    date_range = _get_valid_date_range(from_date, to_date)
    if date_range and printout:
        rich.print(f"Filter with created date: {date_range['from'][:10]} to {date_range['to'][:10]}")

    url = f"{base_url}/api/completions?organization_id={org_id}&offset={offset}&limit={limit}&tagFilter={tag_ids_str}&createdFilter={json.dumps(date_range)}&sort=created_at&desc=true&ids="
    return url


def _get_valid_date_range(from_date, to_date):
    if not from_date and not to_date:
        return {}

    if from_date is None or to_date is None:
        raise click.UsageError("Both --from and --to must be set together.")

    if from_date >= to_date:
        raise click.UsageError(f"from_date {from_date} must be earlier than to_date {to_date}")

    parsed_from_date = from_date.replace(hour=8).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    parsed_to_date = to_date.replace(hour=8).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    date_range = {"from": parsed_from_date, "to": parsed_to_date}
    return date_range


def _render_completions_table(completions_data, total_completions):
    data_for_table = []
    for completion in completions_data:
        prompt, response = "", ""
        if completion.get("kind") == "completion":
            prompt = completion.get("request", {}).get("prompt", "")
            response_choices = completion.get("response", {}).get("choices", [])
            if response_choices:
                response = response_choices[0].get("text", "")
        elif completion.get("kind") == "chat":
            request_messages = completion.get("request", {}).get("messages", [])
            prompt = request_messages[0].get("content", "") if request_messages else ""

            response_choices = completion.get("response", {}).get("choices", [])
            if response_choices:
                # Handle 'message' and 'function_call' within the first choice safely
                first_choice = response_choices[0]
                if "message" in first_choice:
                    response = first_choice["message"].get("content", "")
                    if not response:
                        tool_calls = first_choice["message"].get("tool_calls", [])
                        if tool_calls:
                            last_tool_call = tool_calls[-1]
                            response = last_tool_call.get("function", {}).get("arguments", "")
                elif "function_call" in first_choice:
                    response = json.dumps(first_choice.get("function_call", {}))
        else:
            rich.print(f"Unknown completion kind: {completion['kind']} for id: {completion['id']}")

        data_for_table.append(
            {
                "id": completion["id"],
                "status": "success" if completion["status"] == "finished" else completion["status"],
                "created_at": _get_time_diff(completion["created_at"]),
                "prompt": prompt,
                "completion": response,
                "tags": [t["name"] for t in completion["tagResolved"]],
            }
        )
    # render data_for_table with rich table
    table = Table(show_header=True, header_style="bold magenta")

    table.add_column("ID", style="dim")
    table.add_column("Status")
    table.add_column("Created At")
    table.add_column("Prompt", overflow="fold")
    table.add_column("Completion", overflow="fold")
    table.add_column("Tags", justify="right")

    max_len = 40
    for item in data_for_table:
        tags = ", ".join(item["tags"]) if item["tags"] else ""
        if isinstance(item["prompt"], list):
            item["prompt"] = " ".join(item["prompt"])
        short_prompt = item["prompt"][:max_len] + "..." if len(item["prompt"]) > max_len else item["prompt"]
        completion = item.get("completion", "")
        short_completion = completion[:max_len] + "..." if len(completion) > max_len else completion
        table.add_row(item["id"], item["status"], item["created_at"], short_prompt, short_completion, tags)

    console = Console()
    console.print(table)
    console.print(f"{total_completions=}")


def _write_completions(res, output_file, compact_mode):
    """Processes completions and appends them to the output file."""
    with open(output_file, "a") as file:
        data = res.json()["data"]
        if compact_mode:
            for completion in data:
                file.write(json.dumps(completion) + "\n")
        else:
            for completion_id in (completion["id"] for completion in data):
                completion = _get_completion(completion_id).json()["data"]
                file.write(json.dumps(completion) + "\n")


def _get_llm_repsone(
    model: str,
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 512,
    top_p: float = 1.0,
):
    ret = {"content": "", "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "duration": 0.0}

    start_time = time.perf_counter()
    if "gpt-4" in model or "gpt-3.5" in model:
        from log10.load import OpenAI

        client = OpenAI()
        response = client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p
        )
        ret["content"] = response.choices[0].message.content
        ret["usage"] = response.usage.dict()
    elif "claude-3" in model:
        from log10.load import Anthropic

        system_messages = [m["content"] for m in messages if m["role"] == "system"]
        other_messages = [m for m in messages if m["role"] != "system"]
        system_prompt = ("\n").join(system_messages)

        client = Anthropic()
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=other_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )
        ret["content"] = response.content[0].text
        ret["usage"]["prompt_tokens"] = response.usage.input_tokens
        ret["usage"]["completion_tokens"] = response.usage.output_tokens
        ret["usage"]["total_tokens"] = response.usage.input_tokens + response.usage.output_tokens
    elif "mistral" in model:
        import mistralai
        from mistralai.client import MistralClient

        from log10.load import log10

        log10(mistralai)

        client = MistralClient()
        response = client.chat(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p
        )
        ret["content"] = response.choices[0].message.content
        ret["usage"] = response.usage.model_dump()
    else:
        raise ValueError(f"Model {model} not supported.")
    ret["duration"] = int((time.perf_counter() - start_time) * 1000)

    return ret


def _render_comparison_table(model_response_raw_data):
    rich.print(f"completion_id: {model_response_raw_data['completion_id']}")
    rich.print("original_request:")
    rich.print_json(json.dumps(model_response_raw_data["original_request"], indent=4))

    table = rich.table.Table(show_header=True, header_style="bold magenta", box=rich.box.ROUNDED, show_lines=True)
    table.add_column("Model")
    table.add_column("Content")
    table.add_column("Total Token Usage (Input/Output)")
    table.add_column("Duration (ms)")

    for model, data in model_response_raw_data.items():
        # only display model data
        if model not in ["completion_id", "original_request"]:
            usage = data["usage"]
            formatted_usage = f"{usage['total_tokens']} ({usage['prompt_tokens']}/{usage['completion_tokens']})"
            table.add_row(model, data["content"], formatted_usage, str(data["duration"]))
    rich.print(table)


def _create_dataframe_from_comparison_data(model_response_raw_data):
    completion_id = model_response_raw_data["completion_id"]
    original_request = model_response_raw_data["original_request"]
    rows = []
    for model, model_data in model_response_raw_data.items():
        # only display model data
        if model not in ["completion_id", "original_request"]:
            content = model_data["content"]
            usage = model_data["usage"]
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
            total_tokens = usage["total_tokens"]
            duration = model_data["duration"]
            prompt_messages = json.dumps(original_request["messages"])
            rows.append(
                [
                    completion_id,
                    prompt_messages,
                    model,
                    content,
                    prompt_tokens,
                    completion_tokens,
                    total_tokens,
                    duration,
                ]
            )

    df = pd.DataFrame(
        rows,
        columns=[
            "Completion ID",
            "Prompt Messages",
            "Model",
            "Content",
            "Prompt Tokens",
            "Completion Tokens",
            "Total Tokens",
            "Duration (ms)",
        ],
    )

    return df


def _compare(models: list[str], messages: dict, temperature: float = 0.2, max_tokens: float = 256, top_p: float = 1.0):
    ret = {}
    if models:
        for model in models:
            rich.print(f"Running {model}")
            response = _get_llm_repsone(
                model,
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )

            ret[model] = response
    return ret


_SUPPORTED_MODELS = [
    # openai chat models
    "gpt-4o",
    "gpt-4o-2024-05-13",
    "gpt-4-turbo",
    "gpt-4-turbo-2024-04-09",
    "gpt-4-0125-preview",
    "gpt-4-turbo-preview",
    "gpt-4-1106-preview",
    "gpt-4-vision-preview",
    "gpt-4",
    "gpt-4-0314",
    "gpt-4-0613",
    "gpt-4-32k",
    "gpt-4-32k-0314",
    "gpt-4-32k-0613",
    "gpt-3.5-turbo",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-0301",
    "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo-16k-0613",
    # anthropic claude
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    # mistral
    "mistral-small-latest",
    "mistral-medium-latest",
    "mistral-large-latest",
]


def _check_model_support(model: str) -> bool:
    return model in _SUPPORTED_MODELS
