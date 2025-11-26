import logging
from typing import Any, Dict, List

from utils import openai_utils, storage_utils


def _build_doc_summary_prompt() -> str:
    """Build the system prompt for the document-level summary."""

    return (
        "You are a helpful assistant that writes a multi-paragraph summary of a document "
        "based on per-page summaries. Combine the information into a coherent narrative "
        "without explicitly referring to pages. Aim for clear, well-structured paragraphs. "
        "Return ONLY the summary text with no additional commentary, explanations, or meta-text. "
        "Do not include phrases like 'Here is the summary' or 'This document discusses'. "
        "Start directly with the summary content."
    )


def doc_summary_impl(document_id: str, page_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate a document-level summary from page-level summaries using Azure OpenAI."""

    if not isinstance(document_id, str) or not document_id:
        raise ValueError("'document_id' (string) is required for doc_summary.")
    if not isinstance(page_summaries, list) or not page_summaries:
        raise ValueError("'page_summaries' (non-empty list) is required for doc_summary.")

    # Optionally load/refresh page summary blobs; for now we trust the provided list
    # and build a combined prompt input from their summaries.
    parts: List[str] = []
    for item in page_summaries:
        page = item.get("page")
        summary = item.get("summary", "")
        if not isinstance(summary, str) or not summary:
            continue
        if page is not None:
            parts.append(f"Page {page}: {summary}")
        else:
            parts.append(str(summary))

    if not parts:
        raise ValueError("At least one page summary with non-empty 'summary' is required.")

    joined_summaries = "\n".join(parts)
    prompt = _build_doc_summary_prompt()

    try:
        # Set a reasonable token limit for document summaries (4096 tokens ~ 3000 words)
        # This prevents excessively long generation times for large documents
        final_summary = openai_utils.summarize_text(joined_summaries, prompt)
    except Exception as exc:  # pragma: no cover - failure path covered via tests if added later
        logging.error("doc_summary_impl failed for document %s: %s", document_id, exc)
        raise

    result = {
        "documentId": document_id,
        "status": "success",
        "summary": final_summary,
    }

    summary_blob_path = f"{document_id}.json"
    storage_utils.write_json_blob("summaries", summary_blob_path, result)
    result["summaryBlob"] = summary_blob_path
    return result


def doc_summary_activity(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Durable activity wrapper around doc_summary_impl.

    Expects a payload with documentId and pageSummaries.
    """

    document_id = payload.get("documentId")
    page_summaries = payload.get("pageSummaries")
    return doc_summary_impl(document_id, page_summaries)  # type: ignore[arg-type]
