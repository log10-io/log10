import pytest

from log10.load import log10_session


def pytest_addoption(parser):
    parser.addoption("--openai_model", action="store", help="Model name for OpenAI tests")

    parser.addoption("--openai_vision_model", action="store", help="Model name for OpenAI vision tests")

    parser.addoption("--anthropic_model", action="store", help="Model name for Message API Anthropic tests")

    parser.addoption("--anthropic_legacy_model", action="store", help="Model name for legacy Anthropic tests")

    parser.addoption(
        "--mistralai_model", action="store", default="mistral-tiny", help="Model name for Mistralai tests"
    )

    parser.addoption("--google_model", action="store", help="Model name for Google tests")

    parser.addoption("--llm_provider", action="store", help="Model provider name for Magentic tests")

    parser.addoption(
        "--openai_compatibility_model",
        action="store",
        help="Model name for client compatibility model in Magentic tests",
    )


@pytest.fixture
def openai_model(request):
    return request.config.getoption("--openai_model")


@pytest.fixture
def openai_vision_model(request):
    return request.config.getoption("--openai_vision_model")


@pytest.fixture
def anthropic_model(request):
    return request.config.getoption("--anthropic_model")


@pytest.fixture
def anthropic_legacy_model(request):
    return request.config.getoption("--anthropic_legacy_model")


@pytest.fixture
def mistralai_model(request):
    return request.config.getoption("--mistralai_model")


@pytest.fixture
def google_model(request):
    return request.config.getoption("--google_model")


@pytest.fixture
def llm_provider(request):
    return request.config.getoption("--llm_provider")


@pytest.fixture
def magentic_models(request):
    llm_provider = request.config.getoption("--llm_provider")
    model_configs_to_providers = {
        "openai": ["openai_model", "openai_vision_model"],
        "anthropic": ["anthropic_model", "anthropic_model"],
        "litellm": ["openai_compatibility_model", "openai_compatibility_model"],
    }

    model_configs = model_configs_to_providers[llm_provider]

    return {
        "chat_model": request.config.getoption(model_configs[0]),
        "vision_model": request.config.getoption(model_configs[1]),
    }


@pytest.fixture
def openai_compatibility_model(request):
    return request.config.getoption("--openai_compatibility_model")


@pytest.fixture
def session():
    with log10_session() as session:
        assert session.last_completion_id() is None, "No completion ID should be found."
        yield session
