"""
Diagnose recent pipeline runs to check why summaries weren't generated.
"""
import os
import sys
import json
from pathlib import Path

# Load environment variables from local.settings.json
settings_path = Path(__file__).parent / "local.settings.json"
if settings_path.exists():
    with open(settings_path, 'r') as f:
        settings = json.load(f)
        for key, value in settings.get("Values", {}).items():
            os.environ.setdefault(key, value)

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent))

from utils import storage_utils

def check_document(doc_id: str):
    """Check the status of a document processing run."""
    print(f"\n{'='*70}")
    print(f"Checking document: {doc_id}")
    print(f"{'='*70}\n")
    
    # Check parsed pages
    print("📄 Parsed Pages:")
    print("-" * 70)
    from azure.storage.blob import BlobServiceClient
    from azure.identity import DefaultAzureCredential
    
    account_url = os.environ.get("BLOB_ACCOUNT_URL")
    credential = DefaultAzureCredential()
    blob_service = BlobServiceClient(account_url=account_url, credential=credential)
    container_client = blob_service.get_container_client("raw-pdfs")
    
    parsed_pages = []
    try:
        blobs = container_client.list_blobs(name_starts_with=f"parsed-pages/{doc_id}/")
        for blob in blobs:
            if blob.name.endswith('.json'):
                parsed_pages.append(blob.name)
                blob_client = container_client.get_blob_client(blob.name)
                content = blob_client.download_blob().readall()
                data = json.loads(content)
                print(f"\n{blob.name}:")
                print(f"  Content length: {data.get('length', 0)} characters")
                print(f"  Preview: {data.get('content', '')[:100]}...")
    except Exception as e:
        print(f"❌ Error reading parsed pages: {e}")
    
    if not parsed_pages:
        print("⚠️  No parsed pages found!")
        return
    
    print(f"\n✅ Found {len(parsed_pages)} parsed pages")
    
    # Check page summaries
    print(f"\n📝 Page Summaries:")
    print("-" * 70)
    summaries_container = blob_service.get_container_client("summaries")
    
    page_summaries = []
    try:
        blobs = summaries_container.list_blobs(name_starts_with=f"{doc_id}/pages/")
        for blob in blobs:
            if blob.name.endswith('.json'):
                page_summaries.append(blob.name)
                blob_client = summaries_container.get_blob_client(blob.name)
                content = blob_client.download_blob().readall()
                data = json.loads(content)
                print(f"\n{blob.name}:")
                print(f"  Status: {data.get('status', 'unknown')}")
                print(f"  Summary length: {len(data.get('summary', ''))} characters")
                if data.get('summary'):
                    print(f"  Summary: {data.get('summary')[:150]}...")
                else:
                    print(f"  ⚠️  WARNING: Empty summary!")
    except Exception as e:
        print(f"❌ Error reading page summaries: {e}")
    
    if not page_summaries:
        print("⚠️  No page summaries found!")
    else:
        print(f"\n✅ Found {len(page_summaries)} page summaries")
    
    # Check document summary
    print(f"\n📋 Document Summary:")
    print("-" * 70)
    try:
        doc_summary_path = f"{doc_id}.json"
        blob_client = summaries_container.get_blob_client(doc_summary_path)
        content = blob_client.download_blob().readall()
        data = json.loads(content)
        print(f"\nStatus: {data.get('status', 'unknown')}")
        print(f"Summary length: {len(data.get('summary', ''))} characters")
        if data.get('summary'):
            print(f"\nSummary preview:")
            print(data.get('summary')[:300])
        else:
            print("⚠️  WARNING: Empty document summary!")
    except Exception as e:
        print(f"❌ Error reading document summary: {e}")
    
    # Check report
    print(f"\n📊 Processing Report:")
    print("-" * 70)
    try:
        reports_container = blob_service.get_container_client("reports")
        report_path = f"{doc_id}.json"
        blob_client = reports_container.get_blob_client(report_path)
        content = blob_client.download_blob().readall()
        data = json.loads(content)
        print(f"\nDocument ID: {data.get('documentId')}")
        print(f"Page count: {data.get('pageCount')}")
        print(f"Status: {data.get('status')}")
        print(f"Processing time: {data.get('processingTimeSeconds')} seconds")
    except Exception as e:
        print(f"❌ Error reading report: {e}")
    
    print(f"\n{'='*70}\n")

def main():
    # Check the two most recent runs
    doc_ids = ["bbb-v1", "timken-v5"]
    
    for doc_id in doc_ids:
        check_document(doc_id)

if __name__ == "__main__":
    main()
