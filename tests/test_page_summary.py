from typing import Any, Dict, List, Tuple

import pytest

from activities.page_summary_activity import page_summary_impl
from utils import openai_utils, storage_utils


class DummyDownloader:
    def __init__(self, payload: Dict[str, Any]):
        self._payload = payload

    def readall(self) -> bytes:
        import json

        return json.dumps(self._payload).encode("utf-8")


class DummyBlobClient:
    def __init__(self, downloads: List[Tuple[str, str]], container: str, name: str, payload: Dict[str, Any]):
        self._downloads = downloads
        self._container = container
        self._name = name
        self._payload = payload

    def download_blob(self) -> DummyDownloader:
        self._downloads.append((self._container, self._name))
        return DummyDownloader(self._payload)

    def upload_blob(self, body: bytes, overwrite: bool = False) -> None:  # pragma: no cover
        pass


class DummyContainerClient:
    def __init__(self, downloads: List[Tuple[str, str]], payload: Dict[str, Any]):
        self._downloads = downloads
        self._payload = payload

    def get_blob_client(self, name: str) -> DummyBlobClient:
        return DummyBlobClient(self._downloads, "raw-pdfs", name, self._payload)


class DummyBlobServiceClient:
    def __init__(self, downloads: List[Tuple[str, str]], payload: Dict[str, Any]):
        self._downloads = downloads
        self._payload = payload

    def get_container_client(self, container: str) -> DummyContainerClient:
        assert container == "raw-pdfs"
        return DummyContainerClient(self._downloads, self._payload)


def test_page_summary_impl_reads_page_and_writes_success(monkeypatch: pytest.MonkeyPatch) -> None:
    page_payload = {"content": "This is some test page text."}
    downloads: List[Tuple[str, str]] = []
    service = DummyBlobServiceClient(downloads, page_payload)

    monkeypatch.setattr(storage_utils, "_blob_service_client", service, raising=True)

    def fake_summarize(text: str, prompt: str, max_tokens: int = 512) -> str:  # type: ignore[unused-argument]
        return "This is a summary."

    monkeypatch.setattr(openai_utils, "summarize_text", fake_summarize, raising=True)

    result = page_summary_impl("doc-123", 1)

    assert result["documentId"] == "doc-123"
    assert result["page"] == 1
    assert result["status"] == "success"
    assert result["summary"] == "This is a summary."
    assert downloads == [("raw-pdfs", "parsed-pages/doc-123/1.json")]


def test_page_summary_impl_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    page_payload = {"content": "Some page text that will eventually be summarized."}
    downloads: List[Tuple[str, str]] = []
    service = DummyBlobServiceClient(downloads, page_payload)

    monkeypatch.setattr(storage_utils, "_blob_service_client", service, raising=True)

    call_count = {"n": 0}

    def flaky_summarize(text: str, prompt: str, max_tokens: int = 512) -> str:  # type: ignore[unused-argument]
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise RuntimeError("temporary OpenAI error")
        return "Recovered summary."

    monkeypatch.setattr(openai_utils, "summarize_text", flaky_summarize, raising=True)

    result = page_summary_impl("doc-456", 2)

    assert result["status"] == "success"
    assert result["summary"] == "Recovered summary."
    assert result["documentId"] == "doc-456"
    assert result["page"] == 2
    assert call_count["n"] == 3


def test_page_summary_impl_marks_failed_after_all_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    page_payload = {"content": "Some page text that will never summarize."}
    downloads: List[Tuple[str, str]] = []
    service = DummyBlobServiceClient(downloads, page_payload)

    monkeypatch.setattr(storage_utils, "_blob_service_client", service, raising=True)

    def always_fail_summarize(text: str, prompt: str, max_tokens: int = 512) -> str:  # type: ignore[unused-argument]
        raise RuntimeError("permanent OpenAI error")

    monkeypatch.setattr(openai_utils, "summarize_text", always_fail_summarize, raising=True)

    result = page_summary_impl("doc-789", 3)

    assert result["status"] == "failed"
    assert result["documentId"] == "doc-789"
    assert result["page"] == 3
    assert "permanent OpenAI error" in result.get("error", "")


def test_page_summary_impl_rejects_invalid_arguments() -> None:
    with pytest.raises(ValueError):
        page_summary_impl("", 1)
    with pytest.raises(ValueError):
        page_summary_impl("doc-123", 0)
