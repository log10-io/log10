from log10.completions import Completions


def main():
    completions = Completions()
    model = "gpt-4o"
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What's the capital of France?"},
    ]
    response_content = "The capital of France is Paris."
    result = completions.mock_chat_completions(
        model=model, messages=messages, response_content=response_content, tags=["geography", "test"]
    )
    print(f"Assistant's response: {result.choices[0].message.content}")
    print(f"Model used: {result.model}")


if __name__ == "__main__":
    main()
