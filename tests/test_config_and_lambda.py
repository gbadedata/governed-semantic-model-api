import json
import re
import tomllib
from pathlib import Path

import pytest

from semantic_api.app import build_backend
from semantic_api.backends.base import ConfigError
from semantic_api.backends.fabric import FabricBackend
from semantic_api.config import Settings
from semantic_api.secrets import load_fabric_credentials

ROOT = Path(__file__).resolve().parents[1]
ARN = "arn:aws:secretsmanager:eu-west-2:123456789012:secret:fabric-sp"


class FakeSecrets:
    def __init__(self, payload):
        self.payload = payload
        self.asked_for = None

    def get_secret_value(self, SecretId):  # noqa: N803 - boto3's parameter name
        self.asked_for = SecretId
        return {"SecretString": json.dumps(self.payload)}


def test_credentials_from_secrets_manager():
    fake = FakeSecrets({"tenant_id": "t", "client_id": "c", "client_secret": "s"})
    creds = load_fabric_credentials(Settings(fabric_secret_arn=ARN), secrets_client=fake)
    assert fake.asked_for == ARN and (creds.tenant_id, creds.client_secret) == ("t", "s")


def test_incomplete_secret_is_a_config_error():
    with pytest.raises(ConfigError, match="client_secret"):
        load_fabric_credentials(Settings(fabric_secret_arn=ARN), FakeSecrets({"tenant_id": "t", "client_id": "c"}))


def test_credentials_from_environment_settings():
    s = Settings(fabric_tenant_id="t", fabric_client_id="c", fabric_client_secret="s")
    assert load_fabric_credentials(s).client_id == "c"


def test_missing_credentials_name_the_variables():
    with pytest.raises(ConfigError, match="SEMANTIC_API_FABRIC_CLIENT_SECRET"):
        load_fabric_credentials(Settings(fabric_tenant_id="t", fabric_client_id="c"))


def test_fabric_backend_needs_workspace_and_dataset():
    with pytest.raises(ConfigError, match="WORKSPACE_ID"):
        build_backend(Settings(backend="fabric"))
    s = Settings(backend="fabric", fabric_workspace_id="w", fabric_dataset_id="d", fabric_tenant_id="t",
                 fabric_client_id="c", fabric_client_secret="s")
    assert isinstance(build_backend(s), FabricBackend)


def test_lambda_handler_serves_an_http_api_event(monkeypatch):
    monkeypatch.setenv("SEMANTIC_API_BACKEND", "local")
    from semantic_api.config import get_settings

    get_settings.cache_clear()
    from semantic_api.lambda_handler import handler

    event = {
        "version": "2.0", "routeKey": "GET /v1/health", "rawPath": "/v1/health", "rawQueryString": "",
        "headers": {"host": "example.execute-api.eu-west-2.amazonaws.com"},
        "requestContext": {"http": {"method": "GET", "path": "/v1/health", "sourceIp": "203.0.113.1",
                                    "protocol": "HTTP/1.1"},
                           "requestId": "apigw-req-1", "stage": "$default"},
        "isBase64Encoded": False,
    }
    response = handler(event, None)
    assert response["statusCode"] == 200
    assert json.loads(response["body"])["status"] == "ok"
    assert response["headers"]["x-request-id"] == "apigw-req-1"


def test_lambda_requirements_match_project_dependencies():
    declared = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["dependencies"]
    lines = (ROOT / "src" / "requirements.txt").read_text().splitlines()
    pinned = [ln.strip() for ln in lines if ln.strip() and not ln.startswith("#")]
    assert sorted(pinned) == sorted(declared)


def test_dax_measures_file_defines_every_catalogued_measure():
    from semantic_api.measures import CATALOGUE

    text = (ROOT / "semantic_model" / "measures.dax").read_text()
    defined = set(re.findall(r"^\s*MEASURE\s+fact_orders\[(.+?)\]\s*=", text, flags=re.MULTILINE))
    assert defined == {m.dax_name for m in CATALOGUE.values()}
