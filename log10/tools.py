from langchain.document_loaders import WebBaseLoader
from log10.utils import convert_history_to_claude

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


def code_extractor(full_response, language, completion_func, extraction_model, hparams):
    """useful when you need to extract just the code from a detailed LLM response
    """
    funcname = completion_func.__qualname__
    messages = [
            {"role": "system", "content": f"Extract just the {language} code from the following snippet. Do not include ``` or markdown syntax. Format your reply so I can directly copy your entire response, save it as a file and compile and run the code."},
            {"role": "user", "content": "Here's the snippet:\n" + full_response}
        ]
    if funcname == 'ChatCompletion.create':
        completion = completion_func(model=extraction_model, messages=messages, temperature=0.2, **hparams)
        code = completion.choices[0].message.content
    elif funcname == 'Client.completion':
        prompt = convert_history_to_claude(messages)
        completion = completion_func(model=extraction_model, prompt=prompt, temperature=0.2, **hparams)
        code = completion['completion']

    return code
