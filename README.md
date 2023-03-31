# log10

⚡ Unified LLM data management ⚡

## Quick Install

`pip install -e git+https://github.com/log10-io/log10.git#egg=log10`

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

**🧠🔁 Readiness for RLHF & self hosting**

Use your data and feedback from users to fine-tune custom models with RLHF with the option of building and deploying more reliable, accurate and efficient self-hosted models. 

**👥🤝 Collaboration**

Create flexible groups to share and collaborate over all of the above features

## ⚙️ Setup

Create a free account at [log10.io](https://log10.io) to get a `LOG10_TOKEN` and a `LOG10_ORG_ID`. Please add these to your environment along with `LOG10_URL=https://log10.io`. 

## 💬 Community

We welcome community participation and feedback. Please leave an issue, submit a PR or join our [Discord](https://discord.gg/CGW6xNbC).