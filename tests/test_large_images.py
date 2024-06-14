from log10.load import filter_large_images
import copy


def test_empty_messages():
    assert filter_large_images([]) == []


# Test for regular messages without fragments i.e. content isn't a list.
def test_non_fragment_messages():
    messages = [
        {"content": "This is a message.", "role": "system"},
        {"content": "This is another message.", "role": "user"},
    ]
    assert filter_large_images(copy.deepcopy(messages)) == messages


# Test for a message with a fragment that is not an image.
def test_non_image_fragment():
    messages = [
        {"content": [{"type": "text", "text": "This is a message."}], "role": "system"},
        {
            "content": [{"type": "text", "text": "This is another message."}],
            "role": "user",
        },
    ]
    assert filter_large_images(copy.deepcopy(messages)) == messages


def test_small_image_fragment():
    messages = [
        {"content": [{"type": "text", "text": "This is a message."}], "role": "system"},
        {
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": "https://example.com/image.png"},
                }
            ],
            "role": "system",
        },
        {"content": [{"type": "text", "text": "This is a message."}], "role": "system"},
    ]
    assert filter_large_images(copy.deepcopy(messages)) == messages


def test_large_image_fragment():
    large_string = "a" * int(2e6)
    before_messages = [
        {"content": [{"type": "text", "text": "This is a message."}], "role": "system"},
        {
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{large_string}"},
                }
            ],
            "role": "system",
        },
        {"content": [{"type": "text", "text": "This is a message."}], "role": "system"},
    ]
    after_messages = [
        {"content": [{"type": "text", "text": "This is a message."}], "role": "system"},
        {
            "content": [
                {
                    "type": "text",
                    "text": "Image too large to capture",
                },
            ],
            "role": "system",
        },
        {"content": [{"type": "text", "text": "This is a message."}], "role": "system"},
    ]
    assert filter_large_images(before_messages) == after_messages
