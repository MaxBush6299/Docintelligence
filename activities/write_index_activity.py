from datetime import datetime, timezone
from typing import Any, Dict

from utils import cosmos_utils


def write_index_impl(
    document_id: str,
    blob_path: str,
    page_count: int,
    failed_page_count: int,
    summary_blob: str,
    report_blob: str,
) -> Dict[str, Any]:
    """Build and upsert the documents index record into Cosmos DB."""

    if not isinstance(document_id, str) or not document_id:
        raise ValueError("'document_id' (string) is required for write_index.")
    if not isinstance(blob_path, str) or not blob_path:
        raise ValueError("'blob_path' (string) is required for write_index.")

    status = "completed" if failed_page_count == 0 else "completed_with_errors"
    file_name = blob_path.split("/")[-1]
    now = datetime.now(timezone.utc).isoformat()

    document: Dict[str, Any] = {
        "id": document_id,
        "documentId": document_id,
        "fileName": file_name,
        "blobPath": blob_path,
        "pageCount": page_count,
        "summaryBlob": summary_blob,
        "reportBlob": report_blob,
        "failedPageCount": failed_page_count,
        "status": status,
        "createdAt": now,
        "updatedAt": now,
    }

    cosmos_utils.upsert_document_record(document)
    return document


def write_index_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Durable activity wrapper around write_index_impl.

    Expects a payload with documentId, blobPath, pageCount, failedPageCount,
    summaryBlob, and reportBlob.
    """

    document_id = payload.get("documentId")
    blob_path = payload.get("blobPath")
    page_count = payload.get("pageCount", 0)
    failed_page_count = payload.get("failedPageCount", 0)
    summary_blob = payload.get("summaryBlob", "")
    report_blob = payload.get("reportBlob", "")

    return write_index_impl(
        document_id,
        blob_path,
        page_count,
        failed_page_count,
        summary_blob,
        report_blob,
    )  # type: ignore[arg-type]
