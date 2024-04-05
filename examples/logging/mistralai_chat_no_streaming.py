import mistralai
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from log10.load import log10


log10(mistralai)


def main():
    model = "mistral-tiny"

    client = MistralClient()

    chat_response = client.chat(
        model=model,
        messages=[ChatMessage(role="user", content="10 + 2 * 3=?")],
    )
    print(chat_response.choices[0].message.content)


if __name__ == "__main__":
    main()
