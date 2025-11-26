"""
Utility functions for Azure Content Understanding integration.

Uses the prebuilt-documentSearch analyzer for OCR, layout analysis,
figure descriptions, and document summarization.
"""

import os
import time
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_endpoint_and_key() -> tuple[str, str]:
    """Get Content Understanding endpoint and key from environment variables."""
    endpoint = os.environ.get("CONTENT_UNDERSTANDING_ENDPOINT")
    key = os.environ.get("CONTENT_UNDERSTANDING_KEY")
    
    if not endpoint:
        raise ValueError("CONTENT_UNDERSTANDING_ENDPOINT environment variable is not set")
    if not key:
        raise ValueError("CONTENT_UNDERSTANDING_KEY environment variable is not set")
    
    # Remove trailing slash if present
    endpoint = endpoint.rstrip("/")
    return endpoint, key


def _get_headers(key: str, content_type: str = "application/octet-stream") -> dict:
    """Build headers for Content Understanding API requests."""
    return {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": content_type,
    }


async def analyze_document(
    pdf_bytes: bytes,
    polling_interval: float = 2.0,
    max_wait_time: float = 600.0,  # 10 minutes max for large documents
) -> dict:
    """
    Analyze a PDF document using Azure Content Understanding prebuilt-documentSearch analyzer.
    
    This function:
    1. Submits the PDF for analysis
    2. Polls the operation status until complete
    3. Returns the full analysis result
    
    Args:
        pdf_bytes: The PDF file content as bytes
        polling_interval: Seconds between status checks (default 2.0)
        max_wait_time: Maximum seconds to wait for completion (default 600)
        
    Returns:
        dict: The analysis result containing:
            - contents: List of content items with Markdown text
            - figures: List of detected figures with descriptions
            - summary: Document summary (if generated)
            - pages: Page-level information
            
    Raises:
        ValueError: If environment variables are not set
        httpx.HTTPStatusError: If API request fails
        TimeoutError: If analysis exceeds max_wait_time
    """
    endpoint, key = _get_endpoint_and_key()
    
    # API URL for prebuilt-document analyzer (the general document analyzer)
    # Note: prebuilt-documentSearch is NOT available - use prebuilt-document instead
    analyze_url = f"{endpoint}/contentunderstanding/analyzers/prebuilt-document:analyze?api-version=2025-11-01"
    
    headers = _get_headers(key, content_type="application/octet-stream")
    
    logger.info(f"Submitting PDF for analysis: endpoint={endpoint}, size={len(pdf_bytes)} bytes")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Submit the document for analysis
        try:
            response = await client.post(
                analyze_url,
                headers=headers,
                content=pdf_bytes,
            )
            logger.info(f"API response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            if response.status_code >= 400:
                try:
                    error_body = response.text
                    logger.error(f"API error response body: {error_body}")
                except Exception as e:
                    logger.error(f"Could not read error body: {e}")
            
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error submitting document: {e}")
            logger.error(f"Request URL: {e.request.url}")
            logger.error(f"Request headers: {dict(e.request.headers)}")
            raise
        
        # Get the operation location for polling
        operation_location = response.headers.get("Operation-Location")
        if not operation_location:
            raise ValueError("No Operation-Location header in response")
        
        logger.info(f"Got operation location: {operation_location}")
        
        # Poll until complete
        poll_headers = {"Ocp-Apim-Subscription-Key": key}
        elapsed = 0.0
        
        while elapsed < max_wait_time:
            await _async_sleep(polling_interval)
            elapsed += polling_interval
            
            status_response = await client.get(operation_location, headers=poll_headers)
            status_response.raise_for_status()
            
            result = status_response.json()
            status = result.get("status", "").lower()
            
            logger.debug(f"Poll status after {elapsed:.1f}s: {status}")
            
            if status == "succeeded":
                return result.get("result", result)
            elif status == "failed":
                error = result.get("error", {})
                raise RuntimeError(
                    f"Content Understanding analysis failed: {error.get('message', 'Unknown error')}"
                )
            elif status in ("notstarted", "running"):
                continue
            else:
                # Unknown status, keep polling
                continue
        
        raise TimeoutError(
            f"Content Understanding analysis timed out after {max_wait_time} seconds"
        )


async def _async_sleep(seconds: float):
    """Async sleep helper."""
    import asyncio
    await asyncio.sleep(seconds)


def get_total_pages(result: dict) -> int:
    """
    Get the total number of pages from a Content Understanding result.
    
    Args:
        result: The analysis result from analyze_document()
        
    Returns:
        int: Total number of pages in the document
    """
    # Check for pages array
    pages = result.get("pages", [])
    if pages:
        return len(pages)
    
    # Fallback: check contents for page references
    contents = result.get("contents", [])
    max_page = 0
    for content in contents:
        page_number = content.get("pageNumber", 0)
        if page_number > max_page:
            max_page = page_number
    
    return max_page if max_page > 0 else 1


def get_page_content(result: dict, page_number: int) -> str:
    """
    Extract the text content for a specific page from Content Understanding result.
    
    The content is returned as Markdown text, which includes:
    - OCR-extracted text
    - Table structures
    - Figure descriptions (inline)
    
    Args:
        result: The analysis result from analyze_document()
        page_number: 1-based page number to extract
        
    Returns:
        str: The Markdown content for the specified page, or empty string if not found
    """
    contents = result.get("contents", [])
    
    # Collect all content items for this page
    page_contents = []
    for content in contents:
        content_page = content.get("pageNumber", 0)
        if content_page == page_number:
            markdown = content.get("markdown", content.get("text", ""))
            if markdown:
                page_contents.append(markdown)
    
    if page_contents:
        return "\n\n".join(page_contents)
    
    # Fallback: try to extract from the main markdown content
    # Some responses have a single markdown field with all content
    main_markdown = result.get("markdown", "")
    if main_markdown:
        # The main markdown might have page markers or we return it all
        # For now, return an empty string if we can't find page-specific content
        pass
    
    return ""


def get_document_summary(result: dict) -> Optional[str]:
    """
    Get the document-level summary from Content Understanding result.
    
    The prebuilt-documentSearch analyzer generates a one-paragraph summary
    of the entire document when using generative features.
    
    Args:
        result: The analysis result from analyze_document()
        
    Returns:
        str or None: The document summary, or None if not available
    """
    # Check for summary field
    summary = result.get("summary")
    if summary:
        return summary
    
    # Check in metadata or other locations
    metadata = result.get("metadata", {})
    if metadata.get("summary"):
        return metadata["summary"]
    
    return None


def get_figures(result: dict) -> list[dict]:
    """
    Get all detected figures with their descriptions from the result.
    
    Args:
        result: The analysis result from analyze_document()
        
    Returns:
        list: List of figure dictionaries with 'pageNumber', 'description', etc.
    """
    return result.get("figures", [])


def get_page_figures(result: dict, page_number: int) -> list[dict]:
    """
    Get figures from a specific page.
    
    Args:
        result: The analysis result from analyze_document()
        page_number: 1-based page number
        
    Returns:
        list: List of figure dictionaries for the specified page
    """
    figures = get_figures(result)
    return [f for f in figures if f.get("pageNumber") == page_number]
