# ADR 0002: Host API on AWS serverless stack

## Status
Accepted

## Context
The project needs a realistic cloud-hosted API layer.

## Decision
Use AWS Lambda and API Gateway for v1.

## Rationale
- Cheap and realistic for a portfolio build.
- Good fit for request-response APIs.
- Cross-cloud architecture is stronger than keeping everything in one platform.

## Consequences
- Secrets must be handled securely.
- Logging and metrics will be centralized in CloudWatch.