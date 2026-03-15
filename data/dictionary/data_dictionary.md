# Data Dictionary

## dim_customers
- customer_id: unique customer identifier
- customer_city: customer city
- customer_state: customer state
- segment: customer segment (Consumer, Corporate, Home Office)

## dim_products
- product_id: unique product identifier
- product_category: category name
- product_name: product display name
- brand: product brand

## dim_date
- date_key: integer key in YYYYMMDD format
- full_date: calendar date
- year: numeric year
- month: numeric month
- month_name: month label
- quarter: quarter label

## fact_orders
- order_id: unique order identifier
- customer_id: foreign key to dim_customers
- order_date: order date
- order_status: Delivered, Completed, Cancelled

## fact_order_items
- order_item_id: unique order item identifier
- order_id: foreign key to fact_orders
- product_id: foreign key to dim_products
- quantity: item quantity
- unit_price: unit sale price
- item_total: quantity * unit_price

## fact_payments
- payment_id: unique payment identifier
- order_id: foreign key to fact_orders
- payment_type: Card, Transfer, Wallet
- payment_value: payment amount
- payment_status: Paid, Failed, Refunded