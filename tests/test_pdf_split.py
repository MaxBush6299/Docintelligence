from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from activities import pdf_split_activity as pdf_mod
from utils import storage_utils
from utils import content_understanding_utils


class DummyDownloader:
    def __init__(self, content: bytes) -> None:
        self._content = content

    def readall(self) -> bytes:
        return self._content


class DummyBlobClient:
    def __init__(self, content: bytes) -> None:
        self._content = content
        self.download_called = False

    def download_blob(self) -> DummyDownloader:
        self.download_called = True
        return DummyDownloader(self._content)


class DummyWriteBlobClient:
    def __init__(self) -> None:
        self.writes: list[tuple[str, Any]] = []

    def upload_blob(self, data: bytes, overwrite: bool = False) -> None:  # type: ignore[override]
        self.writes.append((data.decode("utf-8"), overwrite))


class DummyContainerClient:
    def __init__(self, blob_client: DummyBlobClient, write_client: DummyWriteBlobClient) -> None:
        self._blob_client = blob_client
        self._write_client = write_client
        self.requested_blob_names: list[str] = []

    def get_blob_client(self, name: str):  # type: ignore[override]
        # First call is for the PDF download, subsequent calls are for JSON writes
        self.requested_blob_names.append(name)
        if name.endswith(".pdf"):
            return self._blob_client
        return self._write_client


class DummyBlobServiceClient:
    def __init__(self, container_client: DummyContainerClient) -> None:
        self._container_client = container_client
        self.requested_containers: list[str] = []

    def get_container_client(self, name: str):  # type: ignore[override]
        self.requested_containers.append(name)
        return self._container_client


# Mock Content Understanding result with 3 pages
MOCK_CONTENT_UNDERSTANDING_RESULT = {
    "pages": [
        {"pageNumber": 1},
        {"pageNumber": 2},
        {"pageNumber": 3},
    ],
    "contents": [
        {"pageNumber": 1, "markdown": "# Page 1 Title\n\nThis is the content of page 1 with OCR text."},
        {"pageNumber": 2, "markdown": "## Page 2 Section\n\nPage 2 has tables and figures."},
        {"pageNumber": 3, "markdown": "### Page 3 Conclusion\n\nFinal page with summary."},
    ],
}


def test_pdf_split_impl_downloads_from_blob_and_writes_json(monkeypatch: pytest.MonkeyPatch) -> None:
    # Load the real test PDF bytes (we still need actual bytes to send to the mock)
    pdf_path = Path("tests/pdf/github-copilot-exam-preparation-study-guide.pdf")
    assert pdf_path.exists(), "Expected test PDF to exist at tests/pdf/..."
    pdf_bytes = pdf_path.read_bytes()

    # Wire up dummy storage layer
    read_blob_client = DummyBlobClient(pdf_bytes)
    write_blob_client = DummyWriteBlobClient()
    container_client = DummyContainerClient(read_blob_client, write_blob_client)
    service_client = DummyBlobServiceClient(container_client)

    monkeypatch.setattr(storage_utils, "_blob_service_client", service_client, raising=False)

    # Mock Content Understanding API to return predictable results
    async def mock_analyze_document(pdf_bytes, polling_interval=2.0, max_wait_time=600.0):
        return MOCK_CONTENT_UNDERSTANDING_RESULT

    with patch.object(content_understanding_utils, 'analyze_document', mock_analyze_document):
        pages = pdf_mod.pdf_split_impl("doc-123", "raw-pdfs/github-copilot-exam-preparation-study-guide.pdf")

    assert isinstance(pages, list)
    assert len(pages) == 3  # Our mock returns 3 pages
    print(f"pdf_split_impl produced {len(pages)} pages")
    first_page = pages[0]

    assert first_page["documentId"] == "doc-123"
    assert first_page["pageNumber"] == 1
    assert first_page["blobPath"] == "raw-pdfs/github-copilot-exam-preparation-study-guide.pdf"
    assert isinstance(first_page["content"], str)
    assert "Page 1" in first_page["content"]  # Verify mock content
    assert first_page["length"] == len(first_page["content"])

    # Verify second page content
    second_page = pages[1]
    assert second_page["pageNumber"] == 2
    assert "Page 2" in second_page["content"]

    # Storage expectations: container used is "raw-pdfs" and we wrote JSON per page
    assert service_client.requested_containers == ["raw-pdfs"] * (
        1 + len(pages)
    )  # one download + one write per page
    assert any(name.endswith(".pdf") for name in container_client.requested_blob_names)
    assert any(name.startswith("parsed-pages/doc-123/") for name in container_client.requested_blob_names)
    # At least one JSON payload was uploaded
    assert len(write_blob_client.writes) >= 1


def test_pdf_split_activity_returns_page_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the activity wrapper returns correct page count."""
    pdf_bytes = b"%PDF-1.4 fake pdf content"
    
    read_blob_client = DummyBlobClient(pdf_bytes)
    write_blob_client = DummyWriteBlobClient()
    container_client = DummyContainerClient(read_blob_client, write_blob_client)
    service_client = DummyBlobServiceClient(container_client)

    monkeypatch.setattr(storage_utils, "_blob_service_client", service_client, raising=False)

    async def mock_analyze_document(pdf_bytes, polling_interval=2.0, max_wait_time=600.0):
        return MOCK_CONTENT_UNDERSTANDING_RESULT

    with patch.object(content_understanding_utils, 'analyze_document', mock_analyze_document):
        result = pdf_mod.pdf_split_activity(
            {
                "documentId": "doc-123",
                "blobPath": "raw-pdfs/test.pdf",
            }
        )
    
    assert result == {"page_count": 3}


@pytest.mark.parametrize(
    "document_id,blob_path,expected_error_substring",
    [
        ("", "raw-pdfs/doc-123.pdf", "'document_id' (string) is required for pdf_split."),
        (None, "raw-pdfs/doc-123.pdf", "'document_id' (string) is required for pdf_split."),
        ("doc-123", "", "'blob_path' (string) is required for pdf_split."),
        ("doc-123", None, "'blob_path' (string) is required for pdf_split."),
    ],
)
def test_pdf_split_impl_rejects_invalid_arguments(document_id, blob_path, expected_error_substring):
    with pytest.raises(ValueError) as exc_info:
        pdf_mod.pdf_split_impl(document_id, blob_path)  # type: ignore[arg-type]

    assert expected_error_substring in str(exc_info.value)
