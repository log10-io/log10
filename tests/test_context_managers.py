import asyncio
import contextvars
import uuid
import pytest

session_id_var = contextvars.ContextVar("session_id", default=str(uuid.uuid4()))


class ExampleSession:
    def __init__(self):
        # print("Initializing the context...")
        pass

    def __enter__(self):
        self.token = session_id_var.set(str(uuid.uuid4()))

    def __exit__(self, exc_type, exc_value, exc_tb):
        session_id_var.reset(self.token)

    async def __aenter__(self):
        self.token = session_id_var.set(str(uuid.uuid4()))

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        session_id_var.reset(self.token)


def simulated_llm_call():
    session = session_id_var.get()
    print(f"LLM call {session}")
    return session


async def simulated_llm_acall(run_time=0.1):
    await asyncio.sleep(run_time)  # Simulate async work
    session = session_id_var.get()
    print(f"Async LLM call {session}")
    return session


def test_nested_contexts():
    before_outer_session = simulated_llm_call()
    with ExampleSession():
        before_inner_session = simulated_llm_call()

        with ExampleSession():
            inner_session = simulated_llm_call()

            assert inner_session != before_inner_session
            assert inner_session != before_outer_session

        assert simulated_llm_call() == before_inner_session

    assert simulated_llm_call() == before_outer_session


@pytest.mark.asyncio
async def test_nested_async_contexts():
    print("")
    before_outer_session = await simulated_llm_acall()
    async with ExampleSession():
        before_inner_session = await simulated_llm_acall()

        async with ExampleSession():
            inner_session = await simulated_llm_acall()

            assert inner_session != before_inner_session
            assert inner_session != before_outer_session

        assert await simulated_llm_acall() == before_inner_session

    assert await simulated_llm_acall() == before_outer_session


asyncio.run(test_nested_async_contexts())


# Test overlapping async context managers
@pytest.mark.asyncio
async def test_overlapping_async_contexts():
    # Run two async context managers in parallel
    # The second one should not overwrite the session ID of the first one
    # Simulate the first session starts before the other, and doesn't finish before the other starts
    async def run_session(delay=0.0, run_time=0.1):
        async with ExampleSession():
            session_before = session_id_var.get()
            await asyncio.sleep(delay)
            session = await simulated_llm_acall(run_time)
            assert session == session_before

    await asyncio.gather(run_session(delay=0, run_time=3), run_session(delay=1, run_time=1))


asyncio.run(test_overlapping_async_contexts())
