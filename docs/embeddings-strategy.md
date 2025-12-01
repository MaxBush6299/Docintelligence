# Multi-Level Embedding Strategy for Document Intelligence Pipeline

**Version:** 1.0  
**Date:** December 2025  
**Status:** Design Proposal

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Why Multi-Level Embeddings](#why-multi-level-embeddings)
3. [Architecture](#architecture)
4. [Query Patterns & Use Cases](#query-patterns--use-cases)
5. [Implementation Steps](#implementation-steps)
6. [Storage & Infrastructure](#storage--infrastructure)
7. [Integration with Existing Pipeline](#integration-with-existing-pipeline)
8. [Performance Considerations](#performance-considerations)
9. [Example Scenarios](#example-scenarios)
10. [Next Steps](#next-steps)

---

## Overview

This document outlines a **multi-level embedding strategy** to enable semantic search, question-answering, and retrieval-augmented generation (RAG) capabilities for processed documents in the Azure Document Intelligence Pipeline.

### Goals

- **Enable semantic search** across document collections
- **Support RAG-based question answering** with precise citations
- **Optimize query performance** through hierarchical search
- **Reduce costs** by intelligent filtering before expensive operations
- **Improve user experience** with context-aware responses

### Key Principles

1. **Progressive Refinement**: Start broad, drill down as needed
2. **Context-Aware Filtering**: Use metadata to reduce search space
3. **Cost-Optimized**: Minimize embedding comparisons and LLM calls
4. **Citation-Ready**: Always return source pages/paragraphs

---

## Why Multi-Level Embeddings

### The Problem with Single-Level Embeddings

**Flat approach**: Embed every paragraph → 1000+ vectors per document

```
User Query: "What does this say about dairy farmers?"
    ↓
Search 1,000+ paragraph embeddings
    ↓
Return top 5 matches
    ↓
Time: ~500ms, Cost: High, False Positives: Common
```

### Multi-Level Solution

**Hierarchical approach**: Document → Page → Paragraph

```
User Query: "What does this say about dairy farmers?"
    ↓
Level 1: Document-level (1 vector) - Is this doc relevant?
    ↓ (Yes, confidence: 0.87)
Level 2: Page-level (331 vectors) - Which pages discuss dairy?
    ↓ (Pages 29-31, confidence: 0.92)
Level 3: Paragraph-level (50 filtered vectors) - Exact answer?
    ↓ (3 specific paragraphs with citations)
Time: ~150ms, Cost: 70% lower, Accuracy: Higher
```

### Benefits

| Metric | Single-Level | Multi-Level | Improvement |
|--------|--------------|-------------|-------------|
| **Search Time** | 500ms | 150ms | 70% faster |
| **Vectors Searched** | 1,000+ | 50-100 | 90% reduction |
| **Embedding Cost** | $X | $0.3X | 70% savings |
| **False Positives** | Medium | Low | Better filtering |
| **Flexibility** | Low | High | Summary or detail |

---

## Architecture

### Three Embedding Levels

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCUMENT LEVEL (Level 1)                 │
│  1 vector per document - Executive summary embedding        │
│  Purpose: Multi-document search, topic identification       │
│  Example: "Which documents discuss agriculture policy?"     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     PAGE LEVEL (Level 2)                    │
│  331 vectors for bbb-v1 - One per page summary            │
│  Purpose: Topic localization, section discovery            │
│  Example: "Which pages in bbb-v1 discuss SNAP?"           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   PARAGRAPH LEVEL (Level 3)                 │
│  1,000+ vectors - Chunked page content (500-1000 tokens)  │
│  Purpose: Precise answers, exact citations                 │
│  Example: "What is the exact SNAP work requirement change?"│
└─────────────────────────────────────────────────────────────┘
```

### Data Model

#### Document-Level Embedding
```json
{
  "id": "bbb-v1_doc",
  "type": "document",
  "document_id": "bbb-v1",
  "text": "Public Law 119-21 is a sweeping reconciliation measure...",
  "embedding": [0.123, -0.456, 0.789, ...],  // 1536 or 3072 dimensions
  "metadata": {
    "file_name": "bbb.pdf",
    "page_count": 331,
    "creation_date": "2025-07-04",
    "topics": ["agriculture", "healthcare", "tax policy", "defense"]
  }
}
```

#### Page-Level Embedding
```json
{
  "id": "bbb-v1_page_30",
  "type": "page",
  "document_id": "bbb-v1",
  "page_number": 30,
  "text": "Dairy Margin Coverage thresholds rise with updated production history rules...",
  "embedding": [0.234, -0.567, 0.891, ...],
  "metadata": {
    "section": "Title I - Agriculture",
    "subsection": "Dairy Policy",
    "topics": ["dairy", "margin coverage", "milk production"],
    "has_tables": false,
    "has_formulas": true
  }
}
```

#### Paragraph-Level Embedding
```json
{
  "id": "bbb-v1_page_30_para_2",
  "type": "paragraph",
  "document_id": "bbb-v1",
  "page_number": 30,
  "paragraph_number": 2,
  "text": "The law raises Dairy Margin Coverage thresholds from 5,000,000 to 6,000,000...",
  "embedding": [0.345, -0.678, 0.912, ...],
  "metadata": {
    "section": "Dairy Margin Coverage",
    "topics": ["DMC", "thresholds", "premium discounts"],
    "contains_numbers": true,
    "char_count": 387,
    "start_offset": 1450,
    "end_offset": 1837
  }
}
```

---

## Query Patterns & Use Cases

### Pattern 1: Broad Discovery
**User Intent**: "What topics does this document cover?"

```python
# Use ONLY document-level
result = search_embeddings(
    query="document topics overview",
    level="document",
    top_k=1
)
# Returns: High-level summary with topic list
```

**Output**:
- Agriculture (commodity programs, dairy, crop insurance)
- Healthcare (Medicaid, Medicare, rural health)
- Tax Policy (individual relief, business reforms)
- Energy (oil & gas, renewable credits)

---

### Pattern 2: Topic Localization
**User Intent**: "What does this say about crop insurance?"

```python
# Step 1: Page-level search
pages = search_embeddings(
    query="crop insurance provisions",
    level="page",
    filter="document_id == 'bbb-v1'",
    top_k=10
)
# Returns: Pages [33, 34, 35, 36, 37] with relevance scores

# Step 2: Return page summaries
response = {
    "pages": pages,
    "summary": synthesize_summaries([p.text for p in pages]),
    "detail_level": "overview"
}
```

**Output**:
> Crop insurance changes are detailed on **pages 33-37**:
> - Beginning farmer premium subsidies increase
> - Coverage levels raised to 85%/90%/95%
> - Administrative expense subsidies added
> - Poultry insurance pilot program created

---

### Pattern 3: Precise Citation
**User Intent**: "What is the wheat loan rate for 2026?"

```python
# Step 1: Page-level to locate relevant sections
pages = search_embeddings(
    query="wheat loan rate 2026",
    level="page",
    filter="document_id == 'bbb-v1'",
    top_k=5
)
# Returns: Page 23 (score: 0.94)

# Step 2: Paragraph-level for exact answer
paragraphs = search_embeddings(
    query="wheat loan rate 2026",
    level="paragraph",
    filter="document_id == 'bbb-v1' AND page_number == 23",
    top_k=3
)
# Returns specific paragraph with rate

response = {
    "answer": "$3.72 per bushel",
    "source": "Page 23, Section 1202(c)",
    "context": paragraphs[0].text,
    "confidence": 0.94
}
```

**Output**:
> The loan rate for wheat for crop years 2026-2031 is **$3.72 per bushel**.
>
> *Source: Page 23, Section 1202(c), Paragraph 1*

---

### Pattern 4: Comparative Analysis
**User Intent**: "How do SNAP work requirements differ for different groups?"

```python
# Step 1: Identify relevant pages
pages = search_embeddings(
    query="SNAP work requirements exemptions",
    level="page",
    top_k=10
)

# Step 2: Extract comparative paragraphs
chunks_exemptions = search_embeddings(
    query="SNAP work requirement exemptions",
    level="paragraph",
    filter=f"page_number IN {pages} AND topics CONTAINS 'exemptions'",
    top_k=5
)

chunks_general = search_embeddings(
    query="SNAP work requirements general",
    level="paragraph",
    filter=f"page_number IN {pages}",
    top_k=5
)

# Step 3: LLM synthesis with comparison
response = llm_compare(chunks_exemptions, chunks_general)
```

**Output**:
> **Exempt Groups:**
> - Under 18 or over 65
> - Medically unfit
> - Caregivers of dependent child under 14
> - Pregnant women
> - Indians/Urban Indians
> - California Indians (specific provision)
>
> **Non-Exempt:**
> - Must meet general work requirements under subsection (d)(2)
>
> *Source: Pages 11-12*

---

### Pattern 5: RAG Question Answering
**User Intent**: "Explain the changes to Medicaid provider taxes"

```python
# Multi-step RAG
async def answer_question(question):
    # 1. Page-level retrieval
    pages = await search_embeddings(
        query=question,
        level="page",
        filter="document_id == 'bbb-v1'",
        top_k=5
    )
    
    # 2. If high confidence, use page summaries
    if pages[0].score > 0.85:
        context = "\n".join([p.text for p in pages[:3]])
        answer = await llm_generate(question, context, mode="summary")
        return {
            "answer": answer,
            "sources": [f"Page {p.page_number}" for p in pages[:3]],
            "detail": "summary"
        }
    
    # 3. Otherwise, drill to paragraphs
    relevant_pages = [p.page_number for p in pages]
    paragraphs = await search_embeddings(
        query=question,
        level="paragraph",
        filter=f"page_number IN {relevant_pages}",
        top_k=8
    )
    
    context = "\n\n".join([p.text for p in paragraphs])
    answer = await llm_generate(question, context, mode="detailed")
    
    return {
        "answer": answer,
        "sources": [f"Page {p.page_number}, ¶{p.paragraph_number}" for p in paragraphs],
        "detail": "comprehensive"
    }
```

---

## Implementation Steps

### Phase 1: Foundation (Weeks 1-2)

#### Step 1.1: Add Embedding Dependencies
```bash
pip install azure-search-documents==11.6.0
pip install tiktoken  # For token counting
```

Update `requirements.txt`:
```
azure-search-documents==11.6.0
tiktoken>=0.5.0
```

#### Step 1.2: Create Embedding Utility
Create `utils/embedding_utils.py`:

```python
import os
import logging
from typing import List, Dict, Any, Optional
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential
import tiktoken

logger = logging.getLogger(__name__)

# Initialize Azure OpenAI client
credential = DefaultAzureCredential()
client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_version="2024-10-01-preview",
    azure_ad_token_provider=lambda: credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token
)

EMBEDDING_MODEL = "text-embedding-3-large"  # or text-embedding-ada-002
EMBEDDING_DIMENSIONS = 3072  # 1536 for ada-002

def get_embedding(text: str, model: str = EMBEDDING_MODEL) -> List[float]:
    """Generate embedding for text."""
    try:
        response = client.embeddings.create(
            input=text,
            model=model,
            dimensions=EMBEDDING_DIMENSIONS
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise

def chunk_text(
    text: str,
    max_tokens: int = 500,
    overlap_tokens: int = 50
) -> List[Dict[str, Any]]:
    """Split text into overlapping chunks."""
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    
    chunks = []
    start = 0
    chunk_num = 0
    
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        
        chunks.append({
            "chunk_number": chunk_num,
            "text": chunk_text,
            "token_count": len(chunk_tokens),
            "start_token": start,
            "end_token": end
        })
        
        start = end - overlap_tokens
        chunk_num += 1
    
    return chunks

def batch_embeddings(
    texts: List[str],
    batch_size: int = 100
) -> List[List[float]]:
    """Generate embeddings in batches."""
    embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        try:
            response = client.embeddings.create(
                input=batch,
                model=EMBEDDING_MODEL,
                dimensions=EMBEDDING_DIMENSIONS
            )
            embeddings.extend([item.embedding for item in response.data])
        except Exception as e:
            logger.error(f"Error in batch {i}-{i+batch_size}: {e}")
            raise
    
    return embeddings
```

#### Step 1.3: Create Embedding Activity
Create `activities/embedding_activity.py`:

```python
import logging
from typing import Dict, List, Any
from utils import storage_utils, embedding_utils
import json

logger = logging.getLogger(__name__)

async def embedding_impl(document_id: str) -> Dict[str, Any]:
    """Generate multi-level embeddings for a document.
    
    Args:
        document_id: Document identifier
        
    Returns:
        Dict with embedding statistics
    """
    logger.info(f"Generating embeddings for document: {document_id}")
    
    try:
        # Step 1: Fetch document summary
        doc_summary_blob = f"{document_id}.json"
        doc_summary_data = storage_utils.download_blob_json("summaries", doc_summary_blob)
        
        if not doc_summary_data:
            raise ValueError(f"No summary found for document: {document_id}")
        
        embeddings = []
        
        # Step 2: Document-level embedding
        logger.info("Generating document-level embedding")
        doc_embedding = embedding_utils.get_embedding(doc_summary_data['summary'])
        
        embeddings.append({
            "id": f"{document_id}_doc",
            "type": "document",
            "document_id": document_id,
            "text": doc_summary_data['summary'],
            "embedding": doc_embedding,
            "metadata": {
                "page_count": len(doc_summary_data.get('pages', [])),
                "status": doc_summary_data.get('status', 'unknown'),
                "summary_blob": doc_summary_blob
            }
        })
        
        # Step 3: Page-level embeddings
        logger.info("Generating page-level embeddings")
        page_count = 0
        page_embeddings_batch = []
        page_texts = []
        page_metadata = []
        
        for page_data in doc_summary_data.get('pages', []):
            if page_data.get('status') == 'success' and page_data.get('summary'):
                page_texts.append(page_data['summary'])
                page_metadata.append({
                    "page_number": page_data['page'],
                    "status": page_data['status']
                })
                page_count += 1
        
        # Batch generate page embeddings
        if page_texts:
            page_embeddings_batch = embedding_utils.batch_embeddings(page_texts)
            
            for idx, (text, metadata, emb) in enumerate(zip(page_texts, page_metadata, page_embeddings_batch)):
                embeddings.append({
                    "id": f"{document_id}_page_{metadata['page_number']}",
                    "type": "page",
                    "document_id": document_id,
                    "page_number": metadata['page_number'],
                    "text": text,
                    "embedding": emb,
                    "metadata": metadata
                })
        
        # Step 4: Paragraph-level embeddings (from parsed pages)
        logger.info("Generating paragraph-level embeddings")
        paragraph_count = 0
        
        for page_num in range(1, page_count + 1):
            # Fetch parsed page content
            parsed_blob = f"parsed-pages/{document_id}/{page_num}.json"
            
            try:
                parsed_data = storage_utils.download_blob_json("raw-pdfs", parsed_blob)
                
                if parsed_data and parsed_data.get('content'):
                    # Chunk the page content
                    chunks = embedding_utils.chunk_text(
                        parsed_data['content'],
                        max_tokens=500,
                        overlap_tokens=50
                    )
                    
                    # Generate embeddings for chunks
                    chunk_texts = [c['text'] for c in chunks]
                    chunk_embeddings = embedding_utils.batch_embeddings(chunk_texts)
                    
                    for chunk, emb in zip(chunks, chunk_embeddings):
                        embeddings.append({
                            "id": f"{document_id}_page_{page_num}_para_{chunk['chunk_number']}",
                            "type": "paragraph",
                            "document_id": document_id,
                            "page_number": page_num,
                            "paragraph_number": chunk['chunk_number'],
                            "text": chunk['text'],
                            "embedding": emb,
                            "metadata": {
                                "token_count": chunk['token_count'],
                                "start_token": chunk['start_token'],
                                "end_token": chunk['end_token']
                            }
                        })
                        paragraph_count += 1
                        
            except Exception as e:
                logger.warning(f"Could not process page {page_num}: {e}")
                continue
        
        # Step 5: Save embeddings to blob storage
        embeddings_blob = f"embeddings/{document_id}.json"
        storage_utils.upload_blob_json("summaries", embeddings_blob, {
            "document_id": document_id,
            "embedding_count": len(embeddings),
            "document_level": 1,
            "page_level": page_count,
            "paragraph_level": paragraph_count,
            "embeddings": embeddings
        })
        
        logger.info(f"Generated {len(embeddings)} embeddings: 1 doc, {page_count} pages, {paragraph_count} paragraphs")
        
        return {
            "status": "success",
            "document_id": document_id,
            "total_embeddings": len(embeddings),
            "document_level": 1,
            "page_level": page_count,
            "paragraph_level": paragraph_count,
            "embeddings_blob": embeddings_blob
        }
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}", exc_info=True)
        return {
            "status": "failed",
            "document_id": document_id,
            "error": str(e)
        }
```

---

### Phase 2: Infrastructure Setup (Week 3)

#### Step 2.1: Choose Storage Backend

**Option A: Azure AI Search** (Recommended)
```python
# utils/search_utils.py
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchField,
    SearchFieldDataType
)
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]

# Create index
def create_embeddings_index(index_name: str = "document-embeddings"):
    index_client = SearchIndexClient(endpoint, credential)
    
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="type", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
        SimpleField(name="paragraph_number", type=SearchFieldDataType.Int32, filterable=True),
        SearchableField(name="text", type=SearchFieldDataType.String),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="default-profile"
        ),
        SearchableField(name="metadata", type=SearchFieldDataType.String)
    ]
    
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(name="default-algorithm")
        ],
        profiles=[
            VectorSearchProfile(
                name="default-profile",
                algorithm_configuration_name="default-algorithm"
            )
        ]
    )
    
    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    index_client.create_or_update_index(index)
    
    return index_name
```

**Option B: Cosmos DB with Vector Search**
```python
# utils/cosmos_vector_utils.py
from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
endpoint = os.environ["COSMOS_ENDPOINT"]
database_name = os.environ.get("COSMOS_DB", "docsum")

client = CosmosClient(endpoint, credential=credential)
database = client.get_database_client(database_name)

# Create embeddings container with vector indexing
def create_embeddings_container():
    container_name = "embeddings"
    
    vector_embedding_policy = {
        "vectorEmbeddings": [
            {
                "path": "/embedding",
                "dataType": "float32",
                "dimensions": 3072,
                "distanceFunction": "cosine"
            }
        ]
    }
    
    indexing_policy = {
        "indexingMode": "consistent",
        "automatic": True,
        "includedPaths": [{"path": "/*"}],
        "excludedPaths": [{"path": "/embedding/*"}],
        "vectorIndexes": [
            {
                "path": "/embedding",
                "type": "diskANN"
            }
        ]
    }
    
    database.create_container_if_not_exists(
        id=container_name,
        partition_key=PartitionKey(path="/document_id"),
        indexing_policy=indexing_policy,
        vector_embedding_policy=vector_embedding_policy
    )
    
    return container_name
```

#### Step 2.2: Add Upload to Index
Update `activities/embedding_activity.py`:

```python
from utils import search_utils  # or cosmos_vector_utils

# After generating embeddings, upload to search index
async def upload_embeddings_to_index(embeddings: List[Dict[str, Any]]):
    """Upload embeddings to Azure AI Search."""
    search_client = search_utils.get_search_client("document-embeddings")
    
    # Prepare documents for upload
    documents = []
    for emb in embeddings:
        doc = {
            "id": emb["id"],
            "type": emb["type"],
            "document_id": emb["document_id"],
            "page_number": emb.get("page_number"),
            "paragraph_number": emb.get("paragraph_number"),
            "text": emb["text"],
            "embedding": emb["embedding"],
            "metadata": json.dumps(emb.get("metadata", {}))
        }
        documents.append(doc)
    
    # Upload in batches
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        result = search_client.upload_documents(documents=batch)
        logger.info(f"Uploaded batch {i}-{i+len(batch)}: {len(result)} succeeded")
    
    return len(documents)
```

---

### Phase 3: Query & RAG Integration (Week 4)

#### Step 3.1: Create Query Functions
Create `utils/rag_utils.py`:

```python
import logging
from typing import List, Dict, Any, Optional
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from utils import embedding_utils, openai_utils
import os

logger = logging.getLogger(__name__)

def search_embeddings(
    query: str,
    level: str,
    document_id: Optional[str] = None,
    top_k: int = 5,
    filter_expr: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Search embeddings with multi-level support.
    
    Args:
        query: User query text
        level: "document", "page", or "paragraph"
        document_id: Optional filter by document
        top_k: Number of results
        filter_expr: Additional OData filter
        
    Returns:
        List of matching results with scores
    """
    # Generate query embedding
    query_embedding = embedding_utils.get_embedding(query)
    
    # Build filter
    filters = [f"type eq '{level}'"]
    if document_id:
        filters.append(f"document_id eq '{document_id}'")
    if filter_expr:
        filters.append(filter_expr)
    
    filter_str = " and ".join(filters) if filters else None
    
    # Vector search
    search_client = get_search_client("document-embeddings")
    vector_query = VectorizedQuery(
        vector=query_embedding,
        k_nearest_neighbors=top_k,
        fields="embedding"
    )
    
    results = search_client.search(
        search_text=None,
        vector_queries=[vector_query],
        filter=filter_str,
        select=["id", "type", "document_id", "page_number", "paragraph_number", "text", "metadata"],
        top=top_k
    )
    
    return [
        {
            "id": r["id"],
            "type": r["type"],
            "document_id": r["document_id"],
            "page_number": r.get("page_number"),
            "paragraph_number": r.get("paragraph_number"),
            "text": r["text"],
            "score": r["@search.score"],
            "metadata": r.get("metadata", {})
        }
        for r in results
    ]


async def answer_question_rag(
    question: str,
    document_id: str,
    mode: str = "auto"
) -> Dict[str, Any]:
    """Answer question using RAG with multi-level embeddings.
    
    Args:
        question: User question
        document_id: Target document
        mode: "auto", "summary", or "detailed"
        
    Returns:
        Dict with answer, sources, and metadata
    """
    logger.info(f"RAG query: {question} on {document_id}")
    
    # Step 1: Page-level search
    page_results = search_embeddings(
        query=question,
        level="page",
        document_id=document_id,
        top_k=5
    )
    
    if not page_results:
        return {
            "answer": "No relevant information found.",
            "sources": [],
            "confidence": 0.0
        }
    
    # Step 2: Decide on detail level
    top_score = page_results[0]["score"]
    
    if mode == "auto":
        # High confidence -> use page summaries
        if top_score > 0.85:
            mode = "summary"
        else:
            mode = "detailed"
    
    # Step 3: Generate response
    if mode == "summary":
        # Use page-level summaries
        context = "\n\n".join([
            f"Page {r['page_number']}: {r['text']}"
            for r in page_results[:3]
        ])
        
        answer = openai_utils.summarize_text(
            text=context,
            prompt=f"Answer this question based on the following context:\n\nQuestion: {question}\n\nContext:"
        )
        
        return {
            "answer": answer,
            "sources": [f"Page {r['page_number']}" for r in page_results[:3]],
            "detail_level": "summary",
            "confidence": top_score
        }
    
    else:  # detailed
        # Drill down to paragraphs
        relevant_pages = [r["page_number"] for r in page_results[:10]]
        
        paragraph_results = search_embeddings(
            query=question,
            level="paragraph",
            document_id=document_id,
            top_k=8,
            filter_expr=f"page_number in ({','.join(map(str, relevant_pages))})"
        )
        
        context = "\n\n".join([
            f"[Page {r['page_number']}, ¶{r['paragraph_number']}]\n{r['text']}"
            for r in paragraph_results
        ])
        
        answer = openai_utils.summarize_text(
            text=context,
            prompt=f"Provide a detailed answer to this question with specific citations:\n\nQuestion: {question}\n\nContext:"
        )
        
        return {
            "answer": answer,
            "sources": [
                f"Page {r['page_number']}, ¶{r['paragraph_number']}"
                for r in paragraph_results
            ],
            "detail_level": "detailed",
            "confidence": top_score
        }
```

#### Step 3.2: Add RAG HTTP Endpoint
Update `function_app.py`:

```python
@app.route(route="query", methods=["POST"])
async def query_documents(req: func.HttpRequest) -> func.HttpResponse:
    """RAG query endpoint using multi-level embeddings."""
    try:
        req_body = req.get_json()
        question = req_body.get('question')
        document_id = req_body.get('document_id')
        mode = req_body.get('mode', 'auto')  # auto, summary, detailed
        
        if not question or not document_id:
            return func.HttpResponse(
                json.dumps({"error": "Missing question or document_id"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Import RAG utils
        from utils import rag_utils
        
        # Perform RAG query
        result = await rag_utils.answer_question_rag(
            question=question,
            document_id=document_id,
            mode=mode
        )
        
        return func.HttpResponse(
            json.dumps(result),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in query endpoint: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
```

---

### Phase 4: Pipeline Integration (Week 5)

#### Step 4.1: Add Embedding Activity to Orchestrator
Update `function_app.py`:

```python
@app.orchestration_trigger(context_name="context")
def orchestrator(context: df.DurableOrchestrationContext):
    """Main orchestration with embedding generation."""
    input_data = context.get_input()
    document_id = input_data.get("documentId")
    
    # ... existing steps (pdf_split, page_summary, doc_summary) ...
    
    # NEW: Generate embeddings
    embedding_result = yield context.call_activity(
        "embedding_activity",
        document_id
    )
    
    # Continue with report and index
    report_result = yield context.call_activity(
        "write_report_activity",
        {
            "documentId": document_id,
            # ... include embedding_result ...
        }
    )
    
    # ... rest of orchestration ...

# Register embedding activity
@app.activity_trigger(input_name="documentId")
async def embedding_activity(documentId: str):
    """Activity to generate multi-level embeddings."""
    from activities.embedding_activity import embedding_impl
    return await embedding_impl(documentId)
```

---

## Storage & Infrastructure

### Azure AI Search Schema

```json
{
  "name": "document-embeddings",
  "fields": [
    {"name": "id", "type": "Edm.String", "key": true},
    {"name": "type", "type": "Edm.String", "filterable": true},
    {"name": "document_id", "type": "Edm.String", "filterable": true},
    {"name": "page_number", "type": "Edm.Int32", "filterable": true, "sortable": true},
    {"name": "paragraph_number", "type": "Edm.Int32", "filterable": true},
    {"name": "text", "type": "Edm.String", "searchable": true},
    {"name": "embedding", "type": "Collection(Edm.Single)", 
     "searchable": true, "dimensions": 3072, "vectorSearchProfile": "default-profile"},
    {"name": "metadata", "type": "Edm.String"}
  ],
  "vectorSearch": {
    "algorithms": [
      {"name": "default-algorithm", "kind": "hnsw"}
    ],
    "profiles": [
      {"name": "default-profile", "algorithm": "default-algorithm"}
    ]
  }
}
```

### Cosmos DB Container

```json
{
  "id": "embeddings",
  "partitionKey": {
    "paths": ["/document_id"],
    "kind": "Hash"
  },
  "vectorEmbeddingPolicy": {
    "vectorEmbeddings": [
      {
        "path": "/embedding",
        "dataType": "float32",
        "dimensions": 3072,
        "distanceFunction": "cosine"
      }
    ]
  },
  "indexingPolicy": {
    "vectorIndexes": [
      {"path": "/embedding", "type": "diskANN"}
    ]
  }
}
```

---

## Performance Considerations

### Cost Optimization

| Component | Cost Factor | Optimization |
|-----------|-------------|--------------|
| **Embedding Generation** | $0.13 per 1M tokens | Batch API calls (100 texts/call) |
| **Vector Storage** | Storage + queries | Azure AI Search Standard tier |
| **LLM Calls** | Token usage | Use page summaries when possible |
| **Search Queries** | Per-query pricing | Cache frequent queries |

**Example for 331-page document:**
- Document embedding: 1 × 1K tokens = $0.0001
- Page embeddings: 331 × 200 tokens = $0.01
- Paragraph embeddings: 1000 × 500 tokens = $0.06
- **Total**: ~$0.07 per document

### Query Performance

```
Document-level search:    1 vector comparison    → 10ms
Page-level search:        331 vector comparisons  → 50ms
Paragraph-level search:   1000 vector comparisons → 200ms

Multi-level strategy:     1 + 331 + 50 filtered  → 80ms total
```

---

## Example Scenarios

### Scenario 1: Legal Research
**Query**: "What are the new SNAP work requirement exemptions for pregnant women?"

**Execution**:
1. Page-level search → Pages 11-12 identified
2. Paragraph-level search on pages 11-12 → 3 specific paragraphs
3. LLM synthesis with citations

**Output**:
> Pregnant women are **explicitly exempt** from SNAP work requirements under the revised Food and Nutrition Act amendments.
>
> The exemption is listed alongside other categories including individuals under 18 or over 65, those medically unfit, and caregivers of dependent children under 14.
>
> *Source: Page 11, Section 10302, Paragraph 3*

---

### Scenario 2: Policy Impact Analysis
**Query**: "How will these changes affect beginning farmers?"

**Execution**:
1. Page-level search → Pages 33-37 (crop insurance), 22-23 (payment limits)
2. Extract relevant chunks from multiple sections
3. Comparative synthesis

**Output**:
> Beginning farmers (≤10 years experience) receive significant benefits:
>
> **Crop Insurance:**
> - Extra premium subsidies: 5 points (years 1-2), 3 points (year 3), 1 point (year 4)
> - Higher coverage caps: 85%/90%/95%
> - Source: Pages 33-34
>
> **Payment Limits:**
> - Increased from $125K to $155K with CPI adjustments
> - AGI cap waived if 75%+ income from farming
> - Source: Page 22
>
> **Overall Impact:** Substantial financial support and flexibility for new entrants

---

### Scenario 3: Cross-Document Search
**Query**: "Which documents discuss renewable energy tax credits?"

**Execution**:
1. Document-level search across all documents
2. Return ranked list with brief excerpts

**Output**:
```
1. bbb-v1 (Score: 0.94)
   "Terminates various clean energy credits including renewable energy 
    property, clean electricity production, and residential clean energy..."
   
2. inflation-reduction-act (Score: 0.89)
   "Establishes production and investment tax credits for clean electricity,
    hydrogen, and advanced manufacturing..."
   
3. energy-policy-2024 (Score: 0.72)
   "Updates to renewable energy credit calculations and phase-out schedules..."
```

---

## Next Steps

### Immediate Actions
1. [ ] Review and approve this strategy document
2. [ ] Provision Azure AI Search resource (Standard tier)
3. [ ] Install required dependencies
4. [ ] Create embedding utility module
5. [ ] Implement embedding activity

### Short Term (2-3 weeks)
6. [ ] Test embedding generation on sample document
7. [ ] Create search index and upload embeddings
8. [ ] Implement query functions
9. [ ] Add RAG HTTP endpoint
10. [ ] Integration testing

### Medium Term (1-2 months)
11. [ ] Integrate into main pipeline orchestrator
12. [ ] Build UI/API for document Q&A
13. [ ] Add caching layer for frequent queries
14. [ ] Implement analytics on query patterns
15. [ ] Performance optimization

### Long Term (3+ months)
16. [ ] Multi-document search and comparison
17. [ ] Advanced RAG with re-ranking
18. [ ] Fine-tune embeddings for domain-specific terms
19. [ ] Add feedback loop for answer quality
20. [ ] Scale to production workload

---

## References

- [Azure OpenAI Embeddings](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/embeddings)
- [Azure AI Search Vector Search](https://learn.microsoft.com/en-us/azure/search/vector-search-overview)
- [Cosmos DB Vector Search](https://learn.microsoft.com/en-us/azure/cosmos-db/nosql/vector-search)
- [RAG Best Practices](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/use-your-data)

---

**Document Status**: Draft - Pending Review  
**Last Updated**: December 2025  
**Contributors**: AI Assistant, Development Team
