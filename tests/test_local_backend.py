from datetime import date

import pytest

from semantic_api.backends.base import ConfigError, DateRange
from semantic_api.backends.local import LocalBackend

from .conftest import FULL, JANUARY, in_period


@pytest.mark.parametrize("period", [FULL, JANUARY], ids=["full", "january"])
def test_revenue_summary_matches_independent_calculation(local_backend, expected_lines, period):
    lines = in_period(expected_lines, period)
    revenue = round(lines["item_total"].sum(), 2)
    orders = lines["order_id"].nunique()
    s = local_backend.revenue_summary(period)
    assert s.total_revenue == pytest.approx(revenue)
    assert s.total_orders == orders
    assert s.average_order_value == pytest.approx(round(revenue / orders, 2))


def test_cancelled_and_unpaid_orders_are_excluded(local_backend, expected_lines):
    # 80 orders in the sample, 11 cancelled (all with failed or refunded payments)
    assert local_backend.revenue_summary(FULL).total_orders == 69 == expected_lines["order_id"].nunique()


def test_sales_by_category_sums_to_total_revenue(local_backend, expected_lines):
    rows = local_backend.sales_by_category(FULL)
    expected = expected_lines.groupby("product_category")["item_total"].sum().round(2)
    assert {r.category: r.revenue for r in rows} == pytest.approx(expected.to_dict())
    assert [r.revenue for r in rows] == sorted((r.revenue for r in rows), reverse=True)
    assert sum(r.revenue for r in rows) == pytest.approx(local_backend.revenue_summary(FULL).total_revenue)


def test_top_products_are_ranked_and_limited(local_backend, expected_lines):
    rows = local_backend.top_products(FULL, 3)
    expected = expected_lines.groupby("product_id")["item_total"].sum().nlargest(3).round(2)
    assert [r.product_id for r in rows] == list(expected.index)
    assert [r.revenue for r in rows] == pytest.approx(list(expected))


def test_period_with_no_orders_returns_zero_and_null_average(local_backend):
    empty = DateRange(date(2024, 1, 1), date(2024, 1, 31))
    s = local_backend.revenue_summary(empty)
    assert (s.total_revenue, s.total_orders, s.average_order_value) == (0.0, 0, None)
    assert local_backend.sales_by_category(empty) == []
    assert local_backend.top_products(empty, 5) == []


def test_missing_sample_data_fails_at_startup(tmp_path):
    with pytest.raises(ConfigError, match="dim_customers"):
        LocalBackend(tmp_path)


def test_date_range_rejects_reversed_dates():
    with pytest.raises(ValueError):
        DateRange(date(2025, 2, 1), date(2025, 1, 1))
    assert DateRange(date(2025, 1, 1), date(2025, 1, 1)).days == 1
