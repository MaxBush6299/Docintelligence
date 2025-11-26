#!/usr/bin/env python3
"""
Standalone Summary Regeneration Tool

Regenerates page and document summaries for already-processed documents
without rerunning the entire pipeline. Useful for:
- Fixing summaries after prompt changes
- Regenerating summaries after token limit adjustments
- Processing failed summaries without re-splitting PDFs

Usage:
    python regenerate_summaries.py <document_id>
    python regenerate_summaries.py <document_id> --pages 1-50
    python regenerate_summaries.py <document_id> --dry-run
"""

import argparse
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

# Import activity implementations directly
from activities.page_summary_activity import page_summary_impl
from activities.doc_summary_activity import doc_summary_impl
from utils import storage_utils


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def enumerate_parsed_pages(document_id: str) -> List[int]:
    """List all page numbers that have been parsed for a document.
    
    Args:
        document_id: Document identifier
        
    Returns:
        Sorted list of page numbers
        
    Raises:
        ValueError: If no parsed pages found
    """
    logger.info(f"Enumerating parsed pages for document: {document_id}")
    
    # Get blob service client
    account_url = os.environ.get("BLOB_ACCOUNT_URL")
    if not account_url:
        raise RuntimeError("BLOB_ACCOUNT_URL environment variable must be set")
    
    credential = DefaultAzureCredential()
    blob_service = BlobServiceClient(account_url=account_url, credential=credential)
    container_client = blob_service.get_container_client("raw-pdfs")
    
    # List all parsed page blobs
    prefix = f"parsed-pages/{document_id}/"
    blobs = container_client.list_blobs(name_starts_with=prefix)
    
    page_numbers = []
    for blob in blobs:
        if blob.name.endswith('.json'):
            # Extract page number from "parsed-pages/{doc_id}/{page}.json"
            try:
                page_str = blob.name.split('/')[-1].replace('.json', '')
                page_num = int(page_str)
                page_numbers.append(page_num)
            except (ValueError, IndexError):
                logger.warning(f"Could not extract page number from blob: {blob.name}")
                continue
    
    if not page_numbers:
        raise ValueError(f"No parsed pages found for document '{document_id}' in container 'raw-pdfs'")
    
    page_numbers.sort()
    logger.info(f"Found {len(page_numbers)} parsed pages: {page_numbers[0]}-{page_numbers[-1]}")
    
    return page_numbers


def process_pages_batch(
    document_id: str,
    page_numbers: List[int],
    max_workers: int = 32,
    dry_run: bool = False
) -> List[Dict[str, Any]]:
    """Process page summaries in parallel batches.
    
    Args:
        document_id: Document identifier
        page_numbers: List of page numbers to process
        max_workers: Maximum concurrent workers (default from OPENAI_MAX_CONCURRENCY)
        dry_run: If True, skip actual processing and just report what would happen
        
    Returns:
        List of page summary results
    """
    logger.info(f"Processing {len(page_numbers)} pages with max {max_workers} concurrent workers")
    
    if dry_run:
        logger.info("DRY RUN: Would process pages but skipping actual OpenAI calls")
        return [
            {
                "documentId": document_id,
                "page": page_num,
                "status": "dry-run",
                "summary": "[Dry run - not actually processed]"
            }
            for page_num in page_numbers
        ]
    
    results = []
    completed = 0
    total = len(page_numbers)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(page_summary_impl, document_id, page_num): page_num
            for page_num in page_numbers
        }
        
        # Collect results with progress
        for future in as_completed(futures):
            page_num = futures[future]
            completed += 1
            
            try:
                result = future.result()
                status = result.get('status', 'unknown')
                summary_len = len(result.get('summary', ''))
                
                if status == 'success':
                    logger.info(f"✓ [{completed}/{total}] Page {page_num}: {status} ({summary_len} chars)")
                elif status == 'skipped':
                    logger.warning(f"⊘ [{completed}/{total}] Page {page_num}: {status} (no content)")
                else:
                    logger.error(f"✗ [{completed}/{total}] Page {page_num}: {status}")
                
                results.append(result)
                
            except Exception as exc:
                logger.error(f"✗ [{completed}/{total}] Page {page_num} failed: {exc}")
                results.append({
                    "documentId": document_id,
                    "page": page_num,
                    "status": "failed",
                    "error": str(exc)
                })
    
    return results


def generate_document_summary(
    document_id: str,
    page_results: List[Dict[str, Any]],
    dry_run: bool = False
) -> Optional[Dict[str, Any]]:
    """Generate document-level summary from page summaries.
    
    Args:
        document_id: Document identifier
        page_results: List of page summary results
        dry_run: If True, skip actual processing
        
    Returns:
        Document summary result or None if no successful pages
    """
    # Filter successful pages
    successful = [r for r in page_results if r.get('status') == 'success']
    
    if not successful:
        logger.error("Cannot generate document summary - no successful page summaries")
        return None
    
    if dry_run:
        logger.info(f"DRY RUN: Would generate document summary from {len(successful)} page summaries")
        return {
            "documentId": document_id,
            "status": "dry-run",
            "summary": "[Dry run - not actually generated]"
        }
    
    logger.info(f"Generating document summary from {len(successful)} page summaries")
    
    try:
        result = doc_summary_impl(document_id, successful)
        summary_len = len(result.get('summary', ''))
        logger.info(f"✓ Document summary generated ({summary_len} chars)")
        return result
    except Exception as exc:
        logger.error(f"✗ Document summary generation failed: {exc}")
        return {
            "documentId": document_id,
            "status": "failed",
            "error": str(exc)
        }


def parse_page_range(range_str: str) -> Tuple[int, int]:
    """Parse page range string like '1-50' into (start, end) tuple.
    
    Args:
        range_str: Page range string (e.g., '1-50' or '10-20')
        
    Returns:
        Tuple of (start_page, end_page) inclusive
        
    Raises:
        ValueError: If range format is invalid
    """
    if '-' not in range_str:
        raise ValueError("Page range must be in format 'start-end' (e.g., '1-50')")
    
    parts = range_str.split('-')
    if len(parts) != 2:
        raise ValueError("Page range must have exactly one hyphen")
    
    try:
        start = int(parts[0].strip())
        end = int(parts[1].strip())
    except ValueError:
        raise ValueError("Page range start and end must be integers")
    
    if start < 1 or end < 1:
        raise ValueError("Page numbers must be positive integers")
    
    if start > end:
        raise ValueError(f"Invalid range: start ({start}) > end ({end})")
    
    return (start, end)


def regenerate_summaries(
    document_id: str,
    page_range: Optional[Tuple[int, int]] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Main entry point for summary regeneration.
    
    Args:
        document_id: Document identifier
        page_range: Optional (start, end) page range to process
        dry_run: If True, preview what would happen without actually processing
        
    Returns:
        Summary of results
    """
    logger.info("=" * 80)
    logger.info(f"Summary Regeneration for Document: {document_id}")
    if dry_run:
        logger.info("MODE: DRY RUN (no actual processing)")
    logger.info("=" * 80)
    
    # 1. Enumerate pages
    try:
        all_pages = enumerate_parsed_pages(document_id)
    except Exception as exc:
        logger.error(f"Failed to enumerate pages: {exc}")
        return {
            "documentId": document_id,
            "status": "failed",
            "error": str(exc)
        }
    
    # Apply page range filter if specified
    if page_range:
        start, end = page_range
        pages_to_process = [p for p in all_pages if start <= p <= end]
        logger.info(f"Filtering to page range {start}-{end}: {len(pages_to_process)} pages")
        
        if not pages_to_process:
            logger.error(f"No pages found in range {start}-{end}")
            return {
                "documentId": document_id,
                "status": "failed",
                "error": f"No pages in range {start}-{end}"
            }
    else:
        pages_to_process = all_pages
    
    # 2. Process page summaries
    max_concurrency = int(os.environ.get("OPENAI_MAX_CONCURRENCY", "32"))
    
    logger.info("")
    logger.info("Processing page summaries...")
    logger.info("-" * 80)
    
    page_results = process_pages_batch(
        document_id,
        pages_to_process,
        max_workers=max_concurrency,
        dry_run=dry_run
    )
    
    # 3. Analyze results
    successful = [r for r in page_results if r.get('status') == 'success']
    skipped = [r for r in page_results if r.get('status') == 'skipped']
    failed = [r for r in page_results if r.get('status') not in ['success', 'skipped', 'dry-run']]
    
    logger.info("")
    logger.info("Page Summary Results:")
    logger.info(f"  ✓ Successful: {len(successful)}")
    logger.info(f"  ⊘ Skipped (no content): {len(skipped)}")
    logger.info(f"  ✗ Failed: {len(failed)}")
    
    if failed:
        logger.warning(f"Failed pages: {[r['page'] for r in failed]}")
    
    # 4. Generate document summary
    logger.info("")
    logger.info("Generating document summary...")
    logger.info("-" * 80)
    
    doc_summary = None
    if successful or dry_run:
        doc_summary = generate_document_summary(document_id, page_results, dry_run)
    else:
        logger.error("Cannot generate document summary - no successful page summaries")
    
    # 5. Final summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("Summary Regeneration Complete")
    logger.info("=" * 80)
    
    return {
        "documentId": document_id,
        "totalPages": len(pages_to_process),
        "successfulPages": len(successful),
        "skippedPages": len(skipped),
        "failedPages": len(failed),
        "documentSummaryGenerated": doc_summary is not None and doc_summary.get('status') == 'success',
        "dryRun": dry_run
    }


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Regenerate summaries for already-processed documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Regenerate all summaries for a document
  python regenerate_summaries.py timken-v5
  
  # Regenerate summaries for specific page range
  python regenerate_summaries.py timken-v5 --pages 1-50
  
  # Preview what would be regenerated (dry run)
  python regenerate_summaries.py timken-v5 --dry-run
  
  # Regenerate with custom concurrency
  SET OPENAI_MAX_CONCURRENCY=16
  python regenerate_summaries.py timken-v5
        """
    )
    
    parser.add_argument(
        'document_id',
        help='Document identifier (e.g., timken-v5, bbb-v1)'
    )
    
    parser.add_argument(
        '--pages',
        help='Page range to process (e.g., 1-50). Default: all pages',
        type=str,
        default=None
    )
    
    parser.add_argument(
        '--dry-run',
        help='Preview what would be regenerated without actually processing',
        action='store_true'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        help='Enable verbose logging',
        action='store_true'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parse page range if provided
    page_range = None
    if args.pages:
        try:
            page_range = parse_page_range(args.pages)
        except ValueError as exc:
            logger.error(f"Invalid page range: {exc}")
            sys.exit(1)
    
    # Run regeneration
    try:
        result = regenerate_summaries(
            args.document_id,
            page_range=page_range,
            dry_run=args.dry_run
        )
        
        # Exit code based on success
        if result.get('failedPages', 0) > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
        sys.exit(130)
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
