from typing import Any, Dict, List

import pytest

from activities.write_report_activity import write_report_impl
from utils import storage_utils


@pytest.mark.parametrize(
    "document_id,total_pages,expected_error_substring",
    [
        ("", 1, "'document_id' (string) is required for write_report."),
        (None, 1, "'document_id' (string) is required for write_report."),
        ("doc-123", -1, "'total_pages' (non-negative int) is required for write_report."),
    ],
)
def test_write_report_impl_rejects_invalid_arguments(
    document_id: str | None,
    total_pages: int,
    expected_error_substring: str,
):
    with pytest.raises(ValueError) as exc_info:
        write_report_impl(document_id, total_pages, [])  # type: ignore[arg-type]

    assert expected_error_substring in str(exc_info.value)


def test_write_report_impl_counts_and_persists_report(monkeypatch: pytest.MonkeyPatch) -> None:
    page_results: List[Dict[str, Any]] = [
        {"page": 1, "status": "success"},
        {"page": 2, "status": "failed", "errorMessage": "oops"},
        {"page": 3, "status": "success"},
    ]

    uploads: list[tuple[str, str, Dict[str, Any]]] = []

    class DummyBlobClient:
        def __init__(self, container: str, name: str):
            self._container = container
            self._name = name

        def upload_blob(self, body: bytes, overwrite: bool = False) -> None:  # pragma: no cover
            import json

            uploads.append((self._container, self._name, json.loads(body.decode("utf-8"))))

    class DummyContainerClient:
        def get_blob_client(self, name: str) -> "DummyBlobClient":
            return DummyBlobClient("raw-pdfs", name)

    class DummyBlobServiceClient:
        def get_container_client(self, container: str) -> "DummyContainerClient":  # pragma: no cover
            assert container == "raw-pdfs"
            return DummyContainerClient()

    monkeypatch.setattr(storage_utils, "_blob_service_client", DummyBlobServiceClient(), raising=True)

    report = write_report_impl("doc-123", total_pages=3, page_results=page_results)

    assert report["documentId"] == "doc-123"
    assert report["totalPages"] == 3
    assert report["successfulPages"] == 2
    assert report["failedPages"] == 1
    assert report["reportBlob"] == "reports/doc-123.json"
    assert len(report["failedPageDetails"]) == 1
    detail = report["failedPageDetails"][0]
    assert detail["page"] == 2
    assert detail["errorMessage"] == "oops"

    # Verify blob persisted with same data
    assert uploads, "Expected at least one blob upload"
    container, name, payload = uploads[0]
    assert container == "raw-pdfs"
    assert name == "reports/doc-123.json"
    assert payload["documentId"] == "doc-123"
    assert payload["totalPages"] == 3
    assert payload["successfulPages"] == 2
    assert payload["failedPages"] == 1
    assert len(payload["failedPageDetails"]) == 1
