from typing import Any, Dict, List

from utils import storage_utils


def write_report_impl(document_id: str, total_pages: int, page_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute and persist the document processing report.

    Builds counts of successful and failed pages, captures error details,
    and writes a JSON report blob to ``reports/{documentId}.json``.
    """

    if not isinstance(document_id, str) or not document_id:
        raise ValueError("'document_id' (string) is required for write_report.")
    if not isinstance(total_pages, int) or total_pages < 0:
        raise ValueError("'total_pages' (non-negative int) is required for write_report.")

    successful_pages = [r for r in page_results if r.get("status") == "success"]
    failed_pages = [r for r in page_results if r.get("status") != "success"]

    report: Dict[str, Any] = {
        "documentId": document_id,
        "totalPages": total_pages,
        "successfulPages": len(successful_pages),
        "failedPages": len(failed_pages),
        "failedPageDetails": [
            {
                "page": r.get("page"),
                "errorCategory": r.get("errorCategory", "unknown"),
                "errorMessage": r.get("errorMessage", ""),
            }
            for r in failed_pages
        ],
    }

    report_blob_path = f"{document_id}.json"
    storage_utils.write_json_blob("reports", report_blob_path, report)
    report["reportBlob"] = report_blob_path
    return report


def write_report_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Durable activity wrapper around write_report_impl.

    Expects a payload with documentId, totalPages, and pageResults.
    """

    document_id = payload.get("documentId")
    total_pages = payload.get("totalPages")
    page_results = payload.get("pageResults") or []
    return write_report_impl(document_id, total_pages, page_results)  # type: ignore[arg-type]
