"""Test script to trigger a single page summary and observe logs."""
import logging
import requests
import json
import time

# Configure logging to see DEBUG messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test with a page that we know failed
payload = {
    "documentId": "timken-v5",
    "page": 10
}

print("🧪 Testing single page summary activity...")
print(f"   Document: {payload['documentId']}")
print(f"   Page: {payload['page']}")
print()

# Note: This would need the activity to be exposed as an HTTP trigger
# Instead, let's create a minimal test that imports and calls the activity directly

from activities.page_summary_activity import page_summary_impl

print("📤 Calling page_summary_impl directly...")
print()
print("⚠️  NOTE: The logs show finish_reason=length with empty content")
print("    This suggests the max_completion_tokens=512 is being hit")
print("    but something is causing the response to be empty.")
print()

try:
    result = page_summary_impl(payload["documentId"], payload["page"])
    
    print("✅ Activity completed!")
    print(f"   Status: {result.get('status')}")
    print(f"   Summary length: {len(result.get('summary', ''))}")
    print()
    
    if result.get('summary'):
        print(f"Summary: {result['summary']}")
    else:
        print("⚠️ EMPTY SUMMARY - This is the issue!")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
