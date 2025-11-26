# Implementation Checklist

This checklist describes the end-to-end implementation plan for the Azure Durable Functions PDF summarization pipeline.

## 1. Environment and Local Settings

- [x] Create and activate a Python virtual environment.
- [x] Install dependencies from `requirements.txt`.
- [x] Create `local.settings.json` with at least:
  - [x] `AzureWebJobsStorage`
  - [x] `FUNCTIONS_WORKER_RUNTIME`
  - [x] `AZURE_OPENAI_ENDPOINT`
  - [x] `AZURE_OPENAI_DEPLOYMENT`
  - [x] `AZURE_OPENAI_API_KEY` (or configure Managed Identity)
  - [x] `COSMOS_ENDPOINT`
  - [x] `COSMOS_DB`
  - [x] `COSMOS_KEY` (or configure Managed Identity)
  - [x] `BLOB_ACCOUNT_URL`
  - [x] `OPENAI_MAX_CONCURRENCY` (e.g., `32`)
  - [x] `PAGE_SUMMARY_SENTENCES` (default `2`)
  
**Test / Verify**

- [x] Run `func --version` to ensure Azure Functions Core Tools is available.
- [x] Run a simple `python -c "import azure.functions"` to confirm core packages import.
- [x] Start the Functions host (`func start`) and confirm it boots without configuration errors.

_Pytest mapping suggestion: `tests/test_env_and_settings.py`_

- `test_func_core_tools_available()`
- `test_azure_functions_package_imports()`
- `test_functions_host_starts_without_errors()`

## 2. Durable Functions Project and Skeleton (v2 Programming Model)

- [x] Initialize Python Azure Functions project (v2 model with `function_app.py`).
- [x] Define core functions in `function_app.py` via decorators (v2/DFApp model):
  - [x] `http_start` HTTP starter (decorated) + `http_start_impl` implementation used by tests.
  - [x] `main_orch` orchestrator (decorated) + `main_orch_impl` implementation used by tests.
  - [x] `pdf_split_activity` Durable activity (decorated) + `pdf_split_impl` stub implementation used by tests.
  - [ ] `page_summary` (activity) – **not yet implemented**.
  - [ ] `doc_summary` (activity) – **not yet implemented**.
  - [ ] `write_report` (activity) – **not yet implemented**.
  - [ ] `write_index` (activity) – **not yet implemented**.
  - _Tech debt note_: the `*_impl` pattern is intentional to keep Durable bindings thin and logic testable; see `TECH_DEBT.md` for details.
  
**Test / Verify**

- [x] Run `func start` and ensure all functions are discovered without errors.
- [x] Call the default HTTP trigger (even before full logic) and confirm a 200/202 response.

_Pytest mapping suggestion: `tests/test_functions_discovery.py`_

- `test_all_functions_are_discovered()` (imports `function_app.app` and asserts required routes/triggers exist).
- `test_http_trigger_returns_success_response()` (invokes `http_start` directly with a fake `HttpRequest`).

## 3. Shared Helper Modules

- [x] Create `utils.storage_utils` module:
  - [x] `get_blob_client(container, blob_name)`
  - [x] `read_json_blob(container, blob_name)`
  - [x] `write_json_blob(container, blob_name, data)`
  - [x] `blob_exists(container, blob_name)`
- [x] Create `utils.cosmos_utils` module:
  - [x] Cosmos client factory from environment variables.
  - [x] `upsert_document_record(document)` for `documents` container.
  - [ ] (Optional) Simple helpers for `pages` and `summaries` containers.
- [x] Create `utils.openai_utils` module:
  - [x] Initialize Azure OpenAI client from env vars.
  - [ ] `summarize_text(text, prompt, max_tokens)` with retry/backoff for transient errors.
  
**Test / Verify**

- [x] Write unit tests to:
  - [x] Call `write_json_blob`/`read_json_blob` using dummy clients (no real storage dependency).
  - [x] Exercise `upsert_document_record` using a dummy Cosmos client.
  - [x] Call `summarize_text` with a short string via a stubbed Azure OpenAI client.

_Pytest mapping: `tests/test_storage_utils.py`, `tests/test_cosmos_utils.py`, `tests/test_helpers.py`_

- [x] `test_write_and_read_json_blob_roundtrip()`
- [x] `test_blob_exists()`
- [x] `test_get_documents_container_and_upsert()`
- [x] `test_summarize_text_uses_deployment_and_returns_string()`

## 4. `pdf_split` Activity

- [x] Create stubbed `pdf_split_impl` to:
  - [x] Accept `documentId` and `blobPath` arguments and validate them.
  - [x] Return a deterministic single-page list payload for testing and orchestration wiring.
- [x] Expose `pdf_split_activity` Durable activity wrapper (decorated) that calls `pdf_split_impl`.
- [x] Replace stubbed `pdf_split_impl` with implementation to:
  - [x] Download the source PDF from Blob Storage using `utils.storage_utils`.
  - [x] Extract per-page text using `pdfplumber`.
  - [x] Write `parsed-pages/{documentId}/{page}.json` containing at least `documentId`, `pageNumber`, `text`, and `length`.
  - [x] Have `pdf_split_activity` return `{"page_count": N}` to the orchestrator.
  - _Tech debt note_: additional metadata or alternate storage layouts can be layered on later if needed.
  
**Test / Verify**

- [x] Run `pdf_split_impl` locally in tests with a known PDF.
- [x] Confirm (via dummy clients) that `parsed-pages/{documentId}/` JSON blobs are written with expected fields.
- [ ] Manually open a few JSON files and verify text quality and `length` values.

_Pytest mapping: `tests/test_pdf_split.py`_

- [x] `test_pdf_split_impl_downloads_from_blob_and_writes_json()`
- [x] `test_pdf_split_impl_rejects_invalid_arguments()`

## 5. `page_summary` Activity

- [x] Implement `page_summary` to:
  - [x] Accept `documentId` and `page`.
  - [x] Read `parsed-pages/{documentId}/{page}.json`.
  - [ ] Truncate very long text before sending to OpenAI.
  - [x] Read `PAGE_SUMMARY_SENTENCES` (default 2) from configuration.
  - [x] Build a prompt to summarize the page in exactly N sentences.
  - [x] Call Azure OpenAI via `openai_utils.summarize_text`.
  - [x] Retry up to 5 times on transient errors; classify permanent errors.
  - [x] On success, write `summaries/{documentId}/pages/{page}.json` with `status = "success"` and `summary`.
  - [x] On failure, write `summaries/{documentId}/pages/{page}.json` with `status = "failed"` and `error` details.
  - [x] Return a small result object including `page`, `status`, and any error info.

**Test / Verify**

- [x] Invoke `page_summary` for a single page and confirm a `summaries/{documentId}/pages/{page}.json` is written.
- [x] Temporarily misconfigure OpenAI (e.g., bad key) to ensure failures are marked with `status = "failed"` and `error` populated.
- [x] Verify retry behavior by inspecting logs or adding a counter in tests.

_Pytest mapping: `tests/test_page_summary.py`_

- [x] `test_page_summary_impl_reads_page_and_writes_success()`
- [x] `test_page_summary_impl_retries_then_succeeds()`
- [x] `test_page_summary_impl_marks_failed_after_all_retries()`
- [x] `test_page_summary_impl_rejects_invalid_arguments()`

## 6. `doc_summary` Activity

- [x] Implement `doc_summary` to:
  - [x] Accept a list of successful page summary results.
  - [ ] Load corresponding page summary blobs as needed.
  - [x] Build a multi-paragraph document summary prompt from the page summaries.
  - [x] Call Azure OpenAI to generate the document summary.
  - [x] Write `summaries/{documentId}.json` with the final summary and optional metadata.
  - [x] Return the summary blob path and metadata to the orchestrator.
  
**Test / Verify**

- [x] Provide a small list of synthetic page summaries and run `doc_summary` directly.
- [x] Confirm the resulting document summary is multi-paragraph and stored at the expected blob path.

_Pytest mapping: `tests/test_doc_summary.py`_

- [x] `test_doc_summary_impl_generates_summary_and_writes_blob()`
- [x] `test_doc_summary_impl_rejects_invalid_arguments()`

## 7. `write_report` Activity

- [x] Implement `write_report` to:
  - [x] Accept `documentId`, `totalPages`, and the list of page results.
  - [x] Compute `successfulPages`, `failedPages`, and `failedPageDetails`.
  - [x] Write `reports/{documentId}.json` with:
    - [x] `documentId`
    - [x] `totalPages`, `successfulPages`, `failedPages`
    - [x] `failedPageDetails` (list of `{ page, errorCategory, errorMessage }`).
  
  **Test / Verify**

  - [x] Call `write_report` with a mix of success and failed page results.
  - [x] Open `reports/{documentId}.json` and verify counts and `failedPageDetails` match input.

  _Pytest mapping suggestion: `tests/test_write_report.py`_

  _Pytest mapping: `tests/test_write_report.py`_

  - [x] `test_write_report_impl_counts_and_persists_report()`
  - [x] `test_write_report_impl_rejects_invalid_arguments()`

## 8. `write_index` Activity

- [x] Implement `write_index` to:
  - [x] Accept `documentId`, `blobPath`, `pageCount`, `failedPageCount`, and blob paths for summary and report.
  - [x] Derive `fileName` from `blobPath`.
  - [x] Compute `status`:
    - [x] `completed` if `failedPageCount == 0`.
    - [x] `completed_with_errors` otherwise.
  - [x] Build a minimal `documents` record with:
    - [x] `id` / `documentId`
    - [x] `fileName`
    - [x] `pageCount`
    - [x] `summaryBlob`
    - [x] `reportBlob`
    - [x] `failedPageCount`
    - [x] `status`
    - [x] timestamps.
  - [x] Upsert the record into the Cosmos `documents` container.
  
**Test / Verify**

- [x] Run `write_index` with a known input and inspect the `documents` container in Cosmos.
- [x] Confirm `status`, counts, and blob paths are correct and idempotent on repeated upserts.

_Pytest mapping: `tests/test_write_index.py`_

- [x] `test_write_index_impl_builds_expected_record()`
- [x] `test_write_index_impl_rejects_invalid_arguments()`

## 9. `main_orch` Orchestrator

- [x] Implement minimal `main_orch_impl` to:
  - [x] Accept orchestration input and validate `documentId` and `blobPath`.
  - [x] Return a simple payload echoing `documentId` and `blobPath`.
  - _Tech debt note_: this minimal implementation has now been extended to the full pipeline.
- [x] Extend `main_orch_impl` to full pipeline orchestrator to:
  - [x] Accept `documentId` and `blobPath` as input.
  - [x] Call `pdf_split_activity` and get `page_count`.
  - [x] Set custom status after splitting with total pages.
  - [x] Build list of pages `[1..page_count]`.
  - [x] Fan-out `page_summary` activities in batches (e.g., batch size from `OPENAI_MAX_CONCURRENCY`).
  - [x] Periodically update custom status during page summarization (completed vs total).
  - [x] After fan-in, separate successful and failed pages.
  - [x] If there are successful pages, call `doc_summary` with them.
  - [x] Call `write_report` with all page results.
  - [x] Call `write_index` with counts and blob paths.
  - [x] Set final custom status to `completed` with summary of counts and report path.
  
**Test / Verify**

- [ ] Start an orchestration via the Durable Functions dashboard or HTTP starter.
- [ ] Watch orchestrator history to confirm `pdf_split`, `page_summary`, `doc_summary`, `write_report`, and `write_index` run in the expected order.
- [ ] Check custom status updates reflect progress and final counts.

_Pytest mapping: `tests/test_main_orch.py`_

- [x] `test_main_orch_impl_runs_full_pipeline_and_returns_summary()`
- [x] `test_main_orch_impl_rejects_invalid_input()`

## 10. `http_start` Starter (v2 HTTP + Durable Client)

- [ ] Implement `http_start` in `function_app.py` to:
  - [ ] Parse and validate the JSON body containing `documentId` and `blobPath`.
  - [ ] Use the injected Durable client (`DurableOrchestrationClient`) to start the `main_orch` orchestration.
  - [ ] Return the standard Durable Functions status response with status URLs.
  
**Test / Verify**

- [ ] Call `POST /api/process-document` with a minimal valid payload and confirm a 202 response with status URLs.
- [ ] Call with invalid payloads (missing `documentId` or `blobPath`) and confirm appropriate 4xx validation errors.

_Pytest mapping suggestion: `tests/test_http_start.py`_

- `test_http_start_accepts_valid_payload_and_returns_status_urls()` (imports and calls `function_app.http_start` with a mocked Durable client).
- `test_http_start_rejects_invalid_payload()` (same, but with invalid JSON bodies to assert 4xx behavior).

## 11. Documentation Updates

- [ ] Update `docs/prompts.md` with:
  - [ ] Final page summary prompt (configurable N sentences).
  - [ ] Final document summary prompt.
- [ ] Update `docs/function-flow.md` with:
  - [ ] Actual function names and steps.
  - [ ] Inclusion of the `reports/{documentId}.json` artifact.
- [ ] Update `README.md` with:
  - [ ] Description of `PAGE_SUMMARY_SENTENCES` (default 2).
  - [ ] Mention of `reports/{documentId}.json` as a key artifact.
  - [ ] A short demo walkthrough (upload PDF, call endpoint, inspect artifacts).
  
**Test / Verify**

- [ ] Follow the documented steps end-to-end as if you were a new user and confirm nothing is missing or ambiguous.

_Pytest mapping suggestion: `tests/test_docs_and_readme.py`_

- `test_readme_quick_start_steps_are_complete()`
- `test_docs_reference_all_key_artifacts()`

## 12. End-to-End Local Test

- [ ] Start the Functions host with `func start`.
- [ ] Upload a small test PDF to `raw-pdfs/` in local storage.
- [ ] Call `POST /api/process-document` with `documentId` and `blobPath`.
- [ ] Poll the returned status URL until the orchestration completes.
- [ ] Verify:
  - [ ] `parsed-pages/`, `summaries/`, and `reports/` blobs exist and look correct.
  - [ ] A `documents` record exists in Cosmos with the expected `status` and counts.
  - [ ] Page-level failures (if simulated) do not abort the whole document processing.

**Test / Verify (Extended)**

- [ ] Run with a very small PDF (1–2 pages) and a larger manual to compare behavior.
- [ ] Intentionally trigger a few failures (e.g., corrupt page, broken OpenAI config) and verify partial-success behavior and reporting.

_Pytest mapping suggestion: `tests/test_e2e_pipeline.py`_

- `test_e2e_small_pdf_happy_path(func_client, storage_fixture, cosmos_fixture)`
- `test_e2e_large_pdf_with_partial_failures_reports_correctly(func_client, storage_fixture, cosmos_fixture)`
