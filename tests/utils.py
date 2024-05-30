import uuid

from log10.completions.completions import _get_completion


def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def is_arrays_matched(arr1, arr2):
    if len(arr1) != len(arr2):
        return False

    for dict1, dict2 in zip(arr1, arr2):
        if dict1 != dict2:
            return False

    return True


class _LogAssertion:
    def __init__(self, *args, **kwargs):
        self._completion_id = kwargs.get("completion_id", "")
        self._message_content = kwargs.get("message_content", "")
        self._message_tool_calls = kwargs.get("message_tool_calls", [])

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
        choice = self.response_choices[0]
        assert choice.get("message", {}), f"No message logged for completion {self._completion_id}."
        self.message = choice["message"]

    def assert_chat_response(self):
        assert self._message_content, "No output generated from the model."
        self.get_completion()
        self.assert_expected_response_fields()

        assert self.message.get("content", ""), f"No message content logged for completion {self._completion_id}."
        message_content = self.message["content"]
        assert (
            message_content == self._message_content
        ), f"Message content does not match the generated completion for completion {self._completion_id}."

    def assert_function_call_response(self):
        assert self._message_tool_calls, "No tool calls generated from the model."
        function_args = [
            {"name": t.function.name, "arguments": t.function.arguments} for t in self._message_tool_calls
        ]

        self.get_completion()
        self.assert_expected_response_fields()

        assert self.message.get("tool_calls", []), f"No function calls logged for completion {self._completion_id}."
        response_tool_calls = self.message["tool_calls"]
        response_function_args = [
            {"name": t.get("function", "").get("name", ""), "arguments": t.get("function", "").get("arguments", "")}
            for t in response_tool_calls
        ]

        assert is_arrays_matched(
            response_function_args, function_args
        ), f"Function calls do not match the generated completion for completion {self._completion_id}."
