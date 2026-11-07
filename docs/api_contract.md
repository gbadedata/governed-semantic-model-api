# API Contract

Base path `/v1`. All endpoints are `GET`, return JSON, and include an `X-Request-ID` response header.
In AWS every request must be signed with SigV4 (API Gateway IAM authorisation). The live OpenAPI
document is served at `/openapi.json` and interactive docs at `/docs` when running locally.

## Approved filters

| Parameter | Type | Endpoints | Rules |
|---|---|---|---|
| `start_date` | `YYYY-MM-DD` | all metrics | required; first order date included |
| `end_date` | `YYYY-MM-DD` | all metrics | required; on or after `start_date`; range at most 366 days |
| `limit` | integer | `top-products` | 1 to 50, default 5 |

Any other query parameter is rejected with `400`. Consumers cannot run free-form queries.

## Endpoints

### GET /v1/health
Liveness. Add `?deep=true` to also run a trivial query against the semantic model.

```json
{
  "status": "ok",
  "service": "governed-semantic-model-api",
  "version": "1.0.0",
  "backend": "fabric-semantic-model",
  "upstream": "unknown",
  "timestamp": "2026-03-14T12:00:00Z"
}
```

`upstream` is `unknown` for the shallow check and `ok` after a successful deep check. A failed deep
check returns the standard error body with `502`.

### GET /v1/measures
The governed measure catalogue: each key, the semantic-model measure it maps to, and its definition.

### GET /v1/metrics/revenue
Total Revenue, Total Orders and Average Order Value for the period.

```json
{
  "period": {"start_date": "2025-01-01", "end_date": "2025-03-31"},
  "currency": "USD",
  "total_revenue": 43430.95,
  "total_orders": 69,
  "average_order_value": 629.43,
  "source": "fabric-semantic-model",
  "generated_at": "2026-03-14T12:00:00Z"
}
```

`average_order_value` is `null` when the period has no qualifying orders.

### GET /v1/metrics/sales-by-category
Total Revenue by product category, highest first.

```json
{
  "period": {"start_date": "2025-01-01", "end_date": "2025-03-31"},
  "currency": "USD",
  "measure": "total_revenue",
  "categories": [{"category": "Furniture", "revenue": 27179.77}],
  "source": "fabric-semantic-model",
  "generated_at": "2026-03-14T12:00:00Z"
}
```

### GET /v1/metrics/top-products
Products ranked by Total Revenue.

```json
{
  "period": {"start_date": "2025-01-01", "end_date": "2025-03-31"},
  "currency": "USD",
  "measure": "total_revenue",
  "limit": 3,
  "products": [
    {"rank": 1, "product_id": "P006", "product_name": "Standing Desk", "category": "Furniture", "revenue": 16887.69}
  ],
  "source": "fabric-semantic-model",
  "generated_at": "2026-03-14T12:00:00Z"
}
```

## Errors

Every error uses one shape:

```json
{"error": {"code": "invalid_request", "message": "end_date must be on or after start_date", "request_id": "..."}}
```

| Status | `code` | When |
|---|---|---|
| 400 | `invalid_request` | an unsupported query parameter was sent |
| 422 | `invalid_request` | a parameter is missing, malformed or out of range (`details` lists the fields) |
| 502 | `upstream_error` / `upstream_auth_failed` | the semantic model failed or rejected the service principal |
| 503 | `upstream_throttled` | the semantic model is throttling; honour the `Retry-After` header |

Upstream error detail is logged, never returned to the consumer.
