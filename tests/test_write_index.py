from typing import Any, Dict

import pytest

from activities.write_index_activity import write_index_impl
from utils import cosmos_utils


def test_write_index_impl_builds_expected_record(monkeypatch: pytest.MonkeyPatch):
    upserts: list[Dict[str, Any]] = []

    def fake_upsert(doc: Dict[str, Any]) -> None:
        upserts.append(doc)

    monkeypatch.setattr(cosmos_utils, "upsert_document_record", fake_upsert, raising=True)

    record = write_index_impl(
        document_id="doc-123",
        blob_path="raw-pdfs/doc-123.pdf",
        page_count=10,
        failed_page_count=1,
        summary_blob="summaries/doc-123.json",
        report_blob="reports/doc-123.json",
    )

    assert record["id"] == "doc-123"
    assert record["documentId"] == "doc-123"
    assert record["fileName"] == "doc-123.pdf"
    assert record["blobPath"] == "raw-pdfs/doc-123.pdf"
    assert record["pageCount"] == 10
    assert record["failedPageCount"] == 1
    assert record["status"] == "completed_with_errors"
    assert record["summaryBlob"] == "summaries/doc-123.json"
    assert record["reportBlob"] == "reports/doc-123.json"
    assert "createdAt" in record
    assert "updatedAt" in record

    # Ensure upsert was called with same document
    assert upserts == [record]


@pytest.mark.parametrize(
    "document_id,blob_path,expected_error_substring",
    [
        ("", "raw-pdfs/doc-123.pdf", "'document_id' (string) is required for write_index."),
        (None, "raw-pdfs/doc-123.pdf", "'document_id' (string) is required for write_index."),
        ("doc-123", "", "'blob_path' (string) is required for write_index."),
        ("doc-123", None, "'blob_path' (string) is required for write_index."),
    ],
)
def test_write_index_impl_rejects_invalid_arguments(
    document_id: str | None,
    blob_path: str | None,
    expected_error_substring: str,
):
    with pytest.raises(ValueError) as exc_info:
        write_index_impl(
            document_id,
            blob_path,
            page_count=0,
            failed_page_count=0,
            summary_blob="",
            report_blob="",
        )  # type: ignore[arg-type]

    assert expected_error_substring in str(exc_info.value)
