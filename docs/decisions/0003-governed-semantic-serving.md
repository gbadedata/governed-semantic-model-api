# ADR 0003: Use semantic model as the only serving layer

## Status
Accepted

## Context
Enterprise security controls do not permit direct raw-data access for the consumer use case.

## Decision
The API will query only the approved semantic model, not raw warehouse tables or source systems.

## Rationale
- Preserves governance.
- Enforces shared business definitions.
- Prevents downstream metric drift.

## Consequences
- API design must remain tightly scoped to approved measures.
- Semantic model availability becomes an upstream dependency.