import os
import json
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI

# Configuration
STORAGE_ACCOUNT_NAME = "docintelligencestg"
DOCUMENT_ID = "timken-v5"
PAGE_NUMBER = 10  # Test with a page that failed

# Initialize blob client
credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(
    account_url=f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
    credential=credential
)

# Get page content from parsed-pages
print(f"Fetching page {PAGE_NUMBER} content from blob storage...")
container_client = blob_service_client.get_container_client("raw-pdfs")
blob_client = container_client.get_blob_client(f"parsed-pages/{DOCUMENT_ID}/{PAGE_NUMBER}.json")
page_data = json.loads(blob_client.download_blob().readall())
content = page_data.get("content", "")

print(f"✅ Page content length: {len(content)} characters")
print(f"Content preview: {content[:200]}...\n")

# Initialize OpenAI client
endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
api_key = os.environ.get("AZURE_OPENAI_API_KEY")
deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")

if not endpoint or not deployment:
    print("❌ Error: AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT must be set")
    exit(1)

print(f"🔧 OpenAI Configuration:")
print(f"   Endpoint: {endpoint}")
print(f"   Deployment: {deployment}")
print(f"   API Version: 2025-01-01-preview\n")

client = AzureOpenAI(
    api_key=api_key,
    api_version="2025-01-01-preview",
    azure_endpoint=endpoint,
)

# Test with the same prompt used in production
prompt = """You are a helpful assistant that summarizes technical documentation.
Provide a clear and concise summary of the following page content in 2-3 sentences."""

print("📤 Sending request to Azure OpenAI...\n")

try:
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": content},
        ],
        max_completion_tokens=512,
    )
    
    print("✅ Response received successfully!\n")
    print("=" * 80)
    print("FULL RESPONSE DETAILS:")
    print("=" * 80)
    print(f"Response ID: {response.id}")
    print(f"Model: {response.model}")
    print(f"Created: {response.created}")
    print(f"Number of choices: {len(response.choices)}")
    print()
    
    if response.choices:
        choice = response.choices[0]
        print(f"Choice 0:")
        print(f"  Finish reason: {choice.finish_reason}")
        print(f"  Message role: {choice.message.role}")
        print(f"  Message content type: {type(choice.message.content)}")
        print(f"  Message content is None: {choice.message.content is None}")
        print(f"  Message content length: {len(choice.message.content) if choice.message.content else 0}")
        print(f"  Message content repr: {repr(choice.message.content)[:500]}")
        print()
        
        # Check for content filter
        if hasattr(choice, 'content_filter_results'):
            print(f"  Content filter results: {choice.content_filter_results}")
        
    # Check usage
    if hasattr(response, 'usage') and response.usage:
        print(f"Token usage:")
        print(f"  Prompt tokens: {response.usage.prompt_tokens}")
        print(f"  Completion tokens: {response.usage.completion_tokens}")
        print(f"  Total tokens: {response.usage.total_tokens}")
    
    print("=" * 80)
    
    # Extract summary
    summary = response.choices[0].message.content
    if summary:
        print(f"\n✅ SUMMARY ({len(summary)} chars):")
        print(summary)
    else:
        print("\n⚠️ WARNING: EMPTY SUMMARY RETURNED!")
        print("This confirms the issue - OpenAI is returning an empty/null content field.")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
