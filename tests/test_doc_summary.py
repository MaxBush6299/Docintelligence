from typing import Any, Dict, List

import pytest

from activities.doc_summary_activity import doc_summary_impl
from utils import openai_utils, storage_utils


@pytest.mark.parametrize(
    "document_id,page_summaries,expected_error_substring",
    [
        ("", [{"summary": "x"}], "'document_id' (string) is required for doc_summary."),
        (None, [{"summary": "x"}], "'document_id' (string) is required for doc_summary."),
        ("doc-123", [], "'page_summaries' (non-empty list) is required for doc_summary."),
        ("doc-123", None, "'page_summaries' (non-empty list) is required for doc_summary."),
    ],
)
def test_doc_summary_impl_rejects_invalid_arguments(
    document_id: str | None,
    page_summaries,
    expected_error_substring: str,
):
    with pytest.raises(ValueError) as exc_info:
        doc_summary_impl(document_id, page_summaries)  # type: ignore[arg-type]

    assert expected_error_substring in str(exc_info.value)


def test_doc_summary_impl_generates_summary_and_writes_blob(monkeypatch: pytest.MonkeyPatch) -> None:
    page_summaries: List[Dict[str, Any]] = [
        {"page": 1, "summary": "Page 1 summary."},
        {"page": 2, "summary": "Page 2 summary."},
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

    def fake_summarize(text: str, prompt: str, max_tokens: int = 1024) -> str:  # type: ignore[unused-argument]
        assert "Page 1 summary" in text
        assert "Page 2 summary" in text
        return "Multi-paragraph document summary.\nSecond paragraph here."

    monkeypatch.setattr(openai_utils, "summarize_text", fake_summarize, raising=True)

    result = doc_summary_impl("doc-123", page_summaries)

    assert result["documentId"] == "doc-123"
    assert result["status"] == "success"
    assert "Multi-paragraph document summary." in result["summary"]
    assert result["summaryBlob"] == "summaries/doc-123.json"

    # Ensure blob was written with expected path and content
    assert uploads, "Expected at least one blob upload"
    container, name, payload = uploads[0]
    assert container == "raw-pdfs"
    assert name == "summaries/doc-123.json"
    assert payload["documentId"] == "doc-123"
    assert payload["status"] == "success"
    assert "Multi-paragraph document summary." in payload["summary"]
