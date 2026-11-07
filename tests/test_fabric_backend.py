"""The Fabric backend against a mocked Power BI / Entra HTTP API (no network)."""

import json

import httpx
import pytest

from semantic_api.backends.base import BackendError, UpstreamAuthError, UpstreamThrottled
from semantic_api.backends.fabric import FabricBackend, FabricCredentials

from .conftest import FULL

CREDS = FabricCredentials("tenant-1", "client-1", "s3cret")


class FakePowerBI:
    """Records requests and answers token and executeQueries calls from a script."""

    def __init__(self, query_responses, token_status=200):
        self.query_responses = list(query_responses)
        self.token_status = token_status
        self.token_calls = 0
        self.queries: list[dict] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "login.microsoftonline.com":
            self.token_calls += 1
            assert request.url.path == "/tenant-1/oauth2/v2.0/token"
            form = dict(x.split("=", 1) for x in request.content.decode().split("&"))
            assert form["grant_type"] == "client_credentials" and form["client_secret"] == "s3cret"
            if self.token_status != 200:
                return httpx.Response(self.token_status, json={"error": "invalid_client"})
            return httpx.Response(200, json={"access_token": f"token-{self.token_calls}", "expires_in": 3600})
        assert request.url.path == "/v1.0/myorg/groups/ws-1/datasets/ds-1/executeQueries"
        self.queries.append({"auth": request.headers["Authorization"], **json.loads(request.content)})
        status, body, headers = self.query_responses.pop(0)
        return httpx.Response(status, json=body, headers=headers or {})


def rows(*r):
    return (200, {"results": [{"tables": [{"rows": list(r)}]}]}, None)


def backend(fake: FakePowerBI, clock=lambda: 0.0) -> FabricBackend:
    return FabricBackend("ws-1", "ds-1", CREDS, client=httpx.Client(transport=httpx.MockTransport(fake.handler)),
                         clock=clock)


def test_revenue_summary_parses_named_columns():
    fake = FakePowerBI([rows({"[total_revenue]": 43430.951, "[total_orders]": 69, "[average_order_value]": 629.43})])
    s = backend(fake).revenue_summary(FULL)
    assert (s.total_revenue, s.total_orders, s.average_order_value) == (43430.95, 69, 629.43)
    sent = fake.queries[0]
    assert sent["auth"] == "Bearer token-1"
    assert "[Total Revenue]" in sent["queries"][0]["query"]
    assert sent["serializerSettings"] == {"includeNulls": True}


def test_empty_result_means_no_qualifying_orders():
    s = backend(FakePowerBI([rows()])).revenue_summary(FULL)
    assert (s.total_revenue, s.total_orders, s.average_order_value) == (0.0, 0, None)


def test_category_and_product_rows_parse_model_columns():
    fake = FakePowerBI([
        rows({"dim_products[product_category]": "Furniture", "[revenue]": 100.0},
             {"dim_products[product_category]": "Toys", "[revenue]": None}),
        rows({"dim_products[product_id]": "P006", "dim_products[product_name]": "Standing Desk",
              "dim_products[product_category]": "Furniture", "[revenue]": 99.999}),
    ])
    b = backend(fake)
    assert [(c.category, c.revenue) for c in b.sales_by_category(FULL)] == [("Furniture", 100.0)]
    (p,) = b.top_products(FULL, 1)
    assert (p.product_id, p.product_name, p.revenue) == ("P006", "Standing Desk", 100.0)


def test_token_is_cached_until_near_expiry():
    now = [0.0]
    fake = FakePowerBI([rows(), rows(), rows()])
    b = backend(fake, clock=lambda: now[0])
    b.sales_by_category(FULL)
    b.sales_by_category(FULL)
    assert fake.token_calls == 1
    now[0] = 3600  # past expiry minus the refresh margin
    b.sales_by_category(FULL)
    assert fake.token_calls == 2


def test_a_401_refreshes_the_token_once_then_retries():
    fake = FakePowerBI([(401, {"error": {"code": "TokenExpired"}}, None), rows()])
    backend(fake).sales_by_category(FULL)
    assert fake.token_calls == 2 and [q["auth"] for q in fake.queries] == ["Bearer token-1", "Bearer token-2"]


def test_repeated_401_is_an_auth_error():
    fake = FakePowerBI([(401, {}, None), (401, {}, None)])
    with pytest.raises(UpstreamAuthError):
        backend(fake).sales_by_category(FULL)


def test_rejected_credentials_are_an_auth_error():
    with pytest.raises(UpstreamAuthError):
        backend(FakePowerBI([], token_status=401)).sales_by_category(FULL)


def test_throttling_carries_retry_after():
    fake = FakePowerBI([(429, {}, {"Retry-After": "17"})])
    with pytest.raises(UpstreamThrottled) as exc:
        backend(fake).sales_by_category(FULL)
    assert exc.value.retry_after == 17 and exc.value.status_code == 503


@pytest.mark.parametrize(
    "response",
    [
        (500, {"error": "boom"}, None),
        (400, {"error": {"code": "DatasetExecuteQueriesError"}}, None),
        (200, {"results": [{"error": {"code": "QueryError"}}]}, None),
        (200, {"unexpected": True}, None),
        rows({"[something_else]": 1}),
    ],
    ids=["5xx", "bad-query", "result-error", "bad-shape", "missing-column"],
)
def test_upstream_failures_are_backend_errors(response):
    with pytest.raises(BackendError):
        backend(FakePowerBI([response])).revenue_summary(FULL)


def test_network_errors_are_backend_errors():
    def boom(request):
        raise httpx.ConnectError("unreachable")

    b = FabricBackend("ws-1", "ds-1", CREDS, client=httpx.Client(transport=httpx.MockTransport(boom)))
    with pytest.raises(BackendError):
        b.check()


def test_credentials_repr_hides_the_secret():
    assert "s3cret" not in repr(CREDS)
