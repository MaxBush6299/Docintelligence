
# Deployment Guide

This guide covers deploying the pipeline to Azure.

## Required Resources

- Resource Group
- Storage Account
- Function App (Linux, Python)
- Cosmos DB (SQL API)
- Azure OpenAI resource
- Application Insights (often created with Function App)

## Permissions (Managed Identity)

Assign the **Function App**'s system-assigned identity:

- **Blob Storage**: `Storage Blob Data Contributor`
- **Cosmos DB**: Data plane role (e.g., Built-in Data Contributor) or key-based
- **Azure OpenAI**: `Cognitive Services User` (if using MI)

## App Settings

Mirror `local.settings.json` values in the Function App configuration. Prefer **Key Vault** references for secrets.

## Deployment Options

### Azure Functions Core Tools (local)

```bash
func azure functionapp publish <your-function-app-name>
```

### GitHub Actions (example)

```yaml
name: Deploy Functions
on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - uses: Azure/functions-action@v1
        with:
          app-name: ${{ secrets.FUNCTION_APP_NAME }}
          package: '.'
```

## Post-Deployment Checks

- Verify App Insights traces (dependencies: Blob, Cosmos, OpenAI).
- Run an end-to-end test with a small PDF (5–10 pages).
- Tune batch size (16/32/64) to match your OpenAI rate limits.

