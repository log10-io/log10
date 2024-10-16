from log10.completions import Completions
from log10.load import log10_tags


def main():
    completions = Completions()
    model = "gpt-4o"
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What's the capital of France?"},
    ]
    response_content = "The capital of France is Paris."
    with log10_tags(["examples"]):
        result = completions.mock_chat_completions(
            model=model, messages=messages, response_content=response_content, tags=["geography"]
        )
    print(f"Assistant's response: {result.choices[0].message.content}")
    print(f"Model used: {result.model}")


if __name__ == "__main__":
    main()
