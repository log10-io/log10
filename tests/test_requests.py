import asyncio

import pytest
import requests_mock

from log10.load import log_sync, log_async
from log10.llm import LLM, Log10Config


def test_log_sync_500():
    payload = {'abc': '123'}
    url = 'https://log10.io/api/completions'

    with pytest.raises(Exception) as e:
        with requests_mock.Mocker() as m:
            m.post(url, status_code=500)
            log_sync(url, payload)


@pytest.mark.asyncio
async def test_log_async_500():
    payload = {'abc': '123'}
    url = 'https://log10.io/api/completions'

    with pytest.raises(Exception) as e:
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