import os
import json
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI

# Configuration from local.settings.json
STORAGE_ACCOUNT_NAME = "sadocint123"
DOCUMENT_ID = "timken-v5"
PAGE_NUMBER = 10

# Set up environment for Azure credentials
os.environ["AZURE_STORAGE_ACCOUNT"] = STORAGE_ACCOUNT_NAME

# Initialize with connection string or account key
blob_service_client = BlobServiceClient(
    account_url=f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
    credential=DefaultAzureCredential()
)

print(f"Fetching page {PAGE_NUMBER} content from raw-pdfs/parsed-pages/{DOCUMENT_ID}/{PAGE_NUMBER}.json...")

try:
    container_client = blob_service_client.get_container_client("raw-pdfs")
    blob_client = container_client.get_blob_client(f"parsed-pages/{DOCUMENT_ID}/{PAGE_NUMBER}.json")
    blob_data = blob_client.download_blob().readall()
    page_data = json.loads(blob_data)
    
    # Get content the same way the activity does
    text = page_data.get("content") or page_data.get("text") or ""
    
    print(f"✅ Retrieved page data")
    print(f"   Content length: {len(text)} characters")
    print(f"   Content type: {type(text)}")
    print(f"   Content preview: {text[:200]}...")
    print()
    
    # Now test with OpenAI using the EXACT same parameters as the activity
    endpoint = "https://fa-docint123-openai-a437.openai.azure.com/"
    api_key = "0913efbc8e03439ea3f3d11166887f11"
    deployment = "gpt-5"
    
    client = AzureOpenAI(
        api_key=api_key,
        api_version="2025-01-01-preview",
        azure_endpoint=endpoint,
    )
    
    # Build prompt exactly as page_summary_activity does
    sentences = 2  # PAGE_SUMMARY_SENTENCES default
    prompt = (
        "You are a helpful assistant that summarizes a single page of a PDF document. "
        f"Write a concise summary in exactly {sentences} sentences. "
        "Focus only on the content in the provided page text. "
        "Do not mention that this is a summary or refer to the instructions."
    )
    
    print(f"📤 Calling OpenAI with:")
    print(f"   Deployment: {deployment}")
    print(f"   Prompt: {prompt[:100]}...")
    print(f"   Text length: {len(text)}")
    print(f"   Max tokens: 512")
    print()
    
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        max_completion_tokens=512,
    )
    
    print("✅ Response received!")
    print(f"   Finish reason: {response.choices[0].finish_reason}")
    print(f"   Content type: {type(response.choices[0].message.content)}")
    print(f"   Content is None: {response.choices[0].message.content is None}")
    print(f"   Content length: {len(response.choices[0].message.content or '')}")
    print()
    
    summary = (response.choices[0].message.content or "").strip()
    
    if summary:
        print(f"✅ SUCCESS! Summary generated ({len(summary)} chars):")
        print(summary)
    else:
        print("⚠️ EMPTY SUMMARY!")
        print("This is the exact same issue happening in production")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
