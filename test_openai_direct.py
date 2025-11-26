"""
Test OpenAI directly with content from a page that returned empty summary.
"""
import os
import sys
import json
from pathlib import Path

# Load environment variables
settings_path = Path(__file__).parent / "local.settings.json"
if settings_path.exists():
    with open(settings_path, 'r') as f:
        settings = json.load(f)
        for key, value in settings.get("Values", {}).items():
            os.environ.setdefault(key, value)

sys.path.insert(0, str(Path(__file__).parent))

from utils import storage_utils, openai_utils

def main():
    # Pick a page that had empty summary (page 10 for example)
    page_num = 10
    doc_id = "timken-v5"
    
    print(f"Testing OpenAI with content from {doc_id} page {page_num}")
    print("=" * 70)
    
    # Read the parsed page content
    page_data = storage_utils.read_json_blob("raw-pdfs", f"parsed-pages/{doc_id}/{page_num}.json")
    
    content = page_data.get("content", "")
    print(f"\nPage content length: {len(content)} characters")
    print(f"\nFirst 500 chars:")
    print(content[:500])
    print("\n" + "=" * 70)
    
    # Try to summarize it with OpenAI
    print("\nCalling OpenAI to summarize...")
    try:
        prompt = (
            "You are a helpful assistant that summarizes a single page of a PDF document. "
            "Write a concise summary in exactly 2 sentences. "
            "Focus only on the content in the provided page text. "
            "Do not mention that this is a summary or refer to the instructions."
        )
        summary = openai_utils.summarize_text(content, prompt, max_completion_tokens=512)
        print(f"\nOpenAI response:")
        print(f"Summary length: {len(summary)} characters")
        if summary:
            print(f"Summary: {summary}")
        else:
            print("⚠️  EMPTY SUMMARY RETURNED!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
