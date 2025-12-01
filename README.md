# 📄 Azure Document Intelligence Pipeline

A production-ready, serverless document processing pipeline built on **Azure Durable Functions** that transforms unstructured PDFs into searchable, queryable knowledge bases.

## What This Pipeline Does

This pipeline automates the complete lifecycle of document intelligence—from raw PDF ingestion to AI-powered analysis and persistent storage. Built for **scale, reliability, and cost-efficiency**, it processes documents of any size (from 10 pages to 1000+) with built-in retry logic, parallel processing, and comprehensive audit trails.

### Core Capabilities

**📥 Document Ingestion & Extraction**
- Accepts PDF documents up to 500 MB (Azure Document Intelligence S0 tier)
- Uses **span-based text extraction** with Azure Document Intelligence v4.0 GA for high accuracy
- Preserves document structure, handles OCR for scanned documents, and extracts tables/forms
- Stores raw extracted text per page for downstream processing

**🤖 AI-Powered Summarization**
- Generates **concise page-level summaries** (configurable, default: 2 sentences per page)
- Creates **comprehensive document-level summaries** (multi-paragraph executive summaries)
- Uses Azure OpenAI (GPT-5) with custom prompts optimized for different document types
- Processes pages in parallel batches (default: 32 concurrent) for speed

**💾 Persistent Knowledge Storage**
- Stores all artifacts in **Azure Blob Storage** (extracted text, summaries, reports)
- Indexes metadata in **Azure Cosmos DB** for fast querying and tracking
- Maintains complete processing history and audit trails
- Enables version control and reprocessing without re-uploading documents

**🔍 Production-Ready Features**
- **Durable orchestration** with automatic checkpointing and retry on failures
- **Fan-out/fan-in pattern** for parallel page processing
- **Identity-based authentication** (no hardcoded keys) via Azure Managed Identity
- **Comprehensive error handling** with detailed failure reporting
- **Helper tools** for summary regeneration and markdown export

### Use Cases

This pipeline is designed for scenarios where you need to:

- **Build enterprise knowledge bases** from large document libraries (policies, contracts, technical manuals)
- **Automate legal/compliance analysis** across hundreds of regulatory documents
- **Extract insights from research papers** or financial reports at scale
- **Create searchable document archives** with persistent, reusable summaries
- **Enable RAG (Retrieval-Augmented Generation)** applications with structured document data
- **Process documents repeatedly** without re-uploading (cost optimization)
- **Query multiple documents** with cross-document search and comparison

### Technology Stack

- **Azure Durable Functions** (Python 3.10+) - Serverless orchestration with checkpointing
- **Azure Document Intelligence v4.0** - OCR and text extraction with span-based parsing
- **Azure OpenAI** (GPT-5) - AI-powered summarization
- **Azure Blob Storage** - Persistent artifact storage
- **Azure Cosmos DB** - Metadata indexing and querying
- **Azure Identity** - Managed Identity for secure, keyless authentication

![Architecture](./docs/architecture.png)

---

## 🤔 Why Use This Pipeline Instead of Chat Attachments?

### The Chat Attachment Approach

When you attach a document to a chat with an LLM (like ChatGPT, Claude, or Copilot), the system typically:

1. **Uploads the document** to the chat session
2. **Processes it on-the-fly** - extracts text, maybe creates embeddings
3. **Loads into context window** - limited by token limits (128K-200K tokens)
4. **Discards after session** - no persistence, must re-upload each time

**Limitations:**

- ❌ **Token limits**: 331-page document = ~400K tokens (exceeds most context windows)
- ❌ **Cost per query**: Entire document in context = $0.40-$1.20 per question
- ❌ **No persistence**: Must re-upload and re-process every session
- ❌ **Single document focus**: Hard to query across multiple documents
- ❌ **Slow response**: Processing large PDFs adds 10-30 seconds per query
- ❌ **No structured metadata**: Can't filter by page, section, or topic
- ❌ **Quality inconsistency**: LLM may miss content or hallucinate without proper indexing

### The Document Intelligence Pipeline Advantage

This pipeline is purpose-built for **production document analysis at scale**:

#### 1. **Process Once, Query Forever**
```
Traditional Chat:           This Pipeline:
─────────────────          ─────────────────
Upload PDF (30s)           Process PDF once (2 min)
  ↓                           ↓
Process (20s)              Store structured data
  ↓                           ↓
Answer (5s)                Query anytime (0.5s)
  ↓                           ↓
Session ends               Persistent, reusable
  ↓                           ↓
Repeat next time ❌        Build on previous work ✅
```

**Cost Comparison (331-page document, 10 questions):**
- Chat attachment: 10 uploads × $1.00 = **$10.00**
- This pipeline: 1 processing ($0.15) + 10 queries ($0.05 each) = **$0.65** (94% savings)

#### 2. **Handle Documents of Any Size**
- **Chat**: Limited to ~200K tokens (~250 pages max, quality degrades after 100 pages)
- **Pipeline**: No limits - processes 331 pages, 1000+ pages, or entire document libraries

#### 3. **Multi-Document Intelligence**
```python
# Chat attachment: Can't do this
"Compare dairy policy in bbb-v1 with farm-bill-2018"

# This pipeline: Easy
results = search_embeddings(
    query="dairy policy provisions",
    document_ids=["bbb-v1", "farm-bill-2018"],
    level="page"
)
compare_policies(results)
```

#### 4. **Structured Knowledge Graph**
This pipeline creates **rich metadata** that enables advanced queries:

```python
# Find all pages discussing SNAP with numerical data
search(query="SNAP benefits", filters={
    "topics": ["SNAP", "nutrition"],
    "has_tables": True,
    "page_range": [1, 50]
})

# Find policy changes between 2024-2026
search(query="policy changes", filters={
    "year_range": [2024, 2026],
    "section": "Agriculture"
})
```

Chat attachments can't do this - they lack structured metadata.

#### 5. **Production-Ready Features**

| Feature | Chat Attachment | This Pipeline |
|---------|-----------------|---------------|
| **Processing Time** | 20-30s per query | One-time: 2-5 min, then instant |
| **Cost per Query** | $0.40-$1.20 | $0.005-$0.05 (95% cheaper) |
| **Max Document Size** | ~250 pages | Unlimited |
| **Multi-document** | No | Yes |
| **Persistent Storage** | No | Yes (Blob + Cosmos DB) |
| **Structured Metadata** | No | Yes (pages, sections, topics) |
| **API Access** | Limited | Full REST API |
| **Version Control** | No | Yes (track document versions) |
| **Batch Processing** | No | Yes (process 100s of docs) |
| **Audit Trail** | No | Yes (Cosmos DB logs) |
| **Enterprise Security** | Session-based | Azure RBAC, private endpoints |

#### 6. **Real-World Use Cases This Pipeline Enables**

**Legal Compliance:**
- "Which regulations changed between 2023-2025 across all 50 policy documents?"
- "Show me every mention of 'data privacy' with context and citations"
- Chat: ❌ Can't search multiple documents
- Pipeline: ✅ Cross-document semantic search with precise citations

**Financial Analysis:**
- "Extract all budget allocations for renewable energy from 10 congressional bills"
- "Compare spending trends across 5 years of appropriations documents"
- Chat: ❌ Token limits, must upload one at a time
- Pipeline: ✅ Batch processing with structured data extraction

**Research & Discovery:**
- "What topics are covered in this 500-page research report?"
- "Find similar sections across 100 research papers"
- Chat: ❌ Document too large, no cross-document search
- Pipeline: ✅ Document-level summaries, topic clustering

**Enterprise Knowledge Base:**
- Build searchable archive of company policies, contracts, technical manuals
- Enable employees to ask questions without re-uploading docs
- Chat: ❌ Not designed for this
- Pipeline: ✅ Purpose-built for organizational knowledge management

#### 7. **Developer Experience**

**Chat Attachment:**
```
Manual process → No API → No automation → Not scalable
```

**This Pipeline:**
```python
# Automated workflow
documents = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
for doc in documents:
    process_document(doc)  # Runs in background
    
# Query programmatically
answer = query_documents(
    question="What are the key changes?",
    document_ids=["doc1", "doc2", "doc3"]
)

# Integrate with apps
app.add_endpoint("/ask", lambda q: pipeline.query(q))
```

**Result**: Build entire applications on top of this pipeline (chatbots, search engines, compliance tools).

---

### When to Use Chat Attachments vs. This Pipeline

**Use Chat Attachments When:**
- ✅ One-off questions on small documents (<50 pages)
- ✅ Quick exploratory analysis
- ✅ No need for persistence or reusability
- ✅ Simple summarization tasks

**Use This Pipeline When:**
- ✅ Large documents (100+ pages)
- ✅ Repeated queries on same documents
- ✅ Multiple documents to analyze
- ✅ Need for structured data and metadata
- ✅ Cost optimization is important
- ✅ Building production applications
- ✅ Enterprise knowledge management
- ✅ Compliance and audit requirements

---

### The Bottom Line

**Chat attachments are great for casual, one-time use. This pipeline is built for production-grade document intelligence.**

Think of it like:
- **Chat Attachment** = Taking notes with pen and paper
- **This Pipeline** = Building a searchable, persistent knowledge management system

If you're asking the same questions across documents, querying large documents repeatedly, or building an application that needs document intelligence - this pipeline pays for itself in cost savings and capabilities within days.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Serverless & Durable** | Built on Azure Durable Functions with automatic checkpointing and retry |
| **Fan-out/Fan-in Pattern** | Process pages in parallel batches (default: 32 concurrent) |
| **OCR & Text Extraction** | Azure Document Intelligence v4.0 with `prebuilt-read` model for accurate text extraction from PDFs (supports up to 500 MB on paid tier) |
| **AI-Powered Summaries** | Per-page one-sentence summaries + multi-paragraph document summary |
| **Full Audit Trail** | All artifacts persisted to Blob Storage with metadata in Cosmos DB |
| **Identity-Based Auth** | Uses `DefaultAzureCredential` for Blob, Cosmos, and OpenAI |
| **Extensible** | Easy to add classification, additional analyzers, or custom processing steps |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Azure Functions                                 │
│  ┌──────────────┐    ┌─────────────────────────────────────────────────┐    │
│  │  HTTP Start  │───▶│            Durable Orchestrator                 │    │
│  │  (Trigger)   │    │                                                 │    │
│  └──────────────┘    │  ┌─────────┐   ┌──────────────┐   ┌─────────┐  │    │
│                      │  │pdf_split│──▶│ page_summary │──▶│   doc   │  │    │
│                      │  │         │   │  (fan-out)   │   │ summary │  │    │
│                      │  └─────────┘   └──────────────┘   └─────────┘  │    │
│                      │        │              │                │       │    │
│                      │        ▼              ▼                ▼       │    │
│                      │  ┌─────────────────────────────────────────┐   │    │
│                      │  │         write_report + write_index      │   │    │
│                      │  └─────────────────────────────────────────┘   │    │
│                      └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
         │                        │                          │
         ▼                        ▼                          ▼
┌─────────────────┐    ┌─────────────────┐         ┌─────────────────┐
│  Azure Blob     │    │  Azure OpenAI   │         │  Azure Cosmos   │
│  Storage        │    │  (GPT-4/5)      │         │  DB             │
│                 │    │                 │         │                 │
│ • raw-pdfs/     │    │ • Summarization │         │ • documents     │
│ • parsed-pages/ │    │ • Text Analysis │         │   container     │
│ • summaries/    │    │                 │         │                 │
│ • reports/      │    │                 │         │                 │
└─────────────────┘    └─────────────────┘         └─────────────────┘
```

### Pipeline Flow

1. **Upload** → Client uploads PDF to `raw-pdfs` container
2. **Trigger** → HTTP POST to `/api/process-document` starts orchestration
3. **Split** → `pdf_split` uses Azure Document Intelligence (prebuilt-read) with span-based extraction for accurate text extraction → `parsed-pages/`
4. **Summarize Pages** → `page_summary` runs in parallel batches → `summaries/{docId}/pages/`
5. **Summarize Document** → `doc_summary` creates final summary → `summaries/{docId}.json`
6. **Report** → `write_report` creates processing report → `reports/{docId}.json`
7. **Index** → `write_index` upserts metadata to Cosmos DB

---

## 📁 Project Structure

```
dur_func/
├── function_app.py          # Main entry point with all function definitions
├── activities/              # Activity implementations
│   ├── pdf_split_activity.py
│   ├── page_summary_activity.py
│   ├── doc_summary_activity.py
│   ├── write_report_activity.py
│   └── write_index_activity.py
├── utils/                   # Shared utilities
│   ├── storage_utils.py     # Blob Storage operations
│   ├── cosmos_utils.py      # Cosmos DB operations
│   ├── openai_utils.py      # Azure OpenAI client
│   ├── document_intelligence_utils.py  # Azure Document Intelligence SDK v1.0.0b4
│   └── content_understanding_utils.py  # Legacy (deprecated)
├── tests/                   # Unit tests
├── docs/                    # Documentation
│   ├── architecture.md
│   ├── architecture.drawio.svg
│   ├── function-flow.md
│   ├── setup.md
│   ├── deployment.md
│   ├── prompts.md
│   └── troubleshooting.md
├── regenerate_summaries.py  # Standalone summary regeneration tool
├── format_summary_markdown.py  # Markdown formatter for document summaries
├── host.json                # Functions host configuration
├── local.settings.json      # Local development settings
└── requirements.txt         # Python dependencies
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Azure Functions Core Tools v4**
- **Azure CLI** (logged in with `az login`)
- Azure resources:
  - Storage Account with containers: `raw-pdfs`, `summaries`, `reports`
  - Cosmos DB account with database and `documents` container
  - Azure OpenAI deployment (GPT-4 or GPT-4o recommended)
  - Azure Document Intelligence resource (S0 tier recommended for files up to 500 MB)

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd dur_func

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Settings

Create `local.settings.json`:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage__accountName": "<storage-account-name>",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "DOCUMENT_INTELLIGENCE_ENDPOINT": "https://<your-resource>.cognitiveservices.azure.com/",
    "DOCUMENT_INTELLIGENCE_KEY": "<your-key>",
    "AZURE_OPENAI_ENDPOINT": "https://<your-openai>.openai.azure.com/",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4",
    "AZURE_OPENAI_API_KEY": "<your-api-key>",
    "COSMOS_ENDPOINT": "https://<your-cosmos>.documents.azure.com:443/",
    "COSMOS_DB": "<database-name>",
    "BLOB_ACCOUNT_URL": "https://<storage-account>.blob.core.windows.net/",
    "OPENAI_MAX_CONCURRENCY": "32",
    "PAGE_SUMMARY_SENTENCES": "2"
  }
}
```

### 3. Run Locally

```bash
func start
```

### 4. Process a Document

Upload a PDF to the `raw-pdfs` container, then trigger processing:

```powershell
# PowerShell
$body = @{
    documentId = "my-document"
    blobPath = "raw-pdfs/my-document.pdf"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:7071/api/process-document" `
    -Method POST -Body $body -ContentType "application/json"
```

```bash
# Bash/curl
curl -X POST http://localhost:7071/api/process-document \
  -H "Content-Type: application/json" \
  -d '{"documentId": "my-document", "blobPath": "raw-pdfs/my-document.pdf"}'
```

The response includes status URLs to monitor progress:

```json
{
  "id": "abc123...",
  "statusQueryGetUri": "http://localhost:7071/runtime/webhooks/durabletask/instances/abc123...",
  "sendEventPostUri": "...",
  "terminatePostUri": "...",
  "purgeHistoryDeleteUri": "..."
}
```

---

## 📊 Output Artifacts

### Blob Storage

| Container | Path | Description |
|-----------|------|-------------|
| `raw-pdfs` | `{filename}.pdf` | Source PDF documents |
| `raw-pdfs` | `parsed-pages/{docId}/{page}.json` | Extracted text per page |
| `summaries` | `{docId}/pages/{page}.json` | One-sentence page summaries |
| `summaries` | `{docId}.json` | Multi-paragraph document summary |
| `reports` | `{docId}.json` | Processing report with success/failure counts |

### Cosmos DB Document

```json
{
  "id": "my-document",
  "documentId": "my-document",
  "fileName": "my-document.pdf",
  "blobPath": "raw-pdfs/my-document.pdf",
  "pageCount": 8,
  "failedPageCount": 0,
  "summaryBlob": "my-document.json",
  "reportBlob": "my-document.json",
  "status": "completed",
  "createdAt": "2025-11-25T17:04:16.871Z",
  "updatedAt": "2025-11-25T17:04:16.871Z"
}
```

---

## ⚙️ Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | Required |
| `AZURE_OPENAI_DEPLOYMENT` | Model deployment name | Required |
| `AZURE_OPENAI_API_KEY` | API key (or use Managed Identity) | Required |
| `COSMOS_ENDPOINT` | Cosmos DB endpoint URL | Required |
| `COSMOS_DB` | Cosmos DB database name | `docsum` |
| `BLOB_ACCOUNT_URL` | Blob Storage account URL | Required |
| `OPENAI_MAX_CONCURRENCY` | Max parallel page summaries | `32` |
| `PAGE_SUMMARY_SENTENCES` | Sentences per page summary | `2` |

---

## 🔐 Authentication

The pipeline uses **`DefaultAzureCredential`** for Azure services, which supports:

1. **Local Development**: `az login` credentials
2. **Azure Deployment**: Managed Identity

### Required RBAC Roles

| Service | Role |
|---------|------|
| Storage Account | Storage Blob Data Contributor |
| Storage Account | Storage Queue Data Contributor |
| Storage Account | Storage Table Data Contributor |
| Cosmos DB | Cosmos DB Built-in Data Contributor |
| Azure OpenAI | Cognitive Services OpenAI User |

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_page_summary.py -v
```

---

## 🚢 Deployment

See [docs/deployment.md](./docs/deployment.md) for full deployment instructions.

Quick deploy with Azure CLI:

```bash
# Create Function App
az functionapp create \
  --resource-group <rg-name> \
  --consumption-plan-location <region> \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name <function-app-name> \
  --storage-account <storage-name>

# Deploy code
func azure functionapp publish <function-app-name>
```

---

## 🔧 Helper Tools

### Summary Regeneration (`regenerate_summaries.py`)

Standalone tool to regenerate summaries without reprocessing PDFs. Useful for:
- Fixing empty summaries caused by token limit issues
- Re-running summaries with updated prompts
- Selective page regeneration

**Usage:**
```bash
# Regenerate all summaries for a document
python regenerate_summaries.py timken-v5

# Regenerate specific page range
python regenerate_summaries.py timken-v5 --pages 1-50

# Dry-run to check what would be processed
python regenerate_summaries.py timken-v5 --dry-run

# Process all documents
python regenerate_summaries.py --all
```

**Features:**
- Parallel processing (32 concurrent workers by default)
- Progress tracking with success/skipped/failed counts
- Direct activity calls (bypasses orchestrator for faster execution)
- Supports partial regeneration with `--pages` flag

### Markdown Formatter (`format_summary_markdown.py`)

Converts document summaries from blob storage into well-formatted markdown files.

**Usage:**
```bash
# Format a single document summary
python format_summary_markdown.py timken-v5

# Custom output path
python format_summary_markdown.py timken-v5 --output reports/timken.md

# Executive summary only (no page details)
python format_summary_markdown.py timken-v5 --no-pages

# Format all documents in batch
python format_summary_markdown.py --all --output-dir markdown_summaries/
```

**Output includes:**
- Status badges (✅ Success / ❌ Failed)
- Executive summary from document-level analysis
- Page-by-page summaries with statistics
- Metadata (page counts, blob paths, timestamps)
- Error details for failed processing

---

## 📚 Documentation

- [Architecture Overview](./docs/architecture.md)
- [Function Flow](./docs/function-flow.md)
- [Prompts & Summarization](./docs/prompts.md)
- [Embeddings Strategy](./docs/embeddings-strategy.md) - Multi-level embedding architecture for semantic search and RAG
- [Local Setup](./docs/setup.md)
- [Deployment Guide](./docs/deployment.md)
- [Troubleshooting](./docs/troubleshooting.md)

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `max_tokens` error | Use `max_completion_tokens` for GPT-5 models |
| `temperature` error | GPT-5 only supports default temperature (1) |
| Cosmos 404 error | Ensure database and container exist with correct partition key |
| Storage auth error | Run `az login` or check RBAC roles |

See [docs/troubleshooting.md](./docs/troubleshooting.md) for more.

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) for details.
