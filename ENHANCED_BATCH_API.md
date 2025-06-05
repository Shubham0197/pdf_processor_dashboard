# Enhanced Batch Processing API

This document describes the new enhanced batch processing API endpoint that supports the specific JSON format for batch PDF processing with webhook notifications.

## Endpoint

```
POST /api/batch/enhanced
```

## Features

- ✅ **Custom JSON Format**: Supports the specific format with `des_id`, `entry_id`, `file_url`, and metadata
- ✅ **Webhook Notifications**: Sends detailed results to your webhook URL when processing completes
- ✅ **Enhanced Citation Extraction**: Uses improved Gemini service with better handling of split citations
- ✅ **Detailed Results**: Returns complete extraction results for each file
- ✅ **Error Handling**: Comprehensive error tracking and reporting
- ✅ **Background Processing**: Non-blocking asynchronous processing

## Request Format

```json
{
  "files": [
    {
      "des_id": 3,
      "entry_id": "20",
      "file_url": "http://127.0.0.1:8000/media/dms_files/2/153-154.pdf",
      "metadata": {
        "year": "1234",
        "issue": "12",
        "volume": "123",
        "journal": "test"
      }
    }
  ],
  "options": {
    "extract_metadata": true,
    "extract_full_text": true,
    "extract_references": true,
    "complete_references": false
  },
  "batch_id": "9",
  "webhook_url": "http://127.0.0.1:8000/api-integration/webhook/"
}
```

### Request Fields

#### `files` (required)
Array of file objects to process:

- **`des_id`** (integer, required): Destination ID
- **`entry_id`** (string, required): Entry identifier  
- **`file_url`** (string, required): URL to the PDF file
- **`metadata`** (object, optional): Publication metadata
  - `year`: Publication year
  - `issue`: Issue number
  - `volume`: Volume number
  - `journal`: Journal name

#### `options` (required)
Processing options:

- **`extract_metadata`** (boolean): Extract document metadata (default: true)
- **`extract_full_text`** (boolean): Extract full text content (default: false)
- **`extract_references`** (boolean): Extract citations/references (default: true)
- **`complete_references`** (boolean): Use complete reference extraction mode (default: false)

#### `batch_id` (required)
String identifier for the batch. Must be unique.

#### `webhook_url` (required)
URL where results will be sent when processing completes.

## Response Format

### Immediate Response (202 Accepted)

```json
{
  "batch_id": "9",
  "status": "pending",
  "total_files": 3,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Webhook Notification (when complete)

```json
{
  "batch_id": "9",
  "status": "completed",
  "timestamp": "2024-01-15T10:35:00Z",
  "results": {
    "total_files": 3,
    "processed_files": 2,
    "failed_files": 1,
    "files": [
      {
        "des_id": 3,
        "entry_id": "20",
        "file_url": "http://127.0.0.1:8000/media/dms_files/2/153-154.pdf",
        "original_metadata": {
          "year": "1234",
          "issue": "12",
          "volume": "123",
          "journal": "test"
        },
        "processing_status": "completed",
        "extracted_data": {
          "metadata": {
            "title": "Sample Article Title",
            "authors": [...],
            "abstract": "...",
            "keywords": [...],
            "journal": "Test Journal",
            "year": "2023"
          },
          "references": [
            {
              "text": "1. Smith, J. (2020). Sample Reference...",
              "citation_type": "journal",
              "authors": ["Smith, J."],
              "year": "2020",
              "journal": "Sample Journal"
            }
          ],
          "raw_metadata_response": {...},
          "raw_references_response": {...}
        },
        "error": null
      }
    ]
  }
}
```

## Status Monitoring

You can also check batch status using:

```
GET /api/batch/{batch_id}/status
```

## Processing Options Details

### `extract_metadata`
Extracts document metadata including:
- Title
- Authors (with detailed information)
- Abstract
- Keywords
- Journal information
- Publication details

### `extract_references`
Extracts citations/references with enhanced handling of:
- Split citations across pages/columns
- Multiple citation formats
- Complete bibliographic information

### `complete_references`
Uses an enhanced extraction mode that:
- Makes multiple API calls for large reference lists
- Handles complex citation patterns
- Provides more complete reference extraction

## Error Handling

### File-level Errors
Individual files that fail processing will have:
```json
{
  "processing_status": "failed",
  "error": "Error description",
  "extracted_data": {}
}
```

### Batch-level Errors
If the entire batch fails, the webhook will receive:
```json
{
  "batch_id": "9",
  "status": "failed",
  "timestamp": "2024-01-15T10:35:00Z",
  "results": {
    "error": "Critical error description"
  }
}
```

## Example Usage

### Python with httpx
```python
import httpx
import asyncio

async def submit_batch():
    data = {
        "files": [...],
        "options": {...},
        "batch_id": "my_batch_123",
        "webhook_url": "https://my-app.com/webhook"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/batch/enhanced",
            json=data
        )
        return response.json()

# Submit batch
result = asyncio.run(submit_batch())
print(f"Batch submitted: {result['batch_id']}")
```

### cURL
```bash
curl -X POST "http://127.0.0.1:8000/api/batch/enhanced" \
  -H "Content-Type: application/json" \
  -d '{
    "files": [
      {
        "des_id": 3,
        "entry_id": "20", 
        "file_url": "http://example.com/file.pdf",
        "metadata": {"year": "2023", "journal": "Test Journal"}
      }
    ],
    "options": {
      "extract_metadata": true,
      "extract_references": true
    },
    "batch_id": "test_batch",
    "webhook_url": "https://example.com/webhook"
  }'
```

## Performance Notes

- Processing time depends on PDF size and complexity
- Citation extraction with `complete_references=true` takes longer but provides better results
- Webhook notifications are sent within 30 seconds of completion
- Large batches are processed sequentially for stability

## Migration from Original API

The original batch API (`/api/batch/process`) remains available. Key differences:

| Feature | Original API | Enhanced API |
|---------|-------------|--------------|
| JSON Format | Generic | Specific format required |
| Authentication | Required | Not required |
| Results Format | Basic | Detailed per-file results |
| Webhook | Optional | Required |
| Citation Handling | Standard | Enhanced split-citation handling |
| Field Names | `url`, `file_id` | `file_url`, `des_id`, `entry_id` | 