import mistralai
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from log10.load import log10


log10(mistralai)


def main():
    model = "mistral-tiny"

    client = MistralClient()

    response = client.chat_stream(
        model=model,
        messages=[ChatMessage(role="user", content="count the odd numbers from 1 to 20.")],
    )
    # import ipdb; ipdb.set_trace()
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
            print(chunk.choices[0].delta.content, end="")


if __name__ == "__main__":
    main()
