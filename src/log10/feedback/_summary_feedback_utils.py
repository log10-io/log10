import sys

import openai

from log10.load import log10


log10(openai)

if sys.version_info < (3, 10):
    raise RuntimeError("Python 3.10 or higher is required to run summary feedback llm call.")

try:
    from magentic import SystemMessage, UserMessage, chatprompt
    from magentic.chat_model.openai_chat_model import OpenaiChatModel
    from magentic.chatprompt import escape_braces
except ImportError as error:
    msg = "To use summary feedback llm call, you need to install magentic package. Please install it using 'pip install log10-io[autofeedback_icl]'"
    raise ImportError(msg) from error


# define prompts for tldr dataset
SUMMARY_SYSTEM_PROMPT = """You are an evaluator of summaries of articles on reddit. You are tasked with grading the summaries for accuracy, coherence, coverage and overall.

Coherence
For this axis, answer the question “how coherent is the summary on its own?” A summary is
coherent if, when read by itself, it’s easy to understand and free of English errors. A summary is
not coherent if it’s difficult to understand what the summary is trying to say. Generally, it’s more
important that the summary is understandable than it being free of grammar errors.
Rubric:
Score of 1: The summary is impossible to understand.
Score of 4: The summary has mistakes or confusing phrasing that make it a bit hard to understand.
Score of 7: The summary is perfectly clear.

Accuracy
For this axis, answer the question “does the factual information in the summary accurately match
the post?” A summary is accurate if it doesn’t say things that aren’t in the article, it doesn’t mix up
people, and generally is not misleading. If the summary says anything at all that is not mentioned
in the post or contradicts something in the post, it should be given a maximum score of 5. (If you
are confused about how to use ‘6’, see the FAQ!)
Rubric:
Score of 1: The summary is completely wrong, made up, or exactly contradicts what is written in
the post.
Score of 4: The summary says at least one substantial thing that is not mentioned in the post, or
that contradicts something in the post.
(Score of 5: The summary says anything, no matter how small, that is not mentioned in the post,
or that contradicts something in the post.)
Score of 7: The summary has no incorrect statements or misleading implications.

Coverage
For this axis, answer the question “how well does the summary cover the important information
in the post?” A summary has good coverage if it mentions the main information from the post
that’s important to understand the situation described in the post. A summary has poor coverage if
someone reading only the summary would be missing several important pieces of information
about the situation in the post. A summary with good coverage should also match the purpose of
the original post (e.g. to ask for advice).
Rubric:
Score of 1: The summary contains no information relevant to the post.
Score of 4: The summary is missing at least 1 important piece of information required to understand the situation.
Score of 7: The summary covers all of the important information required to understand the
situation.

Overall quality
For this axis, answer the question “how good is the summary overall at representing the post?”
This can encompass all of the above axes of quality, as well as others you feel are important. If
it’s hard to find ways to make the summary better, give the summary a high score. If there are lots
of different ways the summary can be made better, give the summary a low score.
Rubric:
Score of 1: The summary is terrible.
Score of 4: The summary is an okay representation of the post, but could be significantly improved.
Score of 7: The summary is an excellent representation of the post."""

SUMMARY_USER_MESSAGE = """
Assign scores and write a explanation note for the summary in the test post in json format based on what you think the evaluators would have assigned it.
Do not generate a new summary but just grade the summary that is presented in the last test example
Here is an example format for the final output:
{"note": "This summary is pretty concise but the key points are conveyed here", "axes": {"overall": "6", "accuracy": "6", "coverage": "5", "coherence": "6"}}

Only answer with the scores and note for the final test post and not the example posts.
Remember to not add any additional text beyond the json output
For e.g. don't say things such as "Here is my assessment:" or "Here is the extracted JSON:"
"""

SUMMARY_USER_MESSAGE = escape_braces(SUMMARY_USER_MESSAGE)


@chatprompt(
    SystemMessage(SUMMARY_SYSTEM_PROMPT),
    UserMessage(SUMMARY_USER_MESSAGE),
    UserMessage("Examples: \n{examples}\n\nTest: \n{prompt}"),
    model=OpenaiChatModel("gpt-4-0125-preview", temperature=0.2),
)
def summary_feedback_llm_call(examples, prompt) -> str: ...


def flatten_messages(completion: dict) -> dict:
    request_messages = completion.get("request", {}).get("messages", [])
    if len(request_messages) > 1 and request_messages[1].get("content", ""):
        prompt = request_messages[1].get("content")
    else:
        prompt = ""

    response_choices = completion.get("response", {}).get("choices", [])
    if response_choices and response_choices[0].get("message", {}):
        response = response_choices[0].get("message", {}).get("content", "")
    else:
        response = ""
    return {"prompt": prompt, "response": response}
