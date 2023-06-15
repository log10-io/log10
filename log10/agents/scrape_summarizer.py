from log10.utils import convert_history_to_claude
from anthropic import HUMAN_PROMPT
from langchain.document_loaders import WebBaseLoader

# Set up Summarizer agent
system_prompt = "You are an expert at extracting the main points from a website. Only look at the provided website content by the user to extract the main points."
summarize_prompt = "Extract the main points from the following website:\n {website_text}"

# Browser agent / tool
def browser(URL: str) -> str:
    """useful when you need to scrape a website. 
    Input is the URL of the website to be scraped.
    Output is the text of the website
    """
    # Example code if we want to follow links
    # explored_sites = set()
    # queue = [URL]

    # def parse_site(base_url):
    #   if base_url in explored_sites:
    #     return

    #   explored_sites.add(base_url)

    #   if debug:
    #     print("Scraping: ", base_url)

    #   page = requests.get(URL)
    #   soup = BeautifulSoup(page.content, "html.parser")
    #   for a_href in soup.find_all("a", href=True):
    #       link = a_href["href"]
    #       if link[0] == "/":
    #         link = URL + link

    #       if link.startswith(URL):
    #         to_explore = link.split("#")[0]
    #         queue.append(to_explore)

    # while len(queue) != 0:
    #   url = queue.pop()
    #   parse_site(url)

    # return list(explored_sites)

    loader = WebBaseLoader(URL)
    data = loader.load()
    data[0].page_content = " ".join(data[0].page_content.split())

    # hack: crop to 5000 char to fit within context length
    # Will need better strategy eventually
    #   maxlen = 5000 if len(data[0].page_content) > 5000 else len(data[0].page_content)
    #   return data[0].page_content[:maxlen]
    return data[0].page_content


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
