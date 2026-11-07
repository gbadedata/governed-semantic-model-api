from __future__ import annotations

import csv
import random
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
SAMPLE_DIR = BASE_DIR / "data" / "sample"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)

customers = [
    ("C001", "London", "England", "Consumer"),
    ("C002", "Manchester", "England", "Corporate"),
    ("C003", "Birmingham", "England", "Consumer"),
    ("C004", "Leeds", "England", "Home Office"),
    ("C005", "Glasgow", "Scotland", "Consumer"),
    ("C006", "Bristol", "England", "Corporate"),
    ("C007", "Liverpool", "England", "Consumer"),
    ("C008", "Cardiff", "Wales", "Home Office"),
    ("C009", "Edinburgh", "Scotland", "Corporate"),
    ("C010", "Nottingham", "England", "Consumer"),
]

products = [
    ("P001", "Electronics", "Wireless Mouse", "LogiTech"),
    ("P002", "Electronics", "Mechanical Keyboard", "KeyPro"),
    ("P003", "Office Supplies", "Notebook Pack", "WriteWell"),
    ("P004", "Office Supplies", "Desk Lamp", "BrightLite"),
    ("P005", "Furniture", "Office Chair", "ComfortSeat"),
    ("P006", "Furniture", "Standing Desk", "ErgoRise"),
    ("P007", "Accessories", "USB-C Hub", "PortMax"),
    ("P008", "Accessories", "Laptop Sleeve", "CarrySafe"),
]

dates = []
for month in range(1, 4):
    for day in range(1, 29):
        dt = datetime(2025, month, day)
        dates.append(
            (
                int(dt.strftime("%Y%m%d")),
                dt.strftime("%Y-%m-%d"),
                dt.year,
                dt.month,
                dt.strftime("%B"),
                f"Q{((dt.month - 1) // 3) + 1}",
            )
        )

orders = []
order_items = []
payments = []

order_counter = 1
order_item_counter = 1
payment_counter = 1

statuses = ["Delivered", "Completed", "Cancelled"]
payment_types = ["Card", "Transfer", "Wallet"]

for _ in range(80):
    order_id = f"O{order_counter:04d}"
    customer_id = random.choice(customers)[0]
    order_date = random.choice(dates)[1]
    order_status = random.choices(statuses, weights=[60, 30, 10], k=1)[0]
    orders.append((order_id, customer_id, order_date, order_status))

    num_items = random.randint(1, 3)
    order_total = 0.0

    for _ in range(num_items):
        product = random.choice(products)
        product_id = product[0]
        quantity = random.randint(1, 4)

        if product_id in {"P005", "P006"}:
            unit_price = round(random.uniform(120, 450), 2)
        elif product_id in {"P001", "P002", "P007"}:
            unit_price = round(random.uniform(25, 160), 2)
        else:
            unit_price = round(random.uniform(8, 60), 2)

        item_total = round(quantity * unit_price, 2)
        order_total += item_total

        order_items.append(
            (
                f"OI{order_item_counter:05d}",
                order_id,
                product_id,
                quantity,
                unit_price,
                item_total,
            )
        )
        order_item_counter += 1

    payment_status = "Paid"
    if order_status == "Cancelled":
        payment_status = random.choice(["Failed", "Refunded"])

    payments.append(
        (
            f"PM{payment_counter:05d}",
            order_id,
            random.choice(payment_types),
            round(order_total, 2),
            payment_status,
        )
    )

    order_counter += 1
    payment_counter += 1


def write_csv(filename: str, header: list[str], rows: list[tuple]) -> None:
    path = SAMPLE_DIR / filename
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


write_csv(
    "dim_customers.csv",
    ["customer_id", "customer_city", "customer_state", "segment"],
    customers,
)

write_csv(
    "dim_products.csv",
    ["product_id", "product_category", "product_name", "brand"],
    products,
)

write_csv(
    "dim_date.csv",
    ["date_key", "full_date", "year", "month", "month_name", "quarter"],
    dates,
)

write_csv(
    "fact_orders.csv",
    ["order_id", "customer_id", "order_date", "order_status"],
    orders,
)

write_csv(
    "fact_order_items.csv",
    ["order_item_id", "order_id", "product_id", "quantity", "unit_price", "item_total"],
    order_items,
)

write_csv(
    "fact_payments.csv",
    ["payment_id", "order_id", "payment_type", "payment_value", "payment_status"],
    payments,
)

print(f"Sample data written to: {SAMPLE_DIR}")
