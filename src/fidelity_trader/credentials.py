"""Credential providers for Fidelity authentication.

Supports multiple backends:
- AWS Secrets Manager (default)
- AWS SSM Parameter Store
- Environment variables
- JSON file
- Direct (for testing)

Usage:
    from fidelity_trader.credentials import SecretsManagerProvider, EnvProvider

    # AWS Secrets Manager
    creds = SecretsManagerProvider(secret_name="fidelity/trader").get_credentials()

    # Environment variables
    creds = EnvProvider().get_credentials()

    # With FidelityClient
    client = FidelityClient()
    creds = SecretsManagerProvider(secret_name="fidelity/trader").get_credentials()
    client.login(**creds)
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Credentials:
    username: str
    password: str
    totp_secret: Optional[str] = None


class CredentialProvider(ABC):
    """Base class for credential providers."""

    @abstractmethod
    def get_credentials(self) -> Credentials:
        """Return username and password."""
        ...


class SecretsManagerProvider(CredentialProvider):
    """Load credentials from AWS Secrets Manager.

    Supports two modes:
    1. Single JSON secret with "username" and "password" keys
    2. Separate secrets for each field (username_secret, password_secret)
    """

    def __init__(
        self,
        secret_name: str = None,
        username_secret: str = "fidelity/username",
        password_secret: str = "fidelity/password",
        totp_secret_name: str = "fidelity/totp_secret",
        region_name: str = "us-east-1",
    ) -> None:
        self.secret_name = secret_name
        self.username_secret = username_secret
        self.password_secret = password_secret
        self.totp_secret_name = totp_secret_name
        self.region_name = region_name

    def _get_secret(self, client, secret_id: str) -> str:
        resp = client.get_secret_value(SecretId=secret_id)
        return resp["SecretString"]

    def get_credentials(self) -> Credentials:
        import boto3

        client = boto3.client("secretsmanager", region_name=self.region_name)

        if self.secret_name:
            # Single JSON secret mode
            secret = json.loads(self._get_secret(client, self.secret_name))
            return Credentials(
                username=secret["username"],
                password=secret["password"],
            )

        # Separate secrets mode
        username = self._get_secret(client, self.username_secret)
        password = self._get_secret(client, self.password_secret)
        totp_secret = None
        if self.totp_secret_name:
            try:
                totp_secret = self._get_secret(client, self.totp_secret_name)
            except Exception:
                pass  # TOTP is optional
        return Credentials(username=username, password=password, totp_secret=totp_secret)


class SSMParameterProvider(CredentialProvider):
    """Load credentials from AWS SSM Parameter Store.

    Expects two SecureString parameters:
    - {prefix}/username
    - {prefix}/password
    """

    def __init__(
        self,
        prefix: str = "/fidelity/trader",
        region_name: str = "us-east-1",
    ) -> None:
        self.prefix = prefix.rstrip("/")
        self.region_name = region_name

    def get_credentials(self) -> Credentials:
        import boto3

        client = boto3.client("ssm", region_name=self.region_name)

        username = client.get_parameter(
            Name=f"{self.prefix}/username", WithDecryption=True
        )["Parameter"]["Value"]

        password = client.get_parameter(
            Name=f"{self.prefix}/password", WithDecryption=True
        )["Parameter"]["Value"]

        return Credentials(username=username, password=password)


class EnvProvider(CredentialProvider):
    """Load credentials from environment variables."""

    def __init__(
        self,
        username_var: str = "FIDELITY_USERNAME",
        password_var: str = "FIDELITY_PASSWORD",
    ) -> None:
        self.username_var = username_var
        self.password_var = password_var

    def get_credentials(self) -> Credentials:
        username = os.environ.get(self.username_var)
        password = os.environ.get(self.password_var)
        if not username or not password:
            missing = []
            if not username:
                missing.append(self.username_var)
            if not password:
                missing.append(self.password_var)
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")
        return Credentials(username=username, password=password)


class FileProvider(CredentialProvider):
    """Load credentials from a JSON file.

    File format: {"username": "...", "password": "..."}
    """

    def __init__(self, path: str = "credentials.json") -> None:
        self.path = Path(path)

    def get_credentials(self) -> Credentials:
        if not self.path.exists():
            raise FileNotFoundError(f"Credentials file not found: {self.path}")
        data = json.loads(self.path.read_text())
        return Credentials(
            username=data["username"],
            password=data["password"],
        )


class DirectProvider(CredentialProvider):
    """Provide credentials directly. For testing or scripting."""

    def __init__(self, username: str, password: str) -> None:
        self._creds = Credentials(username=username, password=password)

    def get_credentials(self) -> Credentials:
        return self._creds
