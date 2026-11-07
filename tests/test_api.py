import pytest
from fastapi.testclient import TestClient

from semantic_api.app import create_app
from semantic_api.backends.base import BackendError, UpstreamThrottled
from semantic_api.config import Settings

Q = "start_date=2025-01-01&end_date=2025-03-31"


def test_health_is_shallow_by_default(client):
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["upstream"] == "unknown" and body["backend"] == "local-sample"


def test_deep_health_checks_the_backend(client):
    assert client.get("/v1/health?deep=true").json()["upstream"] == "ok"


def test_measures_endpoint_publishes_the_catalogue(client):
    keys = {m["key"] for m in client.get("/v1/measures").json()}
    assert keys == {"total_revenue", "total_orders", "average_order_value"}


def test_revenue(client, local_backend):
    from .conftest import FULL

    body = client.get(f"/v1/metrics/revenue?{Q}").json()
    s = local_backend.revenue_summary(FULL)
    assert body["total_revenue"] == s.total_revenue and body["total_orders"] == s.total_orders
    assert body["currency"] == "USD" and body["period"] == {"start_date": "2025-01-01", "end_date": "2025-03-31"}


def test_sales_by_category(client):
    body = client.get(f"/v1/metrics/sales-by-category?{Q}").json()
    assert body["measure"] == "total_revenue"
    assert {c["category"] for c in body["categories"]} == {"Furniture", "Electronics", "Accessories", "Office Supplies"}


def test_top_products_ranks_and_limits(client):
    body = client.get(f"/v1/metrics/top-products?{Q}&limit=2").json()
    assert [p["rank"] for p in body["products"]] == [1, 2] and body["limit"] == 2
    assert client.get(f"/v1/metrics/top-products?{Q}").json()["limit"] == 5


@pytest.mark.parametrize(
    "query, status, fragment",
    [
        ("start_date=2025-03-01&end_date=2025-01-01", 422, "on or after"),
        ("start_date=2024-01-01&end_date=2025-12-31", 422, "limited to 366 days"),
        ("start_date=not-a-date&end_date=2025-01-31", 422, "invalid"),
        ("end_date=2025-01-31", 422, "invalid"),
        (f"{Q}&region=north", 400, "unsupported query parameter"),
    ],
)
def test_invalid_requests_get_the_standard_error_body(client, query, status, fragment):
    r = client.get(f"/v1/metrics/revenue?{query}")
    assert r.status_code == status
    err = r.json()["error"]
    assert err["code"] == "invalid_request" and fragment in err["message"].lower() and err["request_id"]


@pytest.mark.parametrize("limit", [0, 51, "ten"])
def test_top_products_limit_is_bounded(client, limit):
    assert client.get(f"/v1/metrics/top-products?{Q}&limit={limit}").status_code == 422


def test_limit_is_not_accepted_on_other_endpoints(client):
    assert client.get(f"/v1/metrics/revenue?{Q}&limit=3").status_code == 400


def test_request_id_is_echoed_or_generated(client):
    assert client.get("/v1/health", headers={"X-Request-ID": "abc-123"}).headers["X-Request-ID"] == "abc-123"
    generated = client.get("/v1/health", headers={"X-Request-ID": "bad id with spaces"}).headers["X-Request-ID"]
    assert generated != "bad id with spaces" and len(generated) == 32


class FailingBackend:
    name = "failing"

    def __init__(self, exc):
        self.exc = exc

    def revenue_summary(self, period):
        raise self.exc

    sales_by_category = revenue_summary

    def top_products(self, period, limit):
        raise self.exc

    def check(self):
        raise self.exc


def test_upstream_errors_become_502_without_leaking_detail():
    c = TestClient(create_app(Settings(), backend=FailingBackend(BackendError("secret internal detail"))))
    r = c.get(f"/v1/metrics/revenue?{Q}")
    assert r.status_code == 502 and r.json()["error"]["code"] == "upstream_error"
    assert "secret internal detail" not in r.text


def test_throttling_becomes_503_with_retry_after():
    c = TestClient(create_app(Settings(), backend=FailingBackend(UpstreamThrottled("slow down", retry_after=30))))
    r = c.get(f"/v1/metrics/sales-by-category?{Q}")
    assert r.status_code == 503 and r.headers["Retry-After"] == "30"


def test_deep_health_reports_upstream_failure():
    c = TestClient(create_app(Settings(), backend=FailingBackend(BackendError("down"))))
    assert c.get("/v1/health").status_code == 200
    assert c.get("/v1/health?deep=true").status_code == 502


def test_requests_are_logged_as_json(client):
    import io
    import json
    import logging

    from semantic_api.logging_config import LOGGER_NAME, JsonFormatter

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger(LOGGER_NAME)
    logger.addHandler(handler)
    try:
        client.get("/v1/health", headers={"X-Request-ID": "log-check"})
    finally:
        logger.removeHandler(handler)
    entry = json.loads(stream.getvalue().splitlines()[-1])
    assert entry["request_id"] == "log-check" and entry["path"] == "/v1/health"
    assert entry["status"] == 200 and "duration_ms" in entry and entry["level"] == "INFO"
