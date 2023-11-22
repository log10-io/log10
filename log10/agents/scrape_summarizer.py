from log10.llm import LLM, Message, Role
from log10.tools import browser

# Set up Summarizer agent
system_prompt = (
    "You are an expert at extracting the main points from a website. "
    + "Only look at the provided website content by the user to extract the main points."
)
summarize_prompt = (
    "Extract the main points from the following website:\n {website_text}"
)


def scrape_summarizer(url, llm: LLM):
    website_text = browser(url)
    prompt = summarize_prompt.format(website_text=website_text)
    messages = [
        Message(role=Role.system, content=system_prompt),
        Message(role=Role.user, content=prompt),
    ]

    hparams = {"temperature": 0.2}

    completion = llm.chat(messages, hparams)

    return completion.content
