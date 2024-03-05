"""
This module provides a class for managing secrets.
A secret is a key value pair that comes from the enviornment 
"""

import os
from dotenv import load_dotenv


class SecretsManager:
    """
    A class for managing secrets.
    Override this to work with other secret vaults.
    """

    def __init__(self, env_file=".env"):
        self.env: dict[str, str] = {
            **os.environ,
            **load_dotenv(env_file),  # override what's in os.environ with .env
        }

    @staticmethod
    def get_default() -> "SecretsManager":
        """Return the default secrets manager."""
        return _DEFAULT_SECRETS_MANAGER

    def __getitem__(self, key: str) -> str:
        """Return the value of the given key."""
        return self.env.get(key, None)

    def __setitem__(self, key: str, value: str) -> None:
        """Set the value of the given key."""
        self.env[key] = value


_DEFAULT_SECRETS_MANAGER = SecretsManager()
