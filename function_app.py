import json
import logging
import os
from http import HTTPStatus
from typing import Any, Dict, List

import azure.durable_functions as df
import azure.functions as func

from activities.pdf_split_activity import pdf_split_activity
from activities.doc_summary_activity import doc_summary_activity
from activities.page_summary_activity import page_summary_activity
from activities.write_index_activity import write_index_activity
from activities.write_report_activity import write_report_activity


# Single DFApp for all functions (HTTP routes, orchestrators, and activities)
app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.function_name("health_check")
@app.route(route="health", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Simple health check endpoint to verify the app is running."""
    logging.info("Health check invoked.")
    payload = {"status": "ok"}
    return func.HttpResponse(
        body=json.dumps(payload),
        status_code=HTTPStatus.OK,
        mimetype="application/json",
    )


def _parse_process_document_body(req: func.HttpRequest) -> Dict[str, Any]:
    """Parse and validate the process-document HTTP request body."""
    try:
        data = req.get_json()
    except ValueError as exc:
        raise ValueError("Request body must be valid JSON.") from exc

    document_id = data.get("documentId")
    blob_path = data.get("blobPath")

    if not isinstance(document_id, str) or not document_id:
        raise ValueError("'documentId' (string) is required.")
    if not isinstance(blob_path, str) or not blob_path:
        raise ValueError("'blobPath' (string) is required.")

    return {"documentId": document_id, "blobPath": blob_path}


async def _http_start_impl(
    req: func.HttpRequest,
    client: df.DurableOrchestrationClient,
) -> func.HttpResponse:
    """Core implementation for the main_orch Durable HTTP starter."""
    try:
        payload = _parse_process_document_body(req)
    except ValueError as exc:
        logging.warning("Bad request payload for process-document: %s", exc)
        return func.HttpResponse(
            body=json.dumps({"error": str(exc)}),
            status_code=HTTPStatus.BAD_REQUEST,
            mimetype="application/json",
        )

    instance_id = await client.start_new("main_orch", None, payload)
    logging.info("Started orchestration with ID = %s", instance_id)
    return client.create_check_status_response(req, instance_id)


@app.route(route="process-document")
@app.durable_client_input(client_name="client")
async def http_start(
    req: func.HttpRequest,
    client: df.DurableOrchestrationClient,
) -> func.HttpResponse:
    """HTTP starter for the main_orch Durable orchestrator (v2 DFApp model)."""
    return await _http_start_impl(req, client)


# Explicit alias used by tests so they can await a plain coroutine
http_start_impl = _http_start_impl


@app.activity_trigger(input_name="payload")
def page_summary(payload: Dict[str, Any]):
    """Durable activity entry point for page_summary.

    Delegates to activities.page_summary_activity.page_summary_activity.
    """

    return page_summary_activity(payload)


@app.activity_trigger(input_name="payload")
def doc_summary(payload: Dict[str, Any]):
    """Durable activity entry point for doc_summary.

    Delegates to activities.doc_summary_activity.doc_summary_activity.
    """

    return doc_summary_activity(payload)


@app.activity_trigger(input_name="payload")
def write_report(payload: Dict[str, Any]):
    """Durable activity entry point for write_report.

    Delegates to activities.write_report_activity.write_report_activity.
    """

    return write_report_activity(payload)


@app.activity_trigger(input_name="payload")
def write_index(payload: Dict[str, Any]):
    """Durable activity entry point for write_index.

    Delegates to activities.write_index_activity.write_index_activity.
    """

    return write_index_activity(payload)


@app.activity_trigger(input_name="payload")
def pdf_split(payload: Dict[str, Any]):
    """Durable activity entry point for PDF splitting.

    Delegates to activities.pdf_split_activity.pdf_split_activity.
    """

    return pdf_split_activity(payload)


def main_orch_impl(context: df.DurableOrchestrationContext) -> Dict[str, Any]:
    """Core implementation of the main_orch orchestrator.

    Implements the full document processing pipeline:
    - Split PDF into pages.
    - Summarize each page in batches.
    - Generate a document-level summary.
    - Write a processing report.
    - Upsert an index record into Cosmos.
    """

    data = context.get_input() or {}
    document_id = data.get("documentId")
    blob_path = data.get("blobPath")

    if not isinstance(document_id, str) or not document_id:
        raise ValueError("'documentId' (string) is required in orchestration input.")
    if not isinstance(blob_path, str) or not blob_path:
        raise ValueError("'blobPath' (string) is required in orchestration input.")

    # Step 1: split PDF
    pdf_split_result = yield context.call_activity("pdf_split", {"documentId": document_id, "blobPath": blob_path})
    page_count = int(pdf_split_result.get("page_count", 0))
    context.set_custom_status({"stage": "split", "totalPages": page_count})

    if page_count <= 0:
        # Nothing to process; still write a minimal index and report later.
        page_results: List[Dict[str, Any]] = []
    else:
        # Step 2: page summaries with batching
        max_concurrency = int(os.environ.get("OPENAI_MAX_CONCURRENCY", "32"))
        if max_concurrency <= 0:
            max_concurrency = 32

        pages = list(range(1, page_count + 1))
        page_results = []

        def _chunks(items: List[int], size: int) -> List[List[int]]:
            return [items[i : i + size] for i in range(0, len(items), size)]

        completed_pages = 0
        for batch in _chunks(pages, max_concurrency):
            batch_tasks = []
            for page in batch:
                payload = {"documentId": document_id, "page": page}
                batch_tasks.append(context.call_activity("page_summary", payload))

            batch_results = yield context.task_all(batch_tasks)
            page_results.extend(batch_results)
            completed_pages += len(batch_results)
            context.set_custom_status(
                {
                    "stage": "page_summary",
                    "completedPages": completed_pages,
                    "totalPages": page_count,
                }
            )

    # Step 3: split successes and failures
    successful_pages = [r for r in page_results if r.get("status") == "success"]
    failed_pages = [r for r in page_results if r.get("status") != "success"]
    failed_page_count = len(failed_pages)

    # Step 4: document summary (if there are successful page summaries)
    doc_summary_result: Dict[str, Any] | None = None
    summary_blob: str = ""
    if successful_pages:
        doc_summary_result = yield context.call_activity(
            "doc_summary",
            {"documentId": document_id, "pageSummaries": successful_pages},
        )
        summary_blob = doc_summary_result.get("summaryBlob") or ""

    # Step 5: write report for all pages
    report_result = yield context.call_activity(
        "write_report",
        {"documentId": document_id, "totalPages": page_count, "pageResults": page_results},
    )
    report_blob = report_result.get("reportBlob", "")

    # Step 6: write index record in Cosmos
    index_result = yield context.call_activity(
        "write_index",
        {
            "documentId": document_id,
            "blobPath": blob_path,
            "pageCount": page_count,
            "failedPageCount": failed_page_count,
            "summaryBlob": summary_blob,
            "reportBlob": report_blob,
        },
    )

    # Final custom status and return payload
    context.set_custom_status(
        {
            "stage": "completed",
            "totalPages": page_count,
            "successfulPages": len(successful_pages),
            "failedPages": failed_page_count,
            "summaryBlob": summary_blob,
            "reportBlob": report_blob,
        },
    )

    return {
        "documentId": document_id,
        "blobPath": blob_path,
        "pageCount": page_count,
        "failedPageCount": failed_page_count,
        "summaryBlob": summary_blob,
        "reportBlob": report_blob,
        "indexDocument": index_result,
    }


@app.orchestration_trigger(context_name="context")
def main_orch(context: df.DurableOrchestrationContext):
    """Durable Functions orchestrator entry point.

    This wrapper exists so the DF runtime can bind to it, while tests
    exercise the pure-Python logic in main_orch_impl.
    """
    return main_orch_impl(context)
