.PHONY: examples agents evals logging

agents:
	LOG10_EXAMPLES_MODEL=noop python examples/agents/biochemist.py
	LOG10_EXAMPLES_MODEL=noop python examples/agents/code_optimizer.py
	LOG10_EXAMPLES_MODEL=noop python examples/agents/coder.py
	LOG10_EXAMPLES_MODEL=noop python examples/agents/cybersecurity_expert.py
	LOG10_EXAMPLES_MODEL=noop python examples/agents/email_generator.py
	LOG10_EXAMPLES_MODEL=noop python examples/agents/scrape_summarizer.py
	LOG10_EXAMPLES_MODEL=noop python examples/agents/translator.py

	LOG10_EXAMPLES_MODEL=gpt-3.5-turbo-16k python examples/agents/biochemist.py
	LOG10_EXAMPLES_MODEL=gpt-3.5-turbo-16k python examples/agents/code_optimizer.py
	LOG10_EXAMPLES_MODEL=gpt-3.5-turbo-16k python examples/agents/coder.py
	LOG10_EXAMPLES_MODEL=gpt-3.5-turbo-16k python examples/agents/cybersecurity_expert.py
	LOG10_EXAMPLES_MODEL=gpt-3.5-turbo-16k python examples/agents/email_generator.py
	LOG10_EXAMPLES_MODEL=gpt-3.5-turbo-16k python examples/agents/scrape_summarizer.py
	LOG10_EXAMPLES_MODEL=gpt-3.5-turbo-16k python examples/agents/translator.py

	LOG10_EXAMPLES_MODEL=claude-2 python examples/agents/biochemist.py
	LOG10_EXAMPLES_MODEL=claude-2 python examples/agents/code_optimizer.py
	LOG10_EXAMPLES_MODEL=claude-2 python examples/agents/coder.py
	LOG10_EXAMPLES_MODEL=claude-2 python examples/agents/cybersecurity_expert.py
	LOG10_EXAMPLES_MODEL=claude-2 python examples/agents/email_generator.py
	LOG10_EXAMPLES_MODEL=claude-2 python examples/agents/scrape_summarizer.py
	LOG10_EXAMPLES_MODEL=claude-2 python examples/agents/translator.py

logging:
	python examples/logging/anthropic_completion.py
	python examples/logging/chatcompletion.py
	python examples/logging/chatcompletion_async_vs_sync.py
	python examples/logging/completion.py
	python examples/logging/completion_simple.py
	python examples/logging/get_url.py
	# python examples/logging/langchain_babyagi.py
	python examples/logging/langchain_model_logger.py
	python examples/logging/langchain_multiple_tools.py
	python examples/logging/langchain_qa.py
	python examples/logging/langchain_simple_sequential.py
	python examples/logging/langchain_sqlagent.py
	python examples/logging/multiple_sessions.py
	python examples/logging/tags_mixed.py
	python examples/logging/tags_openai.py

evals:
	(cd examples/evals && python basic_eval.py)
	(cd examples/evals && python compile.py)
	(cd examples/evals && python fuzzy.py)

examples: agents evals logging
