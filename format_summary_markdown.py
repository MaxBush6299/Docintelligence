#!/usr/bin/env python3
"""
Document Summary Markdown Formatter

Pulls document summaries from blob storage and formats them into well-structured
markdown files. Can process single documents or batch process multiple documents.

Usage:
    python format_summary_markdown.py <document_id>
    python format_summary_markdown.py <document_id> --output summary.md
    python format_summary_markdown.py --all --output-dir summaries/
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_blob_service_client() -> BlobServiceClient:
    """Get authenticated blob service client."""
    account_url = os.environ.get("BLOB_ACCOUNT_URL")
    if not account_url:
        raise RuntimeError("BLOB_ACCOUNT_URL environment variable must be set")
    
    credential = DefaultAzureCredential()
    return BlobServiceClient(account_url=account_url, credential=credential)


def fetch_document_summary(document_id: str) -> Optional[Dict[str, Any]]:
    """Fetch document summary from blob storage.
    
    Args:
        document_id: Document identifier
        
    Returns:
        Document summary data or None if not found
    """
    try:
        blob_service = get_blob_service_client()
        container_client = blob_service.get_container_client("summaries")
        blob_client = container_client.get_blob_client(f"{document_id}.json")
        
        blob_data = blob_client.download_blob().readall()
        summary_data = json.loads(blob_data)
        
        return summary_data
    except Exception as exc:
        logger.error(f"Failed to fetch summary for {document_id}: {exc}")
        return None


def fetch_page_summaries(document_id: str) -> List[Dict[str, Any]]:
    """Fetch all page summaries for a document.
    
    Args:
        document_id: Document identifier
        
    Returns:
        List of page summary data dictionaries
    """
    try:
        blob_service = get_blob_service_client()
        container_client = blob_service.get_container_client("summaries")
        
        # List all page summary blobs
        prefix = f"{document_id}/pages/"
        blobs = container_client.list_blobs(name_starts_with=prefix)
        
        page_summaries = []
        for blob in blobs:
            if blob.name.endswith('.json'):
                blob_client = container_client.get_blob_client(blob.name)
                blob_data = blob_client.download_blob().readall()
                page_data = json.loads(blob_data)
                page_summaries.append(page_data)
        
        # Sort by page number
        page_summaries.sort(key=lambda x: x.get('page', 0))
        
        return page_summaries
    except Exception as exc:
        logger.error(f"Failed to fetch page summaries for {document_id}: {exc}")
        return []


def list_all_documents() -> List[str]:
    """List all documents that have summaries.
    
    Returns:
        List of document IDs
    """
    try:
        blob_service = get_blob_service_client()
        container_client = blob_service.get_container_client("summaries")
        
        # Find all document-level summary blobs (not in pages/ subdirectory)
        blobs = container_client.list_blobs()
        
        document_ids = []
        for blob in blobs:
            if blob.name.endswith('.json') and '/' not in blob.name:
                # Extract document ID from filename
                doc_id = blob.name.replace('.json', '')
                document_ids.append(doc_id)
        
        return sorted(document_ids)
    except Exception as exc:
        logger.error(f"Failed to list documents: {exc}")
        return []


def format_document_summary_markdown(
    document_id: str,
    summary_data: Dict[str, Any],
    page_summaries: Optional[List[Dict[str, Any]]] = None,
    include_page_details: bool = True
) -> str:
    """Format document summary as markdown.
    
    Args:
        document_id: Document identifier
        summary_data: Document summary data
        page_summaries: Optional list of page summaries for detailed section
        include_page_details: Whether to include per-page summary details
        
    Returns:
        Formatted markdown string
    """
    lines = []
    
    # Header
    lines.append(f"# Document Summary: {document_id}")
    lines.append("")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Status badge
    status = summary_data.get('status', 'unknown')
    if status == 'success':
        lines.append("**Status:** ✅ Success")
    elif status == 'failed':
        lines.append("**Status:** ❌ Failed")
    else:
        lines.append(f"**Status:** {status}")
    lines.append("")
    
    # Document-level summary
    lines.append("## Executive Summary")
    lines.append("")
    summary_text = summary_data.get('summary', '')
    
    if summary_text:
        # Split into paragraphs for better formatting
        paragraphs = summary_text.split('\n\n')
        for para in paragraphs:
            if para.strip():
                lines.append(para.strip())
                lines.append("")
    else:
        lines.append("*No summary available*")
        lines.append("")
    
    # Error information if failed
    if status == 'failed' and 'error' in summary_data:
        lines.append("## Error Details")
        lines.append("")
        lines.append("```")
        lines.append(summary_data['error'])
        lines.append("```")
        lines.append("")
    
    # Page-level details
    if include_page_details and page_summaries:
        lines.append("---")
        lines.append("")
        lines.append("## Page-by-Page Summaries")
        lines.append("")
        
        successful_pages = [p for p in page_summaries if p.get('status') == 'success']
        skipped_pages = [p for p in page_summaries if p.get('status') == 'skipped']
        failed_pages = [p for p in page_summaries if p.get('status') == 'failed']
        
        # Summary statistics
        lines.append(f"**Total Pages:** {len(page_summaries)}")
        lines.append(f"- ✅ Successful: {len(successful_pages)}")
        lines.append(f"- ⊘ Skipped (no content): {len(skipped_pages)}")
        lines.append(f"- ❌ Failed: {len(failed_pages)}")
        lines.append("")
        
        # Successful page summaries
        if successful_pages:
            lines.append("### Content Summaries")
            lines.append("")
            
            for page_data in successful_pages:
                page_num = page_data.get('page', '?')
                page_summary = page_data.get('summary', '').strip()
                
                lines.append(f"#### Page {page_num}")
                lines.append("")
                lines.append(page_summary)
                lines.append("")
        
        # Skipped pages
        if skipped_pages:
            lines.append("### Skipped Pages")
            lines.append("")
            skipped_nums = [str(p.get('page', '?')) for p in skipped_pages]
            lines.append(f"Pages with no extractable content: {', '.join(skipped_nums)}")
            lines.append("")
        
        # Failed pages
        if failed_pages:
            lines.append("### Failed Pages")
            lines.append("")
            for page_data in failed_pages:
                page_num = page_data.get('page', '?')
                error = page_data.get('error', 'Unknown error')
                lines.append(f"- **Page {page_num}:** {error}")
            lines.append("")
    
    # Metadata
    lines.append("---")
    lines.append("")
    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- **Document ID:** `{document_id}`")
    
    if page_summaries:
        lines.append(f"- **Total Pages:** {len(page_summaries)}")
    
    if 'summaryBlob' in summary_data:
        lines.append(f"- **Summary Blob:** `{summary_data['summaryBlob']}`")
    
    lines.append("")
    
    return '\n'.join(lines)


def save_markdown(content: str, output_path: str) -> None:
    """Save markdown content to file.
    
    Args:
        content: Markdown content
        output_path: Path to save file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    output_file.write_text(content, encoding='utf-8')
    logger.info(f"Saved markdown to: {output_path}")


def format_single_document(
    document_id: str,
    output_path: Optional[str] = None,
    include_page_details: bool = True
) -> bool:
    """Format a single document summary as markdown.
    
    Args:
        document_id: Document identifier
        output_path: Optional output file path (default: {document_id}_summary.md)
        include_page_details: Whether to include per-page summaries
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Fetching summary for document: {document_id}")
    
    # Fetch document summary
    summary_data = fetch_document_summary(document_id)
    if not summary_data:
        logger.error(f"No summary found for document: {document_id}")
        return False
    
    # Fetch page summaries if requested
    page_summaries = None
    if include_page_details:
        logger.info(f"Fetching page summaries for: {document_id}")
        page_summaries = fetch_page_summaries(document_id)
        if page_summaries:
            logger.info(f"Found {len(page_summaries)} page summaries")
    
    # Format as markdown
    markdown_content = format_document_summary_markdown(
        document_id,
        summary_data,
        page_summaries,
        include_page_details
    )
    
    # Determine output path
    if not output_path:
        output_path = f"{document_id}_summary.md"
    
    # Save to file
    save_markdown(markdown_content, output_path)
    
    return True


def format_all_documents(
    output_dir: str = "summaries",
    include_page_details: bool = True
) -> Dict[str, bool]:
    """Format all available document summaries as markdown.
    
    Args:
        output_dir: Directory to save markdown files
        include_page_details: Whether to include per-page summaries
        
    Returns:
        Dictionary mapping document IDs to success status
    """
    logger.info("Listing all available documents...")
    document_ids = list_all_documents()
    
    if not document_ids:
        logger.warning("No documents found")
        return {}
    
    logger.info(f"Found {len(document_ids)} documents")
    
    results = {}
    for doc_id in document_ids:
        output_path = os.path.join(output_dir, f"{doc_id}_summary.md")
        success = format_single_document(doc_id, output_path, include_page_details)
        results[doc_id] = success
    
    # Summary
    successful = sum(1 for v in results.values() if v)
    logger.info(f"Completed: {successful}/{len(results)} documents formatted successfully")
    
    return results


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Format document summaries as markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Format a single document summary
  python format_summary_markdown.py timken-v5
  
  # Format with custom output path
  python format_summary_markdown.py timken-v5 --output reports/timken.md
  
  # Format without page-level details (executive summary only)
  python format_summary_markdown.py timken-v5 --no-pages
  
  # Format all available documents
  python format_summary_markdown.py --all --output-dir markdown_summaries/
        """
    )
    
    parser.add_argument(
        'document_id',
        nargs='?',
        help='Document identifier (e.g., timken-v5, bbb-v1). Omit if using --all'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output markdown file path (default: {document_id}_summary.md)',
        type=str,
        default=None
    )
    
    parser.add_argument(
        '--all',
        help='Format all available documents',
        action='store_true'
    )
    
    parser.add_argument(
        '--output-dir',
        help='Output directory for --all mode (default: summaries)',
        type=str,
        default='summaries'
    )
    
    parser.add_argument(
        '--no-pages',
        help='Exclude page-level summaries (executive summary only)',
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
    
    # Validate arguments
    if args.all:
        # Format all documents
        results = format_all_documents(
            output_dir=args.output_dir,
            include_page_details=not args.no_pages
        )
        
        # Exit code based on results
        if not results:
            sys.exit(1)
        
        failed = sum(1 for v in results.values() if not v)
        sys.exit(1 if failed > 0 else 0)
    
    elif args.document_id:
        # Format single document
        success = format_single_document(
            args.document_id,
            output_path=args.output,
            include_page_details=not args.no_pages
        )
        
        sys.exit(0 if success else 1)
    
    else:
        parser.error("Either provide a document_id or use --all flag")


if __name__ == "__main__":
    main()
