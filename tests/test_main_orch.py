from typing import Any, Dict, List

import pytest

from function_app import main_orch_impl


class DummyTask:
    def __init__(self, result: Any) -> None:
        self._result = result

    def result(self) -> Any:  # pragma: no cover - thin wrapper
        return self._result


class DummyOrchestrationContext:
    def __init__(self, input_payload: Dict[str, Any] | None) -> None:
        self._input = input_payload
        self.activities: list[tuple[str, Dict[str, Any]]] = []
        self.statuses: list[Dict[str, Any]] = []
        self._activity_results: Dict[tuple[str, Any], Any] = {}

    def get_input(self) -> Dict[str, Any] | None:
        return self._input

    def set_custom_status(self, value: Dict[str, Any]) -> None:
        self.statuses.append(value)

    def call_activity(self, name: str, input_: Dict[str, Any]) -> Any:
        self.activities.append((name, input_))
        key = (name, input_.get("page") or input_.get("documentId"))
        return self._activity_results[key]

    def task_all(self, tasks: List[Any]) -> DummyTask:
        return DummyTask([t for t in tasks])

    def set_activity_result(self, name: str, key: Any, result: Any) -> None:
        self._activity_results[(name, key)] = result


def _build_context(payload: Dict[str, Any] | None) -> DummyOrchestrationContext:
    return DummyOrchestrationContext(payload)


def test_main_orch_impl_runs_full_pipeline_and_returns_summary():
    context = _build_context({"documentId": "doc-123", "blobPath": "raw-pdfs/doc-123.pdf"})

    # pdf_split returns 3 pages
    context.set_activity_result("pdf_split", "doc-123", {"page_count": 3})

    # page_summary results for pages 1-3
    for page in [1, 2, 3]:
        context.set_activity_result(
            "page_summary",
            page,
            {"documentId": "doc-123", "page": page, "status": "success", "summary": f"summary-{page}"},
        )

    # doc_summary result
    context.set_activity_result(
        "doc_summary",
        "doc-123",
        {
            "documentId": "doc-123",
            "status": "success",
            "summary": "doc summary",
            "summaryBlob": "summaries/doc-123.json",
        },
    )

    # write_report result
    context.set_activity_result(
        "write_report",
        "doc-123",
        {
            "documentId": "doc-123",
            "totalPages": 3,
            "successfulPages": 3,
            "failedPages": 0,
            "failedPageDetails": [],
            "reportBlob": "reports/doc-123.json",
        },
    )

    # write_index result
    index_document = {
        "id": "doc-123",
        "documentId": "doc-123",
        "status": "completed",
    }
    context.set_activity_result("write_index", "doc-123", index_document)

    result = main_orch_impl(context)  # type: ignore[arg-type]

    assert result["documentId"] == "doc-123"
    assert result["blobPath"] == "raw-pdfs/doc-123.pdf"
    assert result["pageCount"] == 3
    assert result["failedPageCount"] == 0
    assert result["summaryBlob"] == "summaries/doc-123.json"
    assert result["reportBlob"] == "reports/doc-123.json"
    assert result["indexDocument"] == index_document

    # Ensure activities were called in expected order
    activity_names = [name for name, _ in context.activities]
    assert activity_names[0] == "pdf_split"
    assert "page_summary" in activity_names[1:4]
    assert "doc_summary" in activity_names
    assert "write_report" in activity_names
    assert "write_index" in activity_names


@pytest.mark.parametrize(
    "payload,expected_error_substring",
    [
        ({}, "'documentId' (string) is required in orchestration input."),
        ({"documentId": "doc-123"}, "'blobPath' (string) is required in orchestration input."),
        ({"blobPath": "raw-pdfs/doc-123.pdf"}, "'documentId' (string) is required in orchestration input."),
    ],
)
def test_main_orch_impl_rejects_invalid_input(payload, expected_error_substring):
    context = _build_context(payload)

    with pytest.raises(ValueError) as exc_info:
        main_orch_impl(context)  # type: ignore[arg-type]

    assert expected_error_substring in str(exc_info.value)
