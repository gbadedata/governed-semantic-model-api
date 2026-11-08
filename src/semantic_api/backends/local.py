"""Local backend: answers the governed measures from the curated sample mart with DuckDB.

It stands in for the semantic model during development and testing, and implements exactly
the definitions in measures.py so its answers can be compared with the DAX measures.
"""

from __future__ import annotations

import threading
from pathlib import Path

import duckdb

from ..measures import QUALIFYING_ORDER_STATUSES, SUCCESSFUL_PAYMENT_STATUS
from .base import BackendError, CategorySales, ConfigError, DateRange, ProductSales, RevenueSummary

TABLES = ("dim_customers", "dim_date", "dim_products", "fact_orders", "fact_order_items", "fact_payments")

# One row per order item that counts towards revenue. EXISTS (rather than a join to payments)
# keeps an order with several successful payments from being counted twice.
REVENUE_LINES = f"""
CREATE VIEW revenue_lines AS
SELECT o.order_id, CAST(o.order_date AS DATE) AS order_date, i.product_id, i.item_total
FROM fact_orders AS o
JOIN fact_order_items AS i ON i.order_id = o.order_id
WHERE o.order_status IN ({", ".join(f"'{s}'" for s in QUALIFYING_ORDER_STATUSES)})
  AND EXISTS (
      SELECT 1 FROM fact_payments AS p
      WHERE p.order_id = o.order_id AND p.payment_status = '{SUCCESSFUL_PAYMENT_STATUS}'
  )
"""


class LocalBackend:
    name = "local-sample"

    def __init__(self, data_dir: Path) -> None:
        missing = [t for t in TABLES if not (data_dir / f"{t}.csv").exists()]
        if missing:
            raise ConfigError(f"sample data missing in {data_dir}: {', '.join(missing)}")
        self._con = duckdb.connect(":memory:")
        for table in TABLES:
            self._con.execute(
                f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto(?, header = true)",
                [str(data_dir / f"{table}.csv")],
            )
        self._con.execute(REVENUE_LINES)
        self._lock = threading.Lock()

    def _query(self, sql: str, params: list) -> list[tuple]:
        try:
            with self._lock:
                return self._con.execute(sql, params).fetchall()
        except duckdb.Error as exc:  # pragma: no cover - defensive
            raise BackendError(f"local query failed: {exc}") from exc

    def revenue_summary(self, period: DateRange) -> RevenueSummary:
        (revenue, orders), = self._query(
            "SELECT COALESCE(SUM(item_total), 0), COUNT(DISTINCT order_id) FROM revenue_lines "
            "WHERE order_date BETWEEN ? AND ?",
            [period.start, period.end],
        )
        revenue = round(float(revenue), 2)
        return RevenueSummary(
            total_revenue=revenue,
            total_orders=int(orders),
            average_order_value=round(revenue / orders, 2) if orders else None,
        )

    def sales_by_category(self, period: DateRange) -> list[CategorySales]:
        rows = self._query(
            "SELECT p.product_category, SUM(r.item_total) AS revenue FROM revenue_lines AS r "
            "JOIN dim_products AS p USING (product_id) WHERE r.order_date BETWEEN ? AND ? "
            "GROUP BY 1 ORDER BY revenue DESC, 1",
            [period.start, period.end],
        )
        return [CategorySales(category=c, revenue=round(float(v), 2)) for c, v in rows]

    def top_products(self, period: DateRange, limit: int) -> list[ProductSales]:
        rows = self._query(
            "SELECT p.product_id, p.product_name, p.product_category, SUM(r.item_total) AS revenue "
            "FROM revenue_lines AS r JOIN dim_products AS p USING (product_id) "
            "WHERE r.order_date BETWEEN ? AND ? GROUP BY 1, 2, 3 ORDER BY revenue DESC, 1 LIMIT ?",
            [period.start, period.end, limit],
        )
        return [
            ProductSales(product_id=i, product_name=n, category=c, revenue=round(float(v), 2))
            for i, n, c, v in rows
        ]

    def check(self) -> None:
        self._query("SELECT 1", [])
