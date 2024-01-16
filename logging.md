# Logging

Log10 makes it easy to "log" LLM request and responses for tracing, debugging and evaluation.

## Configuration

To turn on logging for a python process, start by setting the following environment variables:

```bash
export LOG10_URL=https://log10.io
export LOG10_ORG_ID=... # Find your organization id in the organization settings in your log10.io account.
export LOG10_TOKEN=... # Create or locate an API key in the personal settings in your log10.io account.
export LOG10_DATA_STORE=log10 # Optional, can be set to bigquery. See the bigquery instructions in the README.md for more detail.
```

## Library wrapping

The simplest way to start logging openai can be done like this: 

```python
import openai
from log10.load import log10

log10(openai)
```
This works for both openai v0 and v1.

For openai v1 only, the logging can be done like this:

```python
from log10.load import OpenAI
# from openai import OpenAI

client = OpenAI()
completion = client.completions.create(model='curie', prompt="Once upon a time")
# All completions.create and chat.completions.create calls will be logged
```

From that point on, all openai calls during the process execution will be logged.
Please note that this only works for non-streaming calls at this time.

Anthropic calls can be logged like so:

```python
import os
from log10.load import log10
import anthropic
import os

log10(anthropic)
anthropicClient = anthropic.Anthropic()
```

### Sessions

To aid debugging across chains and tools, log10 creates a session id when the library is loaded.
To create several sessions within the same process, you can use the `log10_session` context like this:

```python
from log10.load import log10, log10_session
import openai

log10(openai)

with log10_session():
    # Will log in session 1

with log10_session():
    # Will log in session 2
```
### Log10 LLM Abstraction
Import Log10 LLM abstraction modules to call closed and open-source LLMs, such as OpenAI, Anthropic, and Llama-2 Inference endpoints on MosaicML and Together.

Create a log10 configuration object to log on Log10 platform.
Setting `log10_config` is optional.
```python
from log10.llm import Log10Config
```

#### OpenAI
```python
from log10.openai import OpenAI
llm = OpenAI({"model": "gpt-3.5-turbo"}, log10_config=Log10Config())
```
Full script [here](examples/logging/llm_abstraction.py#6-#14).

#### Anthropic
```python
from log10.anthropic import Anthropic
llm = Anthropic({"model": "claude-2"}, log10_config=Log10Config())
```
Full script [here](examples/logging/llm_abstraction.py#16-#19).

#### MosaicML
```python
from log10.mosaicml import MosaicML
llm = MosaicML({"model": "llama2-70b-chat/v1"}, log10_config=Log10Config())
```
Full script [here](/examples/logging/mosaicml_completion.py).

Find all the supported models on MosaicML [website](https://docs.mosaicml.com/en/latest/inference.html#text-completion-models).

#### Together
```python
from log10.together import Together
llm = Together({"model": "togethercomputer/llama-2-70b-chat"}, log10_config=Log10Config())
```
Full script [here](/examples/logging/together_completion.py).

Find all the supported models on Together [website](https://docs.together.ai/docs/inference-models).

### Tags

One useful way to organize your LLM logs is using tags. Tags are strings which can be used to filter and select logs in [log10.io](https://log10.io). See [here](https://log10.io/docs/logs) for more information about tags.

You can add tags using the session scope:

```python
import os
from log10.load import log10, log10_session
import openai
from langchain import OpenAI

log10(openai)

with log10_session(tags=["foo", "bar"]):
    response = openai.Completion.create(
        model="gpt-3.5-turbo-instruct",
        prompt="Where is the Eiffel Tower?",
        temperature=0,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    print(response)

```

An addition way to add tag with openai v1 API:
```python
from log10.load import OpenAI
client = OpenAI(tags=["foo"])
```

## LangChain logger

If you want to use LLMs which are not natively supported by log10 yet, you can use the log10 logger / callback with langchain's llm abstraction:

```python
from langchain import OpenAI
from langchain.chat_models import ChatAnthropic
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

from log10.langchain import Log10Callback
from log10.llm import Log10Config


log10_callback = Log10Callback(log10_config=Log10Config())


messages = [
    HumanMessage(content="You are a ping pong machine"),
    HumanMessage(content="Ping?"),
]

llm = ChatOpenAI(model_name="gpt-3.5-turbo", callbacks=[log10_callback], temperature=0.5, tags=["test"])
completion = llm.predict_messages(messages, tags=["foobar"])
print(completion)

llm = ChatAnthropic(model="claude-2", callbacks=[log10_callback], temperature=0.7, tags=["baz"])
llm.predict_messages(messages)
print(completion)

llm = OpenAI(model_name="gpt-3.5-turbo-instruct", callbacks=[log10_callback], temperature=0.5)
completion = llm.predict("You are a ping pong machine.\nPing?\n")
print(completion)
```

Note that both llm scoped, and individual call's tags are supported.