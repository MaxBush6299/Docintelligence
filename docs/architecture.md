
# Architecture Overview

This document describes the Azure-first architecture for the **Engineering Manual Summarization Pipeline**.

## High-Level Workflow

1. A client uploads a PDF to **Azure Blob Storage** (e.g., `raw-pdfs/`).
2. A client sends an **HTTP POST** to `/process-document` with `documentId` and `blobPath`.
3. The **Durable Orchestrator** begins processing:
   - Calls `pdf_split` to extract per-page text into `parsed-pages/{documentId}/{n}.json`.
   - Fans out `page_summary` activities (batched, default 32 at a time).
   - Fans in results and calls `doc_summary` to compose a multi-paragraph summary.
   - Calls `write_index` to upsert metadata in Cosmos DB.

```
+----------------------+        +----------------------------+
|   HTTP Starter       | -----> |   Durable Orchestrator     |
+----------------------+        +----------------------------+
                                        |
                               +--------+--------+
                               |    pdf_split    |
                               +-----------------+
                                        |
                    +-------------------+-------------------+
                    |                                       |
            page_summary (x N pages)                 (fan-out batches of 32)
                    |                                       |
                    +-------------------+-------------------+
                                        |
                                  doc_summary
                                        |
                                  write_index
```

## Azure Resources

- **Function App** (Python + Durable Functions)
- **Azure Document Intelligence v4.0** — GA prebuilt-read model with span-based text extraction for PDFs (up to 500 MB on S0 tier)
- **Blob Storage** containers:
  - `raw-pdfs/` — source PDFs
  - `parsed-pages/{documentId}/` — per-page text JSON
  - `summaries/{documentId}/pages/` — per-page one-liners
  - `summaries/{documentId}.json` — final summary
- **Cosmos DB (SQL API)** containers:
  - `documents` — overall document record + status
  - `pages` — optional: per-page summary index
  - `summaries` — optional: final summary index
- **Azure OpenAI** — GPT-4.1 (or 4.1-mini) for summarization
- **Application Insights** — telemetry and tracing

## Design Priorities

- **Durability & Reliability:** Automatic checkpointing, retries on activities
- **Performance:** Fan-out batches (default 32) to balance speed and rate limits
- **OCR & Text Extraction:** Azure Document Intelligence v4.0 with prebuilt-read model using span-based content extraction for accurate text layout preservation
- **Traceability:** Artifacts stored in Blob + metadata in Cosmos
- **Extensibility:** Easy to add additional analyzers, routing, legal modes
- **Security:** Prefer **Managed Identity** + RBAC, store secrets in **Key Vault**

## Data Layout

**Blob**

- `raw-pdfs/{documentId}.pdf`
- `parsed-pages/{documentId}/{page}.json`
- `summaries/{documentId}/pages/{page}.json`
- `summaries/{documentId}.json`

**Cosmos DB (examples)**

```json
// documents
{
  "id": "doc-123",
  "fileName": "doc-123.pdf",
  "pageCount": 342,
  "status": "completed",
  "summaryBlob": "summaries/doc-123.json",
  "createdAt": "2025-11-24T17:07:45Z"
}
```

```json
// pages
{
  "id": "doc-123-017",
  "documentId": "doc-123",
  "page": 17,
  "summary": "One sentence summary.",
  "textBlob": "parsed-pages/doc-123/17.json"
}
```

```json
// summaries
{
  "id": "doc-123",
  "documentId": "doc-123",
  "finalSummaryBlob": "summaries/doc-123.json",
  "units": 342
}
```
