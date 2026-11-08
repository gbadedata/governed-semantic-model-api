"""Fabric backend: runs the approved DAX queries against a Fabric / Power BI semantic model
through the Power BI Execute Queries REST API, authenticating as a Microsoft Entra service principal.

See docs/decisions/0001-rest-over-xmla.md for why this API is used rather than XMLA.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from .. import dax
from .base import (
    BackendError,
    CategorySales,
    DateRange,
    ProductSales,
    RevenueSummary,
    UpstreamAuthError,
    UpstreamThrottled,
)

TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
POWER_BI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"
EXECUTE_QUERIES_URL = (
    "https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/datasets/{dataset_id}/executeQueries"
)
TOKEN_REFRESH_MARGIN_SECONDS = 120


@dataclass(frozen=True)
class FabricCredentials:
    tenant_id: str
    client_id: str
    client_secret: str

    def __repr__(self) -> str:  # never print the secret
        return f"FabricCredentials(tenant_id={self.tenant_id!r}, client_id={self.client_id!r}, client_secret=***)"


def _column(row: dict[str, Any], name: str) -> Any:
    """Read a column from an Execute Queries row.

    Keys look like '[revenue]' for named columns and "dim_products[product_name]" for model columns.
    """
    suffix = f"[{name}]"
    for key, value in row.items():
        if key == suffix or key.endswith(suffix):
            return value
    raise BackendError(f"semantic model response is missing column {name!r}")


def _money(value: Any) -> float:
    return round(float(value or 0), 2)


class FabricBackend:
    name = "fabric-semantic-model"

    def __init__(
        self,
        workspace_id: str,
        dataset_id: str,
        credentials: FabricCredentials,
        client: httpx.Client | None = None,
        timeout: float = 20.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._url = EXECUTE_QUERIES_URL.format(workspace_id=workspace_id, dataset_id=dataset_id)
        self._credentials = credentials
        self._client = client or httpx.Client(timeout=timeout)
        self._clock = clock
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._lock = threading.Lock()

    # ---------------- auth ----------------
    def _access_token(self, force_refresh: bool = False) -> str:
        with self._lock:
            if not force_refresh and self._token and self._clock() < self._token_expires_at:
                return self._token
            c = self._credentials
            try:
                resp = self._client.post(
                    TOKEN_URL.format(tenant_id=c.tenant_id),
                    data={
                        "grant_type": "client_credentials",
                        "client_id": c.client_id,
                        "client_secret": c.client_secret,
                        "scope": POWER_BI_SCOPE,
                    },
                )
            except httpx.HTTPError as exc:
                raise BackendError(f"token request failed: {type(exc).__name__}") from exc
            if resp.status_code != 200:
                raise UpstreamAuthError(f"token request rejected with HTTP {resp.status_code}")
            body = resp.json()
            self._token = body["access_token"]
            lifetime = int(body.get("expires_in", 3600))
            self._token_expires_at = self._clock() + max(lifetime - TOKEN_REFRESH_MARGIN_SECONDS, 0)
            return self._token

    # ---------------- queries ----------------
    def _execute(self, query: str) -> list[dict[str, Any]]:
        payload = {"queries": [{"query": query}], "serializerSettings": {"includeNulls": True}}
        for attempt in (1, 2):
            token = self._access_token(force_refresh=attempt == 2)
            try:
                resp = self._client.post(self._url, json=payload, headers={"Authorization": f"Bearer {token}"})
            except httpx.HTTPError as exc:
                raise BackendError(f"semantic model request failed: {type(exc).__name__}") from exc
            if resp.status_code == 401 and attempt == 1:
                continue  # token revoked or expired early: refresh once and retry
            break
        if resp.status_code == 401:
            raise UpstreamAuthError("semantic model rejected the service principal (HTTP 401)")
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After")
            raise UpstreamThrottled(
                "semantic model is throttling requests",
                retry_after=int(retry_after) if retry_after and retry_after.isdigit() else None,
            )
        if resp.status_code != 200:
            raise BackendError(f"semantic model returned HTTP {resp.status_code}")
        try:
            result = resp.json()["results"][0]
        except (ValueError, KeyError, IndexError) as exc:
            raise BackendError("semantic model returned an unexpected response") from exc
        if "error" in result:
            raise BackendError("semantic model reported a query error")
        tables = result.get("tables") or [{}]
        return tables[0].get("rows", [])

    # ---------------- measures ----------------
    def revenue_summary(self, period: DateRange) -> RevenueSummary:
        rows = self._execute(dax.revenue_summary(period))
        if not rows:  # no qualifying orders in the period
            return RevenueSummary(total_revenue=0.0, total_orders=0, average_order_value=None)
        row = rows[0]
        aov = _column(row, "average_order_value")
        return RevenueSummary(
            total_revenue=_money(_column(row, "total_revenue")),
            total_orders=int(_column(row, "total_orders") or 0),
            average_order_value=None if aov is None else _money(aov),
        )

    def sales_by_category(self, period: DateRange) -> list[CategorySales]:
        rows = self._execute(dax.sales_by_category(period))
        return [
            CategorySales(category=_column(r, "product_category"), revenue=_money(_column(r, "revenue")))
            for r in rows
            if _column(r, "revenue") is not None
        ]

    def top_products(self, period: DateRange, limit: int) -> list[ProductSales]:
        rows = self._execute(dax.top_products(period, limit))
        return [
            ProductSales(
                product_id=_column(r, "product_id"),
                product_name=_column(r, "product_name"),
                category=_column(r, "product_category"),
                revenue=_money(_column(r, "revenue")),
            )
            for r in rows
            if _column(r, "revenue") is not None
        ][:limit]

    def check(self) -> None:
        self._execute(dax.HEALTH_CHECK)
