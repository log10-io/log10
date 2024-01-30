import pytest
import requests_mock

from log10.load import log_async, log_sync


def test_log_sync_500():
    payload = {"abc": "123"}
    url = "https://log10.io/api/completions"

    with requests_mock.Mocker() as m:
        m.post(url, status_code=500)
        log_sync(url, payload)


@pytest.mark.asyncio
async def test_log_async_500():
    payload = {"abc": "123"}
    url = "https://log10.io/api/completions"

    with requests_mock.Mocker() as m:
        m.post(url, status_code=500)
        await log_async(url, payload)
