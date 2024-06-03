import uuid

from log10.completions.completions import _get_completion


def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def format_magentic_function_args(outputs):
    return [{"name": t._function.__name__, "arguments": str(t.arguments)} for t in outputs]


def format_function_args(tool_calls):
    return [{"name": t.function.name, "arguments": t.function.arguments} for t in tool_calls]


class _LogAssertion:
    def __init__(self, *args, **kwargs):
        self._completion_id = kwargs.get("completion_id", "")
        self._message_content = kwargs.get("message_content", "")
        self._text = kwargs.get("text", "")
        self._function_args = kwargs.get("function_args", [])

        assert self._completion_id, "No completion id provided."
        assert is_valid_uuid(self._completion_id), "Completion ID should be found and valid uuid."

    def get_completion(self):
        res = _get_completion(self._completion_id)
        self.data = res.json()["data"]
        assert self.data.get("response", {}), f"No response logged for completion {self._completion_id}."
        self.response = self.data["response"]

    def assert_expected_response_fields(self):
        assert self.data.get("status", ""), f"No status logged for completion {self._completion_id}."
        assert self.response.get("choices", []), f"No choices logged for completion {self._completion_id}."
        self.response_choices = self.response["choices"]

    def assert_text_response(self):
        assert self._text, "No output generated from the model."
        self.get_completion()
        self.assert_expected_response_fields()

        choice = self.response_choices[0]
        assert choice.get("text", {}), f"No text logged for completion {self._completion_id}."
        text = choice["text"]
        assert (
            self._text == text
        ), f"Text does not match the generated completion for completion {self._completion_id}."

    def assert_chat_response(self):
        assert self._message_content, "No output generated from the model."
        self.get_completion()
        self.assert_expected_response_fields()

        choice = self.response_choices[0]
        assert choice.get("message", {}), f"No message logged for completion {self._completion_id}."
        message = choice["message"]
        assert message.get("content", ""), f"No message content logged for completion {self._completion_id}."
        message_content = message["content"]
        assert (
            message_content == self._message_content
        ), f"Message content does not match the generated completion for completion {self._completion_id}."

    def assert_function_call_response(self):
        assert self._function_args, "No function args generated from the model."

        self.get_completion()
        self.assert_expected_response_fields()
        choice = self.response_choices[0]
        assert choice.get("message", {}), f"No message logged for completion {self._completion_id}."
        message = choice["message"]
        assert message.get("tool_calls", []), f"No function calls logged for completion {self._completion_id}."
        response_tool_calls = message["tool_calls"]
        response_function_args = [
            {"name": t.get("function", "").get("name", ""), "arguments": t.get("function", "").get("arguments", "")}
            for t in response_tool_calls
        ]

        assert len(response_function_args) == len(
            self._function_args
        ), f"Function calls do not match the generated completion for completion {self._completion_id}."
