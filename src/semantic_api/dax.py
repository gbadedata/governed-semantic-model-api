"""DAX queries for the approved measures.

Only typed values (dates and an integer limit) are ever placed into a query; no
consumer-supplied text reaches DAX, so there is nothing to inject.
"""

from __future__ import annotations

from datetime import date

from .backends.base import DateRange
from .measures import AVERAGE_ORDER_VALUE, TOTAL_ORDERS, TOTAL_REVENUE


def _date(d: date) -> str:
    return f"DATE({d.year}, {d.month}, {d.day})"


def _period_filter(period: DateRange) -> str:
    # Date filters apply on order date through the dim_date relationship (semantic model contract).
    return (
        "VAR __period = FILTER(ALL('dim_date'[full_date]), "
        f"'dim_date'[full_date] >= {_date(period.start)} && 'dim_date'[full_date] <= {_date(period.end)})"
    )


def revenue_summary(period: DateRange) -> str:
    return (
        f"DEFINE {_period_filter(period)}\n"
        "EVALUATE SUMMARIZECOLUMNS(__period, "
        f'"{TOTAL_REVENUE.key}", [{TOTAL_REVENUE.dax_name}], '
        f'"{TOTAL_ORDERS.key}", [{TOTAL_ORDERS.dax_name}], '
        f'"{AVERAGE_ORDER_VALUE.key}", [{AVERAGE_ORDER_VALUE.dax_name}])'
    )


def sales_by_category(period: DateRange) -> str:
    return (
        f"DEFINE {_period_filter(period)}\n"
        "EVALUATE SUMMARIZECOLUMNS('dim_products'[product_category], __period, "
        f'"revenue", [{TOTAL_REVENUE.dax_name}])\n'
        "ORDER BY [revenue] DESC, 'dim_products'[product_category]"
    )


def top_products(period: DateRange, limit: int) -> str:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")
    return (
        f"DEFINE {_period_filter(period)}\n"
        f"EVALUATE TOPN({limit}, SUMMARIZECOLUMNS('dim_products'[product_id], "
        "'dim_products'[product_name], 'dim_products'[product_category], __period, "
        f'"revenue", [{TOTAL_REVENUE.dax_name}]), [revenue], DESC, \'dim_products\'[product_id], ASC)\n'
        "ORDER BY [revenue] DESC, 'dim_products'[product_id]"
    )


HEALTH_CHECK = 'EVALUATE ROW("ok", 1)'
