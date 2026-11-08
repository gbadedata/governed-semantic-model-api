"""The interface every semantic backend implements, plus shared result types and errors."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("end_date must be on or after start_date")

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


@dataclass(frozen=True)
class RevenueSummary:
    total_revenue: float
    total_orders: int
    average_order_value: float | None


@dataclass(frozen=True)
class CategorySales:
    category: str
    revenue: float


@dataclass(frozen=True)
class ProductSales:
    product_id: str
    product_name: str
    category: str
    revenue: float


class BackendError(Exception):
    """The semantic backend could not answer. Mapped to 502 by the API."""

    code = "upstream_error"
    status_code = 502

    def __init__(self, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class UpstreamAuthError(BackendError):
    code = "upstream_auth_failed"


class UpstreamThrottled(BackendError):
    code = "upstream_throttled"
    status_code = 503


class ConfigError(RuntimeError):
    """The service is misconfigured; raised at startup, never per request."""


class SemanticBackend(Protocol):
    name: str

    def revenue_summary(self, period: DateRange) -> RevenueSummary: ...

    def sales_by_category(self, period: DateRange) -> list[CategorySales]: ...

    def top_products(self, period: DateRange, limit: int) -> list[ProductSales]: ...

    def check(self) -> None:
        """Raise BackendError if the upstream cannot be reached."""
