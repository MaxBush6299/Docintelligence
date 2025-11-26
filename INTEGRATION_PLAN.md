# Azure Content Understanding Integration Plan

## Overview
Integration of Azure Content Understanding API with Azure Functions for document analysis and data extraction.

## Key Findings

### 1. API Request Format
- **Endpoint**: `{endpoint}/contentunderstanding/analyzers/{analyzer-id}:analyze?api-version=2025-11-01`
- **Method**: POST
- **Content-Type**: `application/json`
- **Authentication**: `Ocp-Apim-Subscription-Key` header

### 2. Request Body Format
```json
{
  "inputs": [
    {
      "url": "https://example.com/document.pdf"
    }
  ]
}
```

**Note**: The API currently supports:
- URL-based inputs (external file URLs)
- Currently unclear if base64 encoded binary data is supported in the `inputs` array

### 3. Response Pattern
- **Initial Response**: HTTP 202 Accepted (asynchronous operation)
- **Response Header**: Contains `Operation-Location` field
- **Operation-Location Format**: `{endpoint}/contentunderstanding/analyzerResults/{request-id}?api-version=2025-11-01`

### 4. Result Retrieval
- **Endpoint**: `{endpoint}/contentunderstanding/analyzerResults/{request-id}?api-version=2025-11-01`
- **Method**: GET
- **Authentication**: Same as POST request
- **Status Field**: Indicates `Running`, `NotStarted`, or `Succeeded`
- **Polling**: Wait minimum 1 second between GET requests

### 5. Available Prebuilt Analyzers
- `prebuilt-invoice`: Extract structured invoice data
- `prebuilt-image`: Analyze image content
- `prebuilt-audio`: Analyze audio content
- `prebuilt-video`: Analyze video content

## Response Structure

### Successful Response (Status: Succeeded)
```json
{
  "id": "request-id",
  "status": "Succeeded",
  "result": {
    "analyzerId": "analyzer-id",
    "apiVersion": "2025-11-01",
    "createdAt": "ISO-timestamp",
    "warnings": [],
    "contents": [
      {
        "path": "input1",
        "markdown": "extracted markdown content",
        "fields": {
          "FieldName": {
            "type": "string|number|date|object|array",
            "valueString": "value",
            "confidence": 0.95,
            "spans": [...],
            "source": "position info"
          }
        },
        "kind": "document",
        "pages": [...],
        "tables": [...],
        "keyValuePairs": [...]
      }
    ]
  },
  "usage": {
    "documentStandardPages": 1,
    "contextualizationTokens": 2345,
    "tokens": {
      "gpt-4.1-mini-input": 1234,
      "gpt-4.1-mini-output": 567
    }
  }
}
```

## Implementation Considerations

### File Input Methods
1. **URL-based** (Current confirmed method):
   - Pass direct HTTPS URL to document
   - API handles downloading and processing
   - Best for files already in cloud storage (Blob Storage, etc.)

2. **Binary data** (To be verified):
   - May support base64 encoded content in `inputs` array
   - Check documentation for exact format
   - Useful for files received via HTTP request

### Integration Architecture
```
Azure Function Trigger
    ↓
Document Upload/Reference
    ↓
POST /analyzers/{analyzer-id}:analyze
    ↓
202 Accepted + Operation-Location
    ↓
Poll GET /analyzerResults/{request-id}
    ↓
Parse & Store Results
    ↓
Return to Caller
```

### Error Handling
- Monitor HTTP status codes (202, 200, 4xx, 5xx)
- Check `status` field in polling response
- Review `warnings` array for extraction issues
- Implement exponential backoff for polling

### Requirements for Production
1. **Resource Setup**:
   - Microsoft Foundry resource in supported region
   - Default model deployments configured
   - Endpoint and subscription key available

2. **Models Required**:
   - GPT-4.1 (for advanced analysis)
   - GPT-4.1-mini (for lighter tasks)
   - text-embedding-3-large (for semantic processing)

3. **Polling Strategy**:
   - Minimum 1-second intervals between GET requests
   - Implement timeout (e.g., 5-10 minutes max)
   - Handle transient failures with retry logic

## Next Steps
1. Determine if binary data input is supported
2. Set up test environment with sample documents
3. Implement HTTP client with async polling
4. Create function to parse and normalize results
5. Add error handling and logging
6. Configure storage for results
7. Test with different document types and analyzers
