"""The governed measure catalogue: the only metrics this API will serve.

Every endpoint answers from these definitions, and the semantic model implements the same
definitions in DAX (see semantic_model/measures.dax). Consumers cannot request anything else.
"""

from __future__ import annotations

from dataclasses import dataclass

CURRENCY = "USD"
QUALIFYING_ORDER_STATUSES = ("Completed", "Delivered")
SUCCESSFUL_PAYMENT_STATUS = "Paid"


@dataclass(frozen=True)
class Measure:
    key: str  # name used in API responses
    dax_name: str  # measure name in the semantic model
    definition: str


TOTAL_REVENUE = Measure(
    "total_revenue",
    "Total Revenue",
    "Sum of order item totals for Completed or Delivered orders that have a successful (Paid) payment, "
    "filtered by order date.",
)
TOTAL_ORDERS = Measure(
    "total_orders",
    "Total Orders",
    "Distinct count of qualifying orders (Completed or Delivered, with a Paid payment), filtered by order date.",
)
AVERAGE_ORDER_VALUE = Measure(
    "average_order_value",
    "Average Order Value",
    "Total Revenue divided by Total Orders; null when there are no qualifying orders.",
)

CATALOGUE: dict[str, Measure] = {m.key: m for m in (TOTAL_REVENUE, TOTAL_ORDERS, AVERAGE_ORDER_VALUE)}

# The only query parameters each endpoint accepts. Anything else is rejected.
DATE_FILTERS = frozenset({"start_date", "end_date"})
TOP_PRODUCTS_FILTERS = DATE_FILTERS | {"limit"}
