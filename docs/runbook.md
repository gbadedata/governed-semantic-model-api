# Runbook

## Signals
| Signal | Where | Meaning |
|---|---|---|
| `FunctionErrorsAlarm` | CloudWatch alarm | the Lambda raised an unhandled error (a bug, or a config error at cold start) |
| `Upstream5xxAlarm` | CloudWatch alarm | 5 or more 5xx responses in 5 minutes, usually the semantic model failing or throttling |
| `upstream_error` log lines | Logs Insights | each one carries the request ID, error code and upstream HTTP status |

Find recent upstream failures:
```
fields @timestamp, request_id, code, detail
| filter message = "upstream_error"
| sort @timestamp desc
| limit 50
```

## Triage by error code
- **`upstream_auth_failed` (502).** The service principal was rejected. Check the client secret has not
  expired (Entra app, Certificates & secrets), that the Fabric tenant setting still allows the
  principal's security group, and that the app is still a member of the workspace. Rotate the secret
  in Secrets Manager, then redeploy or wait for new containers (the secret is read at cold start).
- **`upstream_throttled` (503).** Fabric capacity is saturated. Consumers receive `Retry-After`. If it
  persists, check the capacity metrics app, lower the API Gateway rate limit, or scale the capacity.
- **`upstream_error` (502).** Run `GET /v1/health?deep=true`. If that fails, check the Power BI service
  status and that the semantic model and its refresh succeeded. A query error after a model change
  usually means a measure or column was renamed; the names the API expects are in `measures.py` and
  `dax.py`.
- **Cold-start `ConfigError`** (in `FunctionErrorsAlarm`). An environment variable or the secret is
  missing or malformed; the log line names what is missing.

## Rotating the client secret
1. Create a new secret on the Entra app.
2. `aws secretsmanager put-secret-value --secret-id <arn> --secret-string '{...}'`
3. Publish a new function version (or wait for containers to recycle) so the new value is read.
4. Delete the old Entra secret once `/v1/health?deep=true` succeeds.
