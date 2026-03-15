# Governed Semantic Model API on Fabric and AWS

## Overview
This project exposes governed business metrics from a Microsoft Fabric / Power BI semantic model through a secure API layer hosted on AWS.

The design assumes a realistic enterprise constraint: downstream consumers are not allowed to connect directly to source systems, so access must happen through an approved semantic serving layer.

## Business Problem
Multiple business consumers need programmatic access to trusted metrics such as revenue, order count, and category sales. Direct access to source data is restricted for security and governance reasons. As a result, the approved semantic model becomes the controlled path for consumption.

## Project Goal
Build a production-style API that:
- serves curated business metrics
- queries a Fabric semantic model instead of raw source systems
- applies secure credential handling
- supports observability and structured error handling
- can be deployed on AWS using serverless components

## Scope for Version 1
- Curated retail sample mart
- Fabric Warehouse
- Fabric / Power BI semantic model
- API endpoints for revenue, category sales, and top products
- AWS Lambda + API Gateway
- Secrets Manager
- CloudWatch logging
- Unit and integration tests

## Out of Scope for Version 1
- Full CI/CD to multiple environments
- Consumer self-service query builder
- Real-time streaming ingestion
- Multi-tenant support