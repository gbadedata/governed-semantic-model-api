from datetime import date

import pytest

from semantic_api import dax
from semantic_api.backends.base import DateRange
from semantic_api.measures import CATALOGUE

P = DateRange(date(2025, 1, 5), date(2025, 2, 28))


def test_period_filter_uses_order_dates_through_dim_date():
    q = dax.revenue_summary(P)
    assert "'dim_date'[full_date] >= DATE(2025, 1, 5)" in q
    assert "'dim_date'[full_date] <= DATE(2025, 2, 28)" in q


def test_revenue_summary_requests_every_catalogued_measure():
    q = dax.revenue_summary(P)
    for m in CATALOGUE.values():
        assert f'"{m.key}", [{m.dax_name}]' in q


def test_category_and_product_queries_use_total_revenue():
    assert "[Total Revenue]" in dax.sales_by_category(P)
    q = dax.top_products(P, 7)
    assert "TOPN(7," in q and "[Total Revenue]" in q


@pytest.mark.parametrize("bad", [0, -1, "5; EVALUATE x", True, 2.5])
def test_top_products_only_accepts_positive_integers(bad):
    with pytest.raises(ValueError):
        dax.top_products(P, bad)
