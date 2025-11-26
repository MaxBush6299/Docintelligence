"""
Utility functions for Azure Document Intelligence integration.

Uses the prebuilt-read model for OCR and text extraction from PDF documents.
"""

import os
import logging
from io import BytesIO
from typing import Optional
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeResult

logger = logging.getLogger(__name__)


def _get_endpoint_and_key() -> tuple[str, str]:
    """Get Document Intelligence endpoint and key from environment variables."""
    endpoint = os.environ.get("DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.environ.get("DOCUMENT_INTELLIGENCE_KEY")
    
    if not endpoint:
        raise ValueError("DOCUMENT_INTELLIGENCE_ENDPOINT environment variable is not set")
    if not key:
        raise ValueError("DOCUMENT_INTELLIGENCE_KEY environment variable is not set")
    
    # Remove trailing slash if present
    endpoint = endpoint.rstrip("/")
    return endpoint, key


def _get_model_id() -> str:
    """Get the Document Intelligence model ID from environment or use default."""
    return os.environ.get("DOCUMENT_INTELLIGENCE_MODEL", "prebuilt-read")


async def analyze_document(
    pdf_bytes: bytes,
    model_id: Optional[str] = None,
) -> AnalyzeResult:
    """
    Analyze a PDF document using Azure Document Intelligence.
    
    This function:
    1. Creates a DocumentIntelligenceClient
    2. Submits the PDF for analysis using begin_analyze_document
    3. Automatically polls until complete
    4. Returns the full AnalyzeResult
    
    Args:
        pdf_bytes: The PDF file content as bytes
        model_id: Optional model ID to use (defaults to prebuilt-read)
        
    Returns:
        AnalyzeResult: The analysis result containing:
            - pages: List of DocumentPage objects with lines and words
            - content: Full document text content
            - model_id: The model used for analysis
            
    Raises:
        ValueError: If environment variables are not set
        Exception: If API request fails
    """
    endpoint, key = _get_endpoint_and_key()
    
    if model_id is None:
        model_id = _get_model_id()
    
    logger.info(f"Analyzing document: endpoint={endpoint}, model={model_id}, size={len(pdf_bytes)} bytes")
    
    # Create the client with key-based authentication
    # API version 2024-11-30 is the latest GA version
    client = DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
        api_version="2024-11-30"
    )
    
    try:
        # Submit document for analysis - SDK handles polling automatically
        # Wrap bytes in BytesIO to create a file-like object
        pdf_stream = BytesIO(pdf_bytes)
        
        # Per SDK docs: begin_analyze_document(model_id, analyze_request, content_type)
        poller = client.begin_analyze_document(
            model_id,
            analyze_request=pdf_stream,
            content_type="application/octet-stream"
        )
        
        logger.info("Document submitted, waiting for analysis to complete...")
        
        # Wait for the operation to complete
        result: AnalyzeResult = poller.result()
        
        logger.info(f"Analysis complete: {len(result.pages)} pages processed")
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing document with Document Intelligence: {e}")
        raise


def get_total_pages(result: AnalyzeResult) -> int:
    """
    Get the total number of pages from an analysis result.
    
    Args:
        result: The AnalyzeResult from analyze_document
        
    Returns:
        int: Number of pages in the document
    """
    if not result.pages:
        return 0
    return len(result.pages)


def get_page_content(result: AnalyzeResult, page_number: int) -> str:
    """
    Extract text content for a specific page using span-based extraction.
    
    This extracts content from result.content using the page's spans to get
    the exact text that belongs to this page, preserving the original formatting.
    
    Args:
        result: The AnalyzeResult from analyze_document
        page_number: 1-indexed page number to extract
        
    Returns:
        str: The text content of the specified page
        
    Raises:
        IndexError: If page_number is out of range
    """
    if not result.pages:
        return ""
    
    # Convert 1-indexed page number to 0-indexed
    page_index = page_number - 1
    
    if page_index < 0 or page_index >= len(result.pages):
        raise IndexError(f"Page {page_number} is out of range (1-{len(result.pages)})")
    
    page = result.pages[page_index]
    
    # Use span-based extraction from result.content if available
    if result.content and page.spans:
        page_texts = []
        for span in page.spans:
            if span.offset is not None and span.length is not None:
                text_chunk = result.content[span.offset:span.offset + span.length]
                page_texts.append(text_chunk)
        
        if page_texts:
            content = "".join(page_texts)
            logger.debug(f"Extracted {len(page_texts)} spans from page {page_number} ({len(content)} chars)")
            return content
    
    # Fallback: Extract from page.lines if spans not available
    if not page.lines:
        logger.warning(f"Page {page_number} has no lines detected")
        return ""
    
    # Concatenate all lines with spaces (lines are already separate text units)
    lines_text = [line.content for line in page.lines]
    content = " ".join(lines_text)
    
    logger.debug(f"Extracted {len(lines_text)} lines from page {page_number} ({len(content)} chars)")
    
    return content
