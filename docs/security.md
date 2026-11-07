# Security

## Consumer access
- API Gateway's HTTP API uses **IAM authorisation** on every route. Consumers call with SigV4-signed
  requests using an IAM role or user granted `execute-api:Invoke` on this API, so access is managed
  and audited in IAM rather than by shared keys.
- Default route throttling (10 requests per second, burst 20) protects the semantic model's capacity.

## What consumers can ask for
- Only the measures in `src/semantic_api/measures.py` are served, and only through the fixed
  endpoints. Unknown query parameters are rejected with `400`.
- **No consumer text reaches DAX.** Queries are built from the catalogue; the only interpolated
  values are dates (parsed and validated as dates) and an integer limit (bounded 1-50 and type-checked
  again in `dax.top_products`). There is no injection path.

## Credentials
- The Fabric service principal's `tenant_id`, `client_id` and `client_secret` live in **AWS Secrets
  Manager**. The Lambda role may read that one secret ARN and nothing else.
- The secret is read once per Lambda container and held in memory. It is never logged, and
  `FabricCredentials.__repr__` masks it.
- The Entra access token is cached in memory until two minutes before expiry, then refreshed. A `401`
  from Power BI triggers one refresh and retry.
- `.env` is git-ignored; `.env.example` contains no values.

## Least privilege on the Fabric side
- Use a dedicated service principal, enabled in the Fabric admin portal setting that allows service
  principals to use Fabric / Power BI APIs (scoped to a security group).
- Give it **Viewer** (or Build) on the one workspace that holds the semantic model, nothing broader.
- Apply row-level security in the semantic model if consumers should see different slices; the API
  then inherits it.

## Logging
- One JSON log line per request: request ID, method, path, status, duration and backend. No query
  results and no credentials are logged. Upstream failures log the error class and HTTP status only.
- Logs go to a dedicated CloudWatch log group with a set retention (30 days by default).
