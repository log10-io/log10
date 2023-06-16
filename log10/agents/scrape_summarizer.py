from log10.utils import convert_history_to_claude
from anthropic import HUMAN_PROMPT
from log10.tools import browser


# Set up Summarizer agent
system_prompt = "You are an expert at extracting the main points from a website. Only look at the provided website content by the user to extract the main points."
summarize_prompt = "Extract the main points from the following website:\n {website_text}"


def scrape_summarizer(url, model, module, hparams):
    website_text = browser(url)
    prompt = summarize_prompt.format(website_text=website_text)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    if 'claude' in model:
        completion = module.completion(
            prompt=convert_history_to_claude(messages),
            stop_sequences=[HUMAN_PROMPT],
            model=model,
            **hparams
        )
        website_summary = completion['completion']
    else:
        completion = module.ChatCompletion.create(
            model=model, messages=messages, temperature=0.2)
        website_summary = completion.choices[0].message
    return website_summary
