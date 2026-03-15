from __future__ import annotations

from pathlib import Path
import csv

BASE_DIR = Path(__file__).resolve().parents[1]
SAMPLE_DIR = BASE_DIR / "data" / "sample"


def read_csv(name: str) -> list[dict]:
    with (SAMPLE_DIR / name).open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


customers = read_csv("dim_customers.csv")
products = read_csv("dim_products.csv")
dates = read_csv("dim_date.csv")
orders = read_csv("fact_orders.csv")
order_items = read_csv("fact_order_items.csv")
payments = read_csv("fact_payments.csv")

customer_ids = {r["customer_id"] for r in customers}
product_ids = {r["product_id"] for r in products}
date_values = {r["full_date"] for r in dates}
order_ids = {r["order_id"] for r in orders}

assert len(customer_ids) == len(customers), "Duplicate customer_id detected"
assert len(product_ids) == len(products), "Duplicate product_id detected"
assert len(order_ids) == len(orders), "Duplicate order_id detected"

for row in orders:
    assert row["customer_id"] in customer_ids, f"Unknown customer_id: {row['customer_id']}"
    assert row["order_date"] in date_values, f"Unknown order_date: {row['order_date']}"

for row in order_items:
    assert row["order_id"] in order_ids, f"Unknown order_id in items: {row['order_id']}"
    assert row["product_id"] in product_ids, f"Unknown product_id: {row['product_id']}"

for row in payments:
    assert row["order_id"] in order_ids, f"Unknown order_id in payments: {row['order_id']}"

print("Validation passed.")
print(f"Customers: {len(customers)}")
print(f"Products: {len(products)}")
print(f"Dates: {len(dates)}")
print(f"Orders: {len(orders)}")
print(f"Order items: {len(order_items)}")
print(f"Payments: {len(payments)}")