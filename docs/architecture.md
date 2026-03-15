# Architecture

## Business Scenario
A retail analytics team maintains curated sales data in Microsoft Fabric. Reporting users consume metrics through a semantic model. Another downstream application team needs the same metrics programmatically, but enterprise security policy does not permit direct access to raw warehouse tables or source systems.

To satisfy this constraint, an API is introduced. The API does not query raw operational data. It queries the approved semantic model and returns business-friendly JSON responses to consumers.

## High-Level Flow
1. Curated retail data is loaded into Fabric Warehouse.
2. A semantic model is built on top of the warehouse.
3. AWS Lambda receives API requests through API Gateway.
4. Lambda retrieves Microsoft Entra credentials from AWS Secrets Manager.
5. Lambda requests an access token and executes DAX queries against the semantic model through the Power BI / Fabric REST API.
6. Lambda transforms the results into consumer-friendly JSON and returns the response.
7. Logs and operational metrics are captured in CloudWatch.

## Why This Pattern
This design preserves governance by enforcing the semantic model as the approved consumption layer instead of allowing direct raw-data access.