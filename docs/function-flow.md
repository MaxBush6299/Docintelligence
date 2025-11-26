
# Function Flow

This document details each Azure Function (Python, Durable) using the **v2 programming model** (`FunctionApp` + decorators in `function_app.py`).

## 1) http_start (HTTP Trigger, v2)

HTTP route defined via `@app.route` and Durable client via `@durable.DurableClientInput` in `function_app.py`. Starts the orchestration and returns Durable status URLs.

**Request body**

```json
{
  "documentId": "doc-123",
  "blobPath": "raw-pdfs/doc-123.pdf"
}
```

**Responsibilities**

- Validate input JSON (`documentId`, `blobPath`).
- Use the injected `DurableOrchestrationClient` to start `main_orch`.
- Return standard Durable Functions status response (async HTTP pattern).

---

## 2) main_orch (Durable Orchestrator, v2)

Registered via `@app.orchestration_trigger` in `function_app.py`. Controls the pipeline:

1. `pdf_split` → returns `page_count`
2. Fan-out `page_summary` for pages `1..N` in **batches of 32**
3. Fan-in results → aggregate
4. `doc_summary` → multi-paragraph synthesis
5. `write_index` → persist metadata

**Notes**

- Use `context.task_all()` for batch waits.
- Use `context.set_custom_status({"stage":"summarizing","completed":x,"total":N})` for progress.

---

## 3) pdf_split (Activity, v2)

- Reads the source PDF from Blob (`blobPath`).
- Extracts text per page using `pdfplumber`/`pdfminer.six`.
- Writes `parsed-pages/{documentId}/{page}.json` with fields:
  - `documentId`, `pageNumber`, `text`, `length`

**Return:** `{"page_count": N}`

---

## 4) page_summary (Activity, v2)

- Reads `parsed-pages/{documentId}/{page}.json`.
- Calls **Azure OpenAI** with a strict **one-sentence** prompt.
- Writes `summaries/{documentId}/pages/{page}.json` with:
  - `documentId`, `page`, `summary`

**Optional:** Upsert a `pages` document to Cosmos.

---

## 5) doc_summary (Activity, v2)

- Accepts an array of page one-liners.
- Calls **Azure OpenAI** to produce a **multi-paragraph** document summary.
- Writes `summaries/{documentId}.json` with:
  - `documentId`, `summary`

**Optional:** Upsert `summaries` record to Cosmos.

---

## 6) write_index (Activity, v2)

- Upserts the `documents` container with:
  - `id` (documentId), `fileName`, `pageCount`, `status`, `summaryBlob`, timestamps

---

## Concurrency & Retry

- Default batch size: **32** (balanced).
- Add exponential backoff retries around OpenAI calls.
- Idempotency: skip a page if the summary blob already exists.
