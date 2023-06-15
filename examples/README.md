# Examples

## Agents

- `camel.py` A [CAMEL agent](https://www.camel-ai.org/) is a special type of agent where you let the LLM take on each of the user and assistant roles in succession to [solve a task](https://www.loom.com/share/08c363e88f0f47ff9f42fcbc39e9afb0). Often this results in better solutions to the task without the pain of manual prompt engineering. You can select between Claude (Anthropic) and OpenAI models (at the top of the file). The following examples are provided (uncomment the corresponding line at the bottom of the file and comment the rest):
  - Patching or optimizing code by a security auditor and a software developer
  - Drafting a sales email by a sales email copyeditor and a sales email copywriter
  - Onboarding a new member by a simulated new member and an expert member
  - Performing a molecular dynamics solution by a PhD student and an Experienced Computational Chemist
  - Writing a blog in a different language by a subject matter expert and a language expert

## Evals

Can be run on `OpenAI` or `Anthropic`

- `match.py` A simple example showcasing how to use metrics such as Match, Includes
- `fuzzy.py` Fuzzy matching

## Logging (and debugging)

### OpenAI

- `chatCompletion_async_vs_sync.py` Compare latencies when logging in async vs sync mode
- `chatCompletion.py` Chat endpoint example
- `completion_ada.py` Completion endpoint on Ada (cost efficient for testing purposes, but low quality output)
- `completion.py` Completion endpoint on davinci (better quality, but more expensive)
- `get_url.py` Get the URL of the completion to get the detailed logs on [log10.io](https://log10.io)

### Langchain

- `langchain_babyagi.py` [Langchain's implementation](https://python.langchain.com/en/latest/use_cases/agents/baby_agi_with_agent.html) of [BabyAGI](https://babyagi.org/)
- `langchain_multiple_tools.py` Langchain with multiple tools
- `langchain_qa.py` Langchain + DocumentQA (also checkout Streamlit example [here](https://huggingface.co/spaces/arjunbansal/log10_langchain_qa_streamlit/blob/main/app.py))
- `langchain_simple_sequential.py` Simplest Langchain example with 2 chains in sequence
- `langchain_sqlagent.py` Langchain's SQLAgent for NLP2SQL
- `multiple_sessions.py` Examples illustrating session scoping for Langchain + Log10

### Anthropic

- `anthropic_completion.py` Simple Anthropic completion example
