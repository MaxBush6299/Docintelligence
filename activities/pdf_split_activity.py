import asyncio
from typing import Any, Dict, List

from utils import storage_utils
from utils import document_intelligence_utils as content_understanding_utils


def _download_pdf_bytes(blob_path: str) -> bytes:
    """Download the source PDF from Blob Storage as bytes.

    ``blob_path`` is expected to look like ``"container/name.pdf"``.
    """
    if "/" not in blob_path:
        raise ValueError("blob_path must be of the form 'container/blob-name.pdf'")

    container, blob_name = blob_path.split("/", 1)
    blob_client = storage_utils.get_blob_client(container, blob_name)

    downloader = blob_client.download_blob()
    return downloader.readall()


async def _analyze_document_async(pdf_bytes: bytes) -> dict:
    """Analyze document using Content Understanding API."""
    return await content_understanding_utils.analyze_document(pdf_bytes)


def pdf_split_impl(document_id: str, blob_path: str) -> List[Dict[str, Any]]:
    """Split a PDF from Blob Storage into pages with extracted text using Azure Content Understanding.

    - Downloads the PDF referenced by ``blob_path`` from Blob Storage.
    - Sends PDF to Azure Content Understanding for OCR and analysis.
    - Extracts text content for each page from the analysis result.
    - Writes per-page JSON blobs under ``parsed-pages/{documentId}/{page}.json``
      using ``storage_utils.write_json_blob``.
    - Returns a list of per-page records for the orchestrator.
    """

    if not isinstance(document_id, str) or not document_id:
        raise ValueError("'document_id' (string) is required for pdf_split.")
    if not isinstance(blob_path, str) or not blob_path:
        raise ValueError("'blob_path' (string) is required for pdf_split.")

    # Download PDF as bytes
    pdf_bytes = _download_pdf_bytes(blob_path)

    # Analyze document with Content Understanding (async call in sync context)
    result = asyncio.run(_analyze_document_async(pdf_bytes))

    # Get total pages from analysis result
    total_pages = content_understanding_utils.get_total_pages(result)

    pages: List[Dict[str, Any]] = []

    for page_num in range(1, total_pages + 1):
        # Extract content for this page
        text = content_understanding_utils.get_page_content(result, page_num)
        
        record = {
            "documentId": document_id,
            "pageNumber": page_num,
            "blobPath": blob_path,
            "content": text,
            "length": len(text),
        }
        pages.append(record)

        # Persist per-page JSON for downstream activities
        # Always write to raw-pdfs container for consistency
        json_blob_name = f"parsed-pages/{document_id}/{page_num}.json"
        storage_utils.write_json_blob("raw-pdfs", json_blob_name, record)

    return pages


def pdf_split_activity(payload: Dict[str, Any]) -> Dict[str, int]:
    """Durable activity wrapper around ``pdf_split_impl``.

    Expects a payload with ``documentId`` and ``blobPath`` keys and returns a
    small summary object ``{"page_count": N}`` for the orchestrator.
    """

    document_id = payload.get("documentId")
    blob_path = payload.get("blobPath")
    pages = pdf_split_impl(document_id, blob_path)  # type: ignore[arg-type]
    return {"page_count": len(pages)}
