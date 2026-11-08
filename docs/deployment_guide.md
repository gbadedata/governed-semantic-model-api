# Deployment Guide

The stack is defined in `infra/template.yaml` (AWS SAM): an HTTP API with IAM authorisation, one
Python 3.12 Lambda function (arm64), a log group, and two CloudWatch alarms.

## 1. Prepare the semantic model (Fabric)
1. Load `data/sample/*.csv` into a Fabric Warehouse (or Lakehouse) as tables with the same names.
2. Build a semantic model on those tables with these relationships, single direction:
   `fact_order_items[order_id] -> fact_orders[order_id]`, `fact_payments[order_id] -> fact_orders[order_id]`,
   `fact_orders[order_date] -> dim_date[full_date]`, `fact_order_items[product_id] -> dim_products[product_id]`,
   `fact_orders[customer_id] -> dim_customers[customer_id]`.
3. Add the measures in `semantic_model/measures.dax` (DAX query view, then "Update model").
4. Run the `EVALUATE` at the bottom of that file. For the full sample it must return Total Revenue
   43430.95, Total Orders 69 and Average Order Value 629.43, the same figures the API's local backend
   produces. If it does not, fix the model before deploying.
5. Note the workspace ID and semantic model (dataset) ID from their URLs.

## 2. Create the service principal
1. Register an app in Microsoft Entra ID and create a client secret.
2. In the Fabric admin portal, allow service principals to use Fabric APIs for a security group that
   contains the app.
3. Add the app to the workspace as **Viewer**.

## 3. Store the credentials in AWS
```bash
aws secretsmanager create-secret --name governed-semantic-api/fabric-sp \
  --secret-string '{"tenant_id":"<tenant>","client_id":"<app id>","client_secret":"<secret>"}'
```

## 4. Deploy
```bash
sam build --template-file infra/template.yaml
sam deploy --guided \
  --parameter-overrides FabricWorkspaceId=<workspace id> FabricDatasetId=<dataset id> \
                        FabricCredentialsSecretArn=<secret arn>
```

## 5. Verify
```bash
# requests must be SigV4-signed; awscurl is one convenient client
awscurl --service execute-api "$API_URL/v1/health?deep=true"
awscurl --service execute-api "$API_URL/v1/metrics/revenue?start_date=2025-01-01&end_date=2025-03-31"
```
The second call should return the same figures as step 1.4.

## Local development
```bash
pip install -e ".[dev]"
python -m semantic_api            # serves the local sample backend on http://127.0.0.1:8000/docs
python -m pytest                  # tests, including the Fabric backend against a mocked HTTP API
```
