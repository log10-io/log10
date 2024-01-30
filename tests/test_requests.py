import asyncio
import uuid

import httpx
import pytest
import requests_mock

from log10.load import log_sync, log_async, OpenAI, log10_session
from log10.llm import LLM, Log10Config


def test_log_sync_500():
    payload = {'abc': '123'}
    url = 'https://log10.io/api/completions'

    with requests_mock.Mocker() as m:
        m.post(url, status_code=500)
        log_sync(url, payload)


@pytest.mark.asyncio
async def test_log_async_500():
    payload = {'abc': '123'}
    url = 'https://log10.io/api/completions'

    with requests_mock.Mocker() as m:
        m.post(url, status_code=500)
        await log_async(url, payload)


@pytest.mark.skip(reason="This is a very simple load test and doesn't need to be run as part of the test suite.")
@pytest.mark.asyncio
async def test_log_async_multiple_calls():
    simultaneous_calls = 100
    url = 'https://log10.io/api/completions'

    mock_resp = {
            "role": "user",
            "content": "Say this is a test",
    }

    log10_config = Log10Config()
    loop = asyncio.get_event_loop()

    def fake_logging():
        llm = LLM(log10_config=log10_config)
        completion_id = llm.log_start(url, kind="chat")
        print(completion_id)
        llm.log_end(completion_id=completion_id, response=mock_resp, duration=5)

    await asyncio.gather(*[loop.run_in_executor(None, fake_logging) for _ in range(simultaneous_calls)])


@pytest.mark.skip(reason="This is a very simple load test and doesn't need to be run as part of the test suite.")
@pytest.mark.asyncio
async def test_log_async_httpx_multiple_calls_with_tags(respx_mock):
    simultaneous_calls = 100

    mock_resp = {
        "role": "user",
        "content": "Say this is a test",
    }

    client = OpenAI()

    respx_mock.post("https://api.openai.com/v1/chat/completions").mock(return_value=httpx.Response(200, json=mock_resp))

    def better_logging():
        uuids = [str(uuid.uuid4()) for _ in range(5)]
        with log10_session(tags=uuids) as s:
            completion = client.chat.completions.create(model="gpt-3.5-turbo", messages=[
                {"role": "user", "content": "Say pong"}])

    loop = asyncio.get_event_loop()
    await asyncio.gather(*[loop.run_in_executor(None, better_logging) for _ in range(simultaneous_calls)])
