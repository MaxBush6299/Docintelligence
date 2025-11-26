
# Local Setup

## Prerequisites

- Python **3.10+**
- Azure Functions Core Tools
- **Azurite** (local storage emulator)
- Azure Document Intelligence resource (S0 tier recommended for files up to 500 MB)
- (Optional) Docker if you prefer containerized local dev

## 1) Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

## 2) Install dependencies

```bash
pip install -r requirements.txt
```

## 3) Configure local settings

Edit `local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_OPENAI_ENDPOINT": "https://<your-endpoint>.openai.azure.com",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4.1",
    "AZURE_OPENAI_API_KEY": "<your-key-or-use-MI>",
    "COSMOS_ENDPOINT": "https://<your-account>.documents.azure.com:443/",
    "COSMOS_DB": "docsum",
    "COSMOS_KEY": "<your-key-or-use-MI>",
    "BLOB_ACCOUNT_URL": "https://<your-storage>.blob.core.windows.net",
    "OPENAI_MAX_CONCURRENCY": "32",
    "DOCUMENT_INTELLIGENCE_ENDPOINT": "https://<your-resource>.cognitiveservices.azure.com/",
    "DOCUMENT_INTELLIGENCE_KEY": "<your-key>"
  }
}
```

### Azure Document Intelligence Setup

The PDF splitting activity uses Azure Document Intelligence v4.0 (API version 2024-11-30 GA) for text extraction.
The prebuilt-read model provides accurate text extraction with span-based content parsing.

1. Create an Azure Document Intelligence resource in the Azure Portal
   - Choose **S0 tier** for production workloads (supports PDFs up to 500 MB)
   - Free tier (F0) supports up to 4 MB files
2. Copy the endpoint and key to your `local.settings.json`
3. No model deployment needed - prebuilt-read is available out-of-the-box

## 4) Start services

In separate terminals:

```bash
azurite
func start
```

## 5) Run a test

```http
POST http://localhost:7071/api/process-document
Content-Type: application/json

{
  "documentId": "doc001",
  "blobPath": "raw-pdfs/doc001.pdf"
}
```

You’ll get Durable status URLs back. Use them to track progress.
