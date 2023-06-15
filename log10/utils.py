import re
import string
from anthropic import HUMAN_PROMPT, AI_PROMPT
import json

# Ref: https://github.com/openai/evals/blob/a24f20a357ecb3cc5eec8323097aeade9585796c/evals/elsuite/utils.py
def normalize(s: str) -> str:
    """Lower text and remove punctuation, articles and extra whitespace."""
    s = s.lower()
    exclude = set(string.punctuation)
    s = "".join(char for char in s if char not in exclude)
    s = re.sub(r"\b(a|an|the)\b", " ", s)
    s = " ".join(s.split())
    return s


def fuzzy_match(s1: str, s2: str) -> bool:
    s1 = normalize(s1)
    s2 = normalize(s2)

    if s1 == "" or s2 == "":
        return s1 == s2

    return s1 in s2 or s2 in s1


def convert_history_to_claude(history):
    text = ""
    for item in history:
        # Anthropic doesn't support a system prompt OOB
        if item['role'] == 'user' or item['role'] == 'system':
            text += HUMAN_PROMPT
        elif item['role'] == 'assistant':
            text += AI_PROMPT
        text += f"{item['content']}"
    text += AI_PROMPT
    return text


def parse_field(value):
    try:
        # Try to parse the value as JSON (list)
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
        else:
            return [value]
    except json.JSONDecodeError:
        # If it's not valid JSON, return the original string value as a list with singleton element
        return [value]
