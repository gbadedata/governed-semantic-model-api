"""Load the Fabric service-principal credentials.

In AWS the credentials live in Secrets Manager (a JSON secret with tenant_id, client_id and
client_secret) and are read once per Lambda container. Locally they can come from environment
variables instead. The secret value is never logged.
"""

from __future__ import annotations

import json
from typing import Any

from .backends.base import ConfigError
from .backends.fabric import FabricCredentials
from .config import Settings

REQUIRED_KEYS = ("tenant_id", "client_id", "client_secret")


def load_fabric_credentials(settings: Settings, secrets_client: Any | None = None) -> FabricCredentials:
    if settings.fabric_secret_arn:
        if secrets_client is None:
            try:
                import boto3  # provided by the Lambda runtime; optional locally
            except ImportError as exc:  # pragma: no cover - depends on environment
                raise ConfigError("boto3 is required to read credentials from Secrets Manager") from exc
            secrets_client = boto3.client("secretsmanager")
        try:
            raw = secrets_client.get_secret_value(SecretId=settings.fabric_secret_arn)["SecretString"]
            values = json.loads(raw)
        except Exception as exc:
            raise ConfigError(f"could not read the Fabric credentials secret: {type(exc).__name__}") from exc
        missing = [k for k in REQUIRED_KEYS if not values.get(k)]
        if missing:
            raise ConfigError(f"Fabric credentials secret is missing: {', '.join(missing)}")
        return FabricCredentials(values["tenant_id"], values["client_id"], values["client_secret"])

    secret = settings.fabric_client_secret.get_secret_value() if settings.fabric_client_secret else None
    values = {"tenant_id": settings.fabric_tenant_id, "client_id": settings.fabric_client_id, "client_secret": secret}
    missing = [k for k, v in values.items() if not v]
    if missing:
        raise ConfigError(
            "Fabric credentials not configured: set SEMANTIC_API_FABRIC_SECRET_ARN, or "
            + ", ".join(f"SEMANTIC_API_FABRIC_{k.upper()}" for k in missing)
        )
    return FabricCredentials(**values)
