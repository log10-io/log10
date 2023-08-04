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

Access your LLM data at [log10.io](https://log10.io)


## 🚀 What can this help with?

**🔍🐞 Prompt chain debugging**

Prompt chains such as those in [Langchain](https://github.com/hwchase17/langchain) can be difficult to debug. Log10 provides prompt provenance, session tracking and call stack functionality to help debug chains.

**📝📊 Logging**

Log all your OpenAI calls to compare and find the best prompts, store feedback, collect latency and usage metrics, and perform analytics and compliance monitoring of LLM powered features.

You can log any openai (as [shown above](#🤔-what-is-this)) or anthropic based application using the library wrappers from log10:

```python
import os
from log10.load import log10
import anthropic
import os

log10(anthropic)
anthropicClient = anthropic.Client()
# anthropic calls are now logged
```

This will log any LLM call through the process execution.

If you want to log other LLMs, you can use LangChain's LLM abstraction with the log10 logger:

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

**💿🧩 Flexible data store**

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

**🧠🔁 Readiness for RLHF & self hosting**

Use your data and feedback from users to fine-tune custom models with RLHF with the option of building and deploying more reliable, accurate and efficient self-hosted models. 

**👥🤝 Collaboration**

Create flexible groups to share and collaborate over all of the above features

## ⚙️ Setup

1. Create a free account at [log10.io](https://log10.io)
2. Set the following environment variables:
- `LOG10_URL=https://log10.io`
- `LOG10_TOKEN`: From the Settings tab in log10.io
- `LOG10_ORG_ID`: From the Organization tab in log10.io
- `OPENAI_API_KEY`: OpenAI API key
- `ANTHROPIC_API_KEY`: Anthropic API key

## 💬 Community

We welcome community participation and feedback. Please leave an issue, submit a PR or join our [Discord](https://discord.gg/CZQvnuRV94).
