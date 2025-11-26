import logging
import os
from typing import Any, Dict

from utils import openai_utils, storage_utils


def _build_page_summary_prompt(sentences: int) -> str:
    """Build the system prompt for page-level summarization."""

    return (
        "You are a helpful assistant that summarizes a single page of a PDF document. "
        f"Write a concise summary in exactly {sentences} sentences. "
        "Focus only on the content in the provided page text. "
        "Return ONLY the summary text with no additional commentary, explanations, or meta-text. "
        "Do not include phrases like 'Here is the summary' or 'This page discusses'. "
        "Start directly with the summary content."
    )


def _get_page_summary_sentences() -> int:
    value = os.environ.get("PAGE_SUMMARY_SENTENCES", "2")
    try:
        parsed = int(value)
    except ValueError as exc:  # pragma: no cover - defensive parsing
        raise RuntimeError("PAGE_SUMMARY_SENTENCES must be an integer") from exc
    if parsed <= 0:
        raise RuntimeError("PAGE_SUMMARY_SENTENCES must be a positive integer")
    return parsed


def page_summary_impl(document_id: str, page_number: int) -> Dict[str, Any]:
    """Summarize a single page using Azure OpenAI.

    Reads parsed page text from Blob Storage, calls Azure OpenAI via
    utils.openai_utils.summarize_text, and writes the result to
    "summaries/{documentId}/pages/{page}.json".
    """

    if not isinstance(document_id, str) or not document_id:
        raise ValueError("'document_id' (string) is required for page_summary.")
    if not isinstance(page_number, int) or page_number <= 0:
        raise ValueError("'page_number' (positive int) is required for page_summary.")

    page_blob = f"parsed-pages/{document_id}/{page_number}.json"
    page_data: Dict[str, Any] = storage_utils.read_json_blob("raw-pdfs", page_blob)
    text = page_data.get("content") or page_data.get("text") or ""
    if not isinstance(text, str) or not text.strip():
        # Handle pages with no extractable text (e.g., image-only pages)
        logging.warning(
            "Page %s of document %s has no extractable text - skipping summarization",
            page_number,
            document_id,
        )
        result = {
            "documentId": document_id,
            "page": page_number,
            "status": "skipped",
            "summary": "[No text content on this page]",
        }
        storage_utils.write_json_blob(
            "summaries",
            f"{document_id}/pages/{page_number}.json",
            result,
        )
        return result

    sentences = _get_page_summary_sentences()
    prompt = _build_page_summary_prompt(sentences)

    max_attempts = 5
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            # No max_completion_tokens limit - let the model generate the full response
            summary = openai_utils.summarize_text(text, prompt)
            result = {
                "documentId": document_id,
                "page": page_number,
                "status": "success",
                "summary": summary,
            }
            storage_utils.write_json_blob(
                "summaries",
                f"{document_id}/pages/{page_number}.json",
                result,
            )
            return result
        except Exception as exc:  # pragma: no cover - error path covered via failure test
            last_error = exc
            logging.warning(
                "page_summary_impl attempt %s/%s failed for document %s page %s: %s",
                attempt,
                max_attempts,
                document_id,
                page_number,
                exc,
            )

    #error after retries
    error_message = str(last_error) if last_error is not None else "Unknown error"
    failed_result = {
        "documentId": document_id,
        "page": page_number,
        "status": "failed",
        "error": error_message,
    }
    storage_utils.write_json_blob(
        "raw-pdfs",
        f"summaries/{document_id}/pages/{page_number}.json",
        failed_result,
    )
    return failed_result


def page_summary_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Durable activity wrapper around page_summary_impl.

    Expects a payload with documentId and page.
    """

    document_id = payload.get("documentId")
    page_number = payload.get("page")
    return page_summary_impl(document_id, page_number)  # type: ignore[arg-type]
