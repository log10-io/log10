import pytest


def pytest_addoption(parser):
    parser.addoption("--openai_model", action="store", help="Model name for OpenAI tests")

    parser.addoption("--openai_vision_model", action="store", help="Model name for OpenAI vision tests")

    parser.addoption("--anthropic_model", action="store", help="Model name for Anthropic tests")

    parser.addoption("--lamini_model", action="store", help="Model name for Lamini tests")

    parser.addoption(
        "--mistralai_model", action="store", default="mistral-tiny", help="Model name for Mistralai tests"
    )

    parser.addoption("--google_model", action="store", help="Model name for Google tests")

    parser.addoption("--magnetic_model", action="store", help="Model name for Magnetic tests")


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
def mistralai_model(request):
    return request.config.getoption("--mistralai_model")


@pytest.fixture
def lamini_model(request):
    return request.config.getoption("--lamini_model")


@pytest.fixture
def google_model(request):
    return request.config.getoption("--google_model")


@pytest.fixture
def magnetic_model(request):
    return request.config.getoption("--magnetic_model")
