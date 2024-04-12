import json
import time

import anthropic
import click
import mistralai
import mistralai.client
import openai
import rich

from log10.completions.completions import _get_completion
from log10.load import log10


log10(openai)
log10(anthropic)
log10(mistralai)


SUPPORTED_MODELS = [
    "gpt-4-0125-preview",
]


def _get_llm_repsone(
    model: str,
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 512,
    top_p: float = 1.0,
):
    ret = {"content": "", "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "duration": 0.0}
    # TODO: use log10 llm abstraction
    start_time = time.perf_counter()
    if "gpt-4" in model or "gpt-3.5" in model:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p
        )
        ret["content"] = response.choices[0].message.content
        ret["usage"] = response.usage.dict()
    elif "claude-3" in model:
        system_messages = [m["content"] for m in messages if m["role"] == "system"]
        other_messages = [m for m in messages if m["role"] != "system"]
        system_prompt = ("\n").join(system_messages)

        client = anthropic.Anthropic()
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
        client = mistralai.client.MistralClient()
        response = client.chat(
            model=model, messages=messages, temperature=temperature, max_tokens=max_tokens, top_p=top_p
        )
        ret["content"] = response.choices[0].message.content
        ret["usage"] = response.usage.dict()
    else:
        raise ValueError(f"Model {model} not supported.")
    ret["duration"] = int((time.perf_counter() - start_time) * 1000)

    return ret


@click.command()
@click.option("--id", prompt="Enter completion id", help="Completion ID")
@click.option("--models", default="", help="Comma separated list of models to compare")
@click.option("--temperature", default=0.2, help="Temperature")
@click.option("--max_tokens", default=512, help="Max tokens")
@click.option("--top_p", default=1.0, help="Top p")
def compare(id, models, temperature, max_tokens, top_p):
    res = _get_completion(id)
    data = res.json()["data"]
    original_model_request = data["request"]
    original_model_response = data["response"]
    original_model = original_model_response["model"]
    # rich.print(f"{original_model_request=}")
    # rich.print(f"{original_model_response=}")

    ret = {
        "completion_id": id,
        "original_request": original_model_request,
        original_model: {
            "content": original_model_response["choices"][0]["message"]["content"],
            "usage": original_model_response["usage"],
            "duration": data["duration"],
        },
    }
    if models:
        model_list = models.split(",")
        for model in model_list:
            rich.print(f"Running {model}")
            response = _get_llm_repsone(
                model,
                original_model_request["messages"],
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
            )

            ret[model] = response

    # table view to show request messages, and response messages for each model, including the original_response
    # also show the usage of tokens for each model and the duration
    rich.print(f"completion_id: {id}")
    rich.print("original_request:")
    rich.print_json(json.dumps(original_model_request, indent=4))

    table = rich.table.Table(show_header=True, header_style="bold magenta", box=rich.box.ROUNDED, show_lines=True)
    table.add_column("Model")
    table.add_column("Content")
    table.add_column("Usage (prompt/completion)")
    table.add_column("Duration (ms)")
    # put a string for usage, make the format showing total_tokens (prompt_tokens/completion_tokens)

    for model, data in ret.items():
        if model not in ["completion_id", "original_request"]:
            usage = data["usage"]
            formatted_usage = f"{usage['total_tokens']} ({usage['prompt_tokens']}/{usage['completion_tokens']})"
            table.add_row(model, data["content"], formatted_usage, str(data["duration"]))
    rich.print(table)


if __name__ == "__main__":
    compare()
