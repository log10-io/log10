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

## 💬 Community

We welcome community participation and feedback. Please leave an issue, submit a PR or join our [Discord](https://discord.gg/CZQvnuRV94).
