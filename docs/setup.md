
# Local Setup

## Prerequisites

- Python **3.10+**
- Azure Functions Core Tools
- **Azurite** (local storage emulator)
- Azure Content Understanding resource (for OCR and document analysis)
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
    "CONTENT_UNDERSTANDING_ENDPOINT": "https://<your-content-understanding>.cognitiveservices.azure.com",
    "CONTENT_UNDERSTANDING_KEY": "<your-content-understanding-key>"
  }
}
```

### Azure Content Understanding Setup

The PDF splitting activity uses Azure Content Understanding for OCR and text extraction.
This enables processing of scanned documents and image-heavy PDFs.

1. Create an Azure Content Understanding resource in the Azure Portal
2. Deploy a model that supports the `prebuilt-documentSearch` analyzer
3. Copy the endpoint and key to your `local.settings.json`

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
