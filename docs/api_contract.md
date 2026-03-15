# API Contract

## Base Path
`/v1`

## Endpoints

### GET /v1/health
Checks API health and upstream dependency status.

**Response**
```json
{
  "status": "ok",
  "service": "governed-semantic-model-api",
  "upstream": "unknown",
  "timestamp": "2026-03-14T12:00:00Z"
}