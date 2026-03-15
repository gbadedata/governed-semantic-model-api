# ADR 0001: Use REST Execute Queries over XMLA for v1

## Status
Accepted

## Context
The project needs to query a Fabric / Power BI semantic model from an AWS-hosted API.

## Decision
Use the Power BI Execute Queries REST API for version 1 instead of XMLA.

## Rationale
- HTTPS-based integration is simpler from AWS Lambda.
- The project only needs approved DAX query execution, not full model management.
- XMLA adds unnecessary client and connectivity complexity for the first version.

## Consequences
- The API will expose only approved metric endpoints.
- Advanced semantic model administration remains out of scope.