from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from semantic_api.app import create_app
from semantic_api.backends.base import DateRange
from semantic_api.backends.local import LocalBackend
from semantic_api.config import DEFAULT_SAMPLE_DIR, Settings

FULL = DateRange(date(2025, 1, 1), date(2025, 3, 31))
JANUARY = DateRange(date(2025, 1, 1), date(2025, 1, 31))


@pytest.fixture(scope="session")
def local_backend() -> LocalBackend:
    return LocalBackend(DEFAULT_SAMPLE_DIR)


@pytest.fixture(scope="session")
def client(local_backend) -> TestClient:
    return TestClient(create_app(Settings(backend="local"), backend=local_backend))


@pytest.fixture(scope="session")
def expected_lines() -> pd.DataFrame:
    """Revenue lines computed independently with pandas, straight from the contract's rules."""
    d = DEFAULT_SAMPLE_DIR
    orders = pd.read_csv(d / "fact_orders.csv", parse_dates=["order_date"])
    items = pd.read_csv(d / "fact_order_items.csv")
    payments = pd.read_csv(d / "fact_payments.csv")
    products = pd.read_csv(d / "dim_products.csv")
    paid = set(payments.loc[payments["payment_status"] == "Paid", "order_id"])
    ok = orders[orders["order_status"].isin(["Completed", "Delivered"]) & orders["order_id"].isin(paid)]
    return ok.merge(items, on="order_id").merge(products, on="product_id")


def in_period(lines: pd.DataFrame, period: DateRange) -> pd.DataFrame:
    return lines[(lines["order_date"].dt.date >= period.start) & (lines["order_date"].dt.date <= period.end)]
