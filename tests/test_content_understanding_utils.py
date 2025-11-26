"""
Tests for Content Understanding utility functions.
"""

import pytest

from utils import content_understanding_utils


# Sample Content Understanding API response for testing
SAMPLE_RESULT = {
    "pages": [
        {"pageNumber": 1, "width": 612, "height": 792},
        {"pageNumber": 2, "width": 612, "height": 792},
        {"pageNumber": 3, "width": 612, "height": 792},
    ],
    "contents": [
        {"pageNumber": 1, "markdown": "# Document Title\n\nIntroduction paragraph with key concepts."},
        {"pageNumber": 2, "markdown": "## Chapter 1\n\nDetailed content with **bold** and *italic* text."},
        {"pageNumber": 3, "markdown": "## Conclusion\n\nFinal summary of the document."},
    ],
    "figures": [
        {"pageNumber": 1, "description": "Company logo in top right corner"},
        {"pageNumber": 2, "description": "Figure 1: Architecture diagram showing system components"},
        {"pageNumber": 2, "description": "Figure 2: Data flow illustration"},
    ],
    "summary": "This document provides an overview of system architecture and design principles.",
}


class TestGetTotalPages:
    def test_returns_page_count_from_pages_array(self):
        result = content_understanding_utils.get_total_pages(SAMPLE_RESULT)
        assert result == 3

    def test_returns_page_count_from_contents_when_no_pages(self):
        result_without_pages = {
            "contents": [
                {"pageNumber": 1, "markdown": "Page 1"},
                {"pageNumber": 2, "markdown": "Page 2"},
                {"pageNumber": 5, "markdown": "Page 5"},  # Gap in pages
            ]
        }
        result = content_understanding_utils.get_total_pages(result_without_pages)
        assert result == 5

    def test_returns_1_for_empty_result(self):
        result = content_understanding_utils.get_total_pages({})
        assert result == 1


class TestGetPageContent:
    def test_returns_content_for_existing_page(self):
        content = content_understanding_utils.get_page_content(SAMPLE_RESULT, 1)
        assert "Document Title" in content
        assert "Introduction paragraph" in content

    def test_returns_content_for_middle_page(self):
        content = content_understanding_utils.get_page_content(SAMPLE_RESULT, 2)
        assert "Chapter 1" in content
        assert "**bold**" in content

    def test_returns_empty_string_for_nonexistent_page(self):
        content = content_understanding_utils.get_page_content(SAMPLE_RESULT, 99)
        assert content == ""

    def test_returns_empty_string_for_empty_result(self):
        content = content_understanding_utils.get_page_content({}, 1)
        assert content == ""


class TestGetDocumentSummary:
    def test_returns_summary_when_present(self):
        summary = content_understanding_utils.get_document_summary(SAMPLE_RESULT)
        assert summary == "This document provides an overview of system architecture and design principles."

    def test_returns_none_when_no_summary(self):
        result_no_summary = {"pages": [{"pageNumber": 1}]}
        summary = content_understanding_utils.get_document_summary(result_no_summary)
        assert summary is None


class TestGetFigures:
    def test_returns_all_figures(self):
        figures = content_understanding_utils.get_figures(SAMPLE_RESULT)
        assert len(figures) == 3
        assert figures[0]["description"] == "Company logo in top right corner"

    def test_returns_empty_list_when_no_figures(self):
        figures = content_understanding_utils.get_figures({})
        assert figures == []


class TestGetPageFigures:
    def test_returns_figures_for_page(self):
        figures = content_understanding_utils.get_page_figures(SAMPLE_RESULT, 2)
        assert len(figures) == 2
        assert "Architecture diagram" in figures[0]["description"]

    def test_returns_empty_list_for_page_without_figures(self):
        figures = content_understanding_utils.get_page_figures(SAMPLE_RESULT, 3)
        assert figures == []


class TestGetEndpointAndKey:
    def test_raises_when_endpoint_not_set(self, monkeypatch):
        monkeypatch.delenv("CONTENT_UNDERSTANDING_ENDPOINT", raising=False)
        monkeypatch.setenv("CONTENT_UNDERSTANDING_KEY", "test-key")
        
        with pytest.raises(ValueError) as exc_info:
            content_understanding_utils._get_endpoint_and_key()
        assert "CONTENT_UNDERSTANDING_ENDPOINT" in str(exc_info.value)

    def test_raises_when_key_not_set(self, monkeypatch):
        monkeypatch.setenv("CONTENT_UNDERSTANDING_ENDPOINT", "https://test.cognitiveservices.azure.com")
        monkeypatch.delenv("CONTENT_UNDERSTANDING_KEY", raising=False)
        
        with pytest.raises(ValueError) as exc_info:
            content_understanding_utils._get_endpoint_and_key()
        assert "CONTENT_UNDERSTANDING_KEY" in str(exc_info.value)

    def test_returns_endpoint_and_key_when_set(self, monkeypatch):
        monkeypatch.setenv("CONTENT_UNDERSTANDING_ENDPOINT", "https://test.cognitiveservices.azure.com/")
        monkeypatch.setenv("CONTENT_UNDERSTANDING_KEY", "test-key-123")
        
        endpoint, key = content_understanding_utils._get_endpoint_and_key()
        # Trailing slash should be removed
        assert endpoint == "https://test.cognitiveservices.azure.com"
        assert key == "test-key-123"


class TestGetHeaders:
    def test_returns_headers_with_key(self):
        headers = content_understanding_utils._get_headers("my-api-key")
        assert headers["Ocp-Apim-Subscription-Key"] == "my-api-key"
        assert headers["Content-Type"] == "application/pdf"

    def test_allows_custom_content_type(self):
        headers = content_understanding_utils._get_headers("my-key", "application/json")
        assert headers["Content-Type"] == "application/json"
