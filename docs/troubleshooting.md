
# Troubleshooting Guide

## 1) Orchestrator never completes

**Causes:** Activity failure, OpenAI timeout, rate limiting.  
**Fixes:** Check App Insights traces; reduce batch size from 32 → 16; add retry/backoff.

## 2) Blob path errors

Ensure paths follow the convention:

- `raw-pdfs/<documentId>.pdf`
- `parsed-pages/<documentId>/<page>.json`
- `summaries/<documentId>/pages/<page>.json`
- `summaries/<documentId>.json`

## 3) OpenAI authentication issues

- If using Managed Identity: ensure Function App has **Cognitive Services User**.
- If using API Key: header must be `api-key: <key>` and endpoint/deployment names correct.

## 4) Cosmos DB permission errors

- Confirm SQL API mode.  
- Assign correct data-plane role if using MI, or use account key.

## 5) Memory or parse errors on large PDFs

- Try `pdfminer.six` instead of `pdfplumber` for certain edge PDFs.  
- Parse in batches or stream pages.  
- Avoid loading entire PDFs into memory when possible.

## 6) Rate limits on OpenAI

- Lower batch size (e.g., 16).  
- Add small sleeps between batches.  
- Coordinate with Azure OpenAI quota limits for your resource/region.

## 7) Idempotency / reruns

- Check if per-page summary blob exists and skip rework.  
- Use deterministic IDs in Cosmos.

## 8) Observability

- Use custom status (`set_custom_status`) for progress.  
- Ensure App Insights is receiving dependency telemetry.
