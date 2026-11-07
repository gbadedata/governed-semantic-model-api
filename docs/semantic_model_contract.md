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

A **qualifying order** is one with status Completed or Delivered and at least one payment with
status Paid. All revenue measures are built on qualifying orders only.

### Total Revenue
Sum of order item totals for qualifying orders within the selected date range.

### Total Orders
Distinct count of qualifying orders within the selected date range. (Counting cancelled or unpaid
orders here would make Average Order Value understate what customers actually spend.)

### Average Order Value
Total Revenue divided by Total Orders; blank (null in the API) when there are no qualifying orders.

The DAX implementation is in `semantic_model/measures.dax`; the API's catalogue is in
`src/semantic_api/measures.py`. Tests check that both cover the same measures.

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