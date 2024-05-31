from distutils.core import setup

from setuptools import setup

setup(
    name="Log10",
	@@ -12,13 +11,35 @@
    author="Log10 team",
    author_email="team@log10.io",
    url="",
    packages=[
        "log10",
    ],
    install_requires=[
        "openai<2",
        "anthropic<1",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "backoff>=2.2.1",
        "pandas>=2",
    ],
    extras_require={
        "autofeedback_icl": ["magentic>=0.17.0; python_version >= '3.10'"],
        "litellm": ["litellm>=1.34.18"],
        "langchain": ["langchain<0.2.0"],
        "gemini": ["google-cloud-aiplatform>=1.44.0"],
        "mistralai": ["mistralai>=0.1.5"],
        "together": ["together>=0.2.7"],
        "mosaicml": ["mosaicml-cli>=0.5.30"],
        "google-generativeai": ["google-generativeai>=0.5.2"],
        "bigquery": ["google-cloud-bigquery>=3.11.4"],
        "dev": [
            "build>=0.10.0",
            "pytest>=8.0.0",
            "requests-mock>=1.11.0",
            "respx>=0.20.2",
            "ruff>=0.3.2",
            "pytest-asyncio>=0.23.6",
            "chromadb"
        ],
    },
)