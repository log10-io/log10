# log10

⚡ Unified LLM data management ⚡

[![pypi](https://github.com/log10-io/log10/actions/workflows/release.yml/badge.svg)](https://github.com/log10-io/log10/actions/workflows/release.yml)
[![](https://dcbadge.vercel.app/api/server/CZQvnuRV94?compact=true&style=flat)](https://discord.gg/CZQvnuRV94)

## Quick Install

`pip install log10-io`

## 🤔 What is this?

A one-line Python integration to manage your LLM data.

```python
import openai
from log10.load import log10

log10(openai)
# all your openai calls are now logged
```
For OpenAI v1, use `from log10.load import OpenAI` instead of `from openai import OpenAI`
```python
from log10.load import OpenAI

client = OpenAI()
```
Access your LLM data at [log10.io](https://log10.io)


## 🚀 What can this help with?

### 🔍🐞 Prompt chain debugging

Prompt chains such as those in [Langchain](https://github.com/hwchase17/langchain) can be difficult to debug. Log10 provides prompt provenance, session tracking and call stack functionality to help debug chains.

### 📝📊 Logging

Use Log10 to log both closed and open-source LLM calls. It helps you:
- Compare and identify the best models and prompts (try [playground](https://log10.io/docs/observability/playgrounds) and [llmeval](https://log10.io/docs/evaluation/installation))
- Store feedback for fine-tuning
- Collect performance metrics such as latency and usage
- Perform analytics and monitor compliance for LLM powered applications

Log10 offers various integration methods, including a python LLM library wrapper, the Log10 LLM abstraction, and callbacks, to facilitate its use in both existing production environments and new projects.
Pick the one that works best for you.

#### OpenAI
| log10 ver| openai v0 | openai v1 |
|----------|----------|----------|
| 0.4 | `load(openai)` ✅ | ❌ |
| 0.5 | `load(openai)` ✅ | `from log10.load import OpenAI` ✅ |

**OpenAI v0** - Use library wrapper `log10(openai)`. Check out `examples/logging` in log10 version `0.4.6`.
```python
import openai
from log10.load import log10

log10(openai)
# openai calls are now logged
```

**OpenAI v1**
> NOTE: We added OpenAI v1 API support in log10 `0.5.0` release. `load.log10(openai)` still works for openai v1.
```python
from log10.load import OpenAI
# from openai import OpenAI

client = OpenAI()
completion = client.completions.create(model="curie", prompt="Once upon a time")
# All completions.create and chat.completions.create calls will be logged
```
Full script [here](examples/logging/completion.py).


**Use Log10 LLM abstraction**

```python
from log10.openai import OpenAI

llm = OpenAI({"model": "gpt-3.5-turbo"}, log10_config=Log10Config())
```
openai v1+ lib required. Full script [here](examples/logging/llm_abstraction.py#6-#14).

#### Anthropic
Use library wrapper `log10(anthropic)`.
Full script [here](/examples/logging/anthropic_completion.py).
```python
import anthropic
from log10.load import log10

log10(anthropic)
# anthropic calls are now logged
```

Use Log10 LLM abstraction.
Full script [here](examples/logging/llm_abstraction.py#16-#19).
```python
from log10.anthropic import Anthropic

llm = Anthropic({"model": "claude-2"}, log10_config=Log10Config())
```

#### Open-source LLMs
Log open-source LLM calls, e.g. Llama-2, Mistral, etc from providers.
Currently we support inference endpoints on Together.AI and MosaicML (ranked on the top based on our [benchmarking](https://arjunbansal.substack.com/p/which-llama-2-inference-api-should-i-use) on Llama-2 inference providers).
Adding other providers is on the roadmap.

**MosaicML** with LLM abstraction. Full script [here](/examples/logging/mosaicml_completion.py).
```python
from log10.mosaicml import MosaicML

llm = MosaicML({"model": "llama2-70b-chat/v1"}, log10_config=Log10Config())
```

**Together** with LLM abstraction. Full script [here](/examples/logging/together_completion.py).
```python
from log10.together import Together

llm = Together({"model": "togethercomputer/llama-2-70b-chat"}, log10_config=Log10Config())
```

#### Other LLM frameworks
Use Log10 callbacks if you use LangChain's LLM abstraction. Full script [here](/examples/logging/langchain_model_logger.py).

```python
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage

from log10.langchain import Log10Callback
from log10.llm import Log10Config

log10_callback = Log10Callback(log10_config=Log10Config())

messages = [
    HumanMessage(content="You are a ping pong machine"),
    HumanMessage(content="Ping?"),
]

llm = ChatOpenAI(model_name="gpt-3.5-turbo", callbacks=[log10_callback])
```

Read more here for options for logging using library wrapper, langchain callback logger and how to apply log10 tags [here](./logging.md).

### 💿🧩 Flexible data store

log10 provides a managed data store, but if you'd prefer to manage data in your own environment, you can use data stores like google big query.

Install the big query client library with:

`pip install log10-io[bigquery]`

And provide the following configuration in either a `.env` file, or as environment variables:

| Name | Description |
|------|-------------|
| `LOG10_DATA_STORE`  |  Either `log10` or `bigquery` |
| `LOG10_BQ_PROJECT_ID`   | Your google cloud project id      |
| `LOG10_BQ_DATASET_ID`  |  The big query dataset id  |
| `LOG10_BQ_COMPLETIONS_TABLE_ID` | The name of the table to store completions in |

**Note** that your environment should have been setup with google cloud credentials. Read more [here](https://cloud.google.com/sdk/gcloud/reference/auth/login) about authenticating.

### 🧠🔁 Readiness for RLHF & self hosting

Use your data and feedback from users to fine-tune custom models with RLHF with the option of building and deploying more reliable, accurate and efficient self-hosted models.

### 👥🤝 Collaboration

Create flexible groups to share and collaborate over all of the above features

## ⚙️ Setup

1. Create a free account at [log10.io](https://log10.io)
2. Set the following environment variables:
- `LOG10_URL=https://log10.io`
- `LOG10_TOKEN`: From the Settings tab in log10.io
- `LOG10_ORG_ID`: From the Organization tab in log10.io
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key

### ✅ Run examples and tests

You can find and run examples under folder `examples`, e.g. run a logging example:
```
python examples/logging/chatcompletion.py
```

Also you can run some end-to-end tests with [`xdocttest`](https://github.com/Erotemic/xdoctest) installed (`pip install xdoctest`).

```
# list all tests
python -m xdoctest log10 list

# run all tests
python -m xdoctest log10 all

# run a single test, e.g.
python -m xdoctest /Users/wenzhe/dev/log10/log10/load.py log10:0
```

### Logging
Few options to enable debug logging:
1. set environment varible `export LOG10_DEBUG=1`
1. set `log10.load.log10(DEBUG_=True)` when using `log10.load`
1. set `log10_config(DEBUG=True)` when using llm abstraction classes or callback.

## 💬 Community

We welcome community participation and feedback. Please leave an issue, submit a PR or join our [Discord](https://discord.gg/CZQvnuRV94).
