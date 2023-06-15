import sys

if 'init_modules' in globals():
    # second or subsequent run: remove all but initially loaded modules
    for m in list(sys.modules.keys()):
        if m not in init_modules:
            del (sys.modules[m])
else:
    # first run: find out which modules were initially loaded
    init_modules = list(sys.modules.keys())

import os
from log10.load import log10, log10_session
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

# Launch an async run
with log10_session():
    log10(openai, DEBUG_=True, USE_ASYNC_=True)
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {'role': "system", "content": "You are the most knowledgable Star Wars guru on the planet"},
            {"role": "user", "content": "Write the time period of all the Star Wars movies and spinoffs?"}
        ]
    )
    print(completion.choices[0].message)

# reload modules to prevent double calling openAI
if 'init_modules' in globals():
    # second or subsequent run: remove all but initially loaded modules
    for m in list(sys.modules.keys()):
        if m not in init_modules:
            del (sys.modules[m])
else:
    # first run: find out which modules were initially loaded
    init_modules = list(sys.modules.keys())


import openai  # noqa

# Compare to sync run - note there can be variability in the OpenAI calls
with log10_session():
    log10(openai, DEBUG_=True, USE_ASYNC_=False)

    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {'role': "system", "content": "You are the most knowledgable Star Wars guru on the planet"},
            {"role": "user", "content": "Write the time period of all the Star Wars movies and spinoffs?"}
        ]
    )
    print(completion.choices[0].message)
