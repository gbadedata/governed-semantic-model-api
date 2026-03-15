# Semantic Model Contract

## Purpose
This semantic model is the governed business-serving layer for downstream API access.

## Core Dimensions
- Customer
- Product
- Date

## Core Facts
- Orders
- Order Items
- Payments

## Business Measures

### Total Revenue
Sum of paid order item totals for completed or delivered orders within the selected date range.

### Total Orders
Distinct count of orders within the selected date range.

### Average Order Value
Total Revenue divided by Total Orders.

### Sales by Category
Total Revenue grouped by product category.

### Top Products
Products ranked by Total Revenue.

## Assumptions
- Cancelled orders are excluded from revenue.
- Only successful payments count toward revenue.
- Date filters apply using order date.
- Currency is modeled as USD for the sample project.

## Consumer Constraints
- Consumers cannot run arbitrary free-form analytical queries through the API.
- Only approved measures and approved filters are exposed.