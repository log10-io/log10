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

evals:
	(cd examples/evals && python basic_eval.py)
	(cd examples/evals && python compile.py)
	(cd examples/evals && python fuzzy.py)

examples: agents evals logging

logging-completion:
	python examples/logging/openai_completions.py
	python examples/logging/anthropic_completion.py

logging-chat:
	python examples/logging/anthropic_messages.py
	python examples/logging/mistralai_chat_no_streaming.py
	python examples/logging/openai_chat.py
	python examples/logging/lamini_generate.py
	# python examples/logging/vertexai_gemini_chat.py
	python examples/logging/openai_async_logging.py
	python examples/logging/openai_async_stream_logging.py

logging-chat-stream:
	python examples/logging/openai_chat_stream.py
	python examples/logging/anthropic_messages_stream.py
	python examples/logging/mistralai_chat_with_streaming.py
	python examples/logging/litellm_completion_stream.py

logging-image:
	python examples/logging/openai_chat_image.py
	python examples/logging/anthropic_messages_image.py
	python examples/logging/litellm_image.py

logging-tools:
	python examples/logging/openai_tools.py
	python examples/logging/openai_tools_stream.py
	python examples/logging/openai_async_tools_stream.py

logging-tags:
	python examples/logging/tags_mixed.py
	python examples/logging/tags_openai.py

logging-magentic:
	python examples/logging/magentic_async_stream_logging.py
	python examples/logging/magentic_function_logging.py
	python examples/logging/magentic_async_parallel_function_call.py
	python examples/logging/magentic_async_multi_session_tags.py

logging-langchain:
	python -m xdoctest log10/load.py log10:2
	python -m xdoctest log10/load.py log10:4

logging-litellm:
	python examples/logging/litellm_async_stream_completion.py
	python examples/logging/litellm_image_stream.py
	python examples/logging/litellm_image_async_stream.py
