# log10

⚡ Unified LLM data management to drive accuracy at scale ⚡

[![pypi](https://github.com/log10-io/log10/actions/workflows/release.yml/badge.svg)](https://github.com/log10-io/log10/actions/workflows/release.yml)
[![](https://dcbadge.vercel.app/api/server/CZQvnuRV94?compact=true&style=flat)](https://discord.gg/CZQvnuRV94)

## Quick Install

`pip install log10-io`

## 🤔 What is this?

<img width="800" alt="Log10 stack" src="https://github.com/user-attachments/assets/8a790f82-6d75-4aa0-905b-7d3693815414">

A one-line Python integration to manage your LLM data.

```python
import openai
from log10.load import log10

log10(openai)
# all your openai calls are now logged - including 3rd party libs using openai
```
For OpenAI v1, use `from log10.load import OpenAI` instead of `from openai import OpenAI`
```python
from log10.load import OpenAI

client = OpenAI()
```
Access your LLM data at [log10.io](https://log10.io)


## 🚀 What can this help with?

### 📝📊 Logging

Use Log10 to log both closed and open-source LLM calls, e.g. OpenAI, Anthropic, Google Gemini, Llama, Mistral, etc. It helps you:
- Compare and identify the best models and prompts (try [playground](https://log10.io/docs/observability/playgrounds) and [llmeval](https://log10.io/docs/evaluation/installation))
- Store feedback for fine-tuning
- Collect performance metrics such as latency and usage
- Perform analytics and monitor compliance for LLM powered applications

Log10 offers various integration methods, including a python LLM library wrapper, the Log10 LLM abstraction, and callbacks, to facilitate its use in both existing production environments and new projects.
Pick the one that works best for you.

#### OpenAI
| log10 ver| openai v0 | openai v1 |
|----------|----------|----------|
| 0.4 | `log10(openai)` ✅ | ❌ |
| 0.5+ | `log10(openai)` ✅ | `from log10.load import OpenAI` ✅ |

**OpenAI v0** - Use library wrapper `log10(openai)`. Check out `examples/logging` in log10 version `0.4.6`.
```python
import openai
from log10.load import log10

log10(openai)
# openai calls are now logged - including 3rd party libs using openai such as magentic or langchain
```

**OpenAI v1**
> NOTE: We added OpenAI v1 API support in log10 `0.5.0` release. `load.log10(openai)` still works for openai v1. This also enables logging LLM completions from providers which support OpenAI API, such as [Ollama](https://github.com/ollama/ollama/blob/main/docs/openai.md).

```python
from log10.load import OpenAI
# from openai import OpenAI

client = OpenAI()
completion = client.completions.create(model="gpt-3.5-turbo-instruct", prompt="Once upon a time")
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

#### Asynchronous LLM calls
We support OpenAI and Anthropic Async-client (e.g. AsyncOpenAI and AsyncAnthropic client) in their Python SDK
You could use the same code `log10(openai)` or `log10(anthropic)` and then call the async-client to start logging asynchronous mode (including streaming).

Release `0.9.0` includes significant improvements in how we handle concurrency while using LLM in asynchronous streaming mode.
This update is designed to ensure that logging at steady state incurs no overhead (previously up to 1-2 seconds), providing a smoother and more efficient experience in latency critical settings.

__Important Considerations for Short-Lived Scripts__:
> 💡For short-lived scripts using asynchronous streaming, it's important to note that you may need to wait until all logging requests have been completed before terminating your script.
We have provided a convenient method called `finalize()` to handle this.
Here's how you can implement this in your code:

``` python
from log10._httpx_utils import finalize

...

await finalize()
```
Ensure `finalize()` is called once, at the very end of your event loop to guarantee that all pending logging requests are processed before the script exits.


For more details, check [async logging examples](./examples/logging/).

#### Open-source LLMs
Log open-source LLM calls, e.g. Llama, Mistral, etc from providers.
Currently we support inference endpoints on Together.AI and MosaicML (ranked on the top based on our [benchmarking](https://arjunbansal.substack.com/p/which-llama-2-inference-api-should-i-use) on Llama-2 inference providers).
Adding other providers is on the roadmap.

If the providers support OpenAI API (e.g. [Groq](https://console.groq.com/docs/openai), [vLLM](https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html), [Together](https://docs.together.ai/docs/openai-api-compatibility)), you can easily starting logging using `log10(openai)`.

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

### 🤖👷 Prompt engineering copilot

Optimizing prompts requires a lot of manual effort. Log10 provides a copilot that can help you with suggestions on how to [optimize your prompt](https://log10.io/docs/prompt_engineering/auto_prompt#how-to-use-auto-prompting-in-log10-python-library).

### 👷🔢 Feedback

Add feedback to your completions. Checkout the Python [example](/examples/feedback/simple_feedback.py)
or use CLI `log10 feedback-task create` and `log10 feedback create`. Please check our [doc](https://log10.io/docs/feedback) for more details.

#### AutoFeedback
Leverage your current feedback and AI by using our AutoFeedback feature to generate feedback automatically. Here’s a quick guide:

* Summary feedback: Use [TLDR summary feedback](/log10/feedback/_summary_feedback_utils.py) rubics to rate summarization. E.g. `log10 feedback predict --task_id $FEEDBACK_TASK_ID --content '{"prompt": "this is article", "response": "summary of the article."}'`.
  * You can pass a file containing the context with `--file` or pass a completion from your Log10 logs with `--completion_id`.
* Custom Feedback Rubrics: Integrate your own feedback criteria for personalized assessments.
* Getting Started: To explore all options and usage details, use CLI `log10 feedback predict --help`.

Feel free to integrate AutoFeedback into your workflow to enhance the feedback and evaluation process.

### ⚖️📊 Model Comparison
Easily benchmark your logged completions using LLM models from OpenAI, Anthropic, Mistral, Meta, etc., by using the `log10 completions benchmark_models` command in the log10 CLI.
Generate detailed reports and gain insights to enhance your model's performance and cost.
Please refer to the [cli doc](cli_docs.md#log10-completions-benchmark_models) or the [demo video](https://www.loom.com/share/6d088f9f079f4e65962741f58344d77e?sid=1d2c51e6-8978-4422-af5b-d39ebe561b83) for details.

### 🔍🐞 Prompt chain debugging

Prompt chains such as those in [Langchain](https://github.com/hwchase17/langchain) can be difficult to debug. Log10 provides prompt provenance, session tracking and call stack functionality to help debug chains.

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

## CLI for completions and feedback
We add CLI to manage your completions and feedback. Read more [here](cli_docs.md).

## 💬 Community

We welcome community participation and feedback. Please leave an issue, submit a PR or join our [Discord](https://discord.gg/CZQvnuRV94). For enterprise use cases, please [contact us](mailto:support@log10.io) to set up a shared slack channel.
