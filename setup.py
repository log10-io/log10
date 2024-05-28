#!/usr/bin/env python

from distutils.core import setup

from setuptools import find_packages, setup


setup(
    name="Log10",
    version="0.8.5",
    description="Log10 LLM data management",
    author="Log10 team",
    author_email="team@log10.io",
    url="",
    packages=find_packages(),
    install_requires=[
        "openai",
        "python-dotenv",
    ],
    extras_require={
        "bigquery": ["google-cloud-bigquery"],
        "dev": ["chromadb"],
    },
)
