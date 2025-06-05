# Getting Started with PDF Processing API

## 🚀 Quick Setup

The FastAPI server is running on: `http://127.0.0.1:9000`

### API Key Authentication
All API endpoints use simple API key authentication. Include this header in all requests:
```
X-API-Key: pdf-processing-api-key-2024
```

---

## 📖 Available APIs

### 1. Enhanced Batch Processing (Recommended)
**Endpoint:** `POST /api/v1/batch/enhanced`

This is the new enhanced API that supports your specific JSON format with detailed results.

**Features:**
- ✅ Custom JSON format with `des_id`, `entry_id`, `file_url`
- ✅ Webhook notifications with detailed results
- ✅ Enhanced citation extraction with split-citation handling
- ✅ No user authentication required (just API key)

**Example Request:**
```bash
curl -X POST "http://127.0.0.1:9000/api/v1/batch/enhanced" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pdf-processing-api-key-2024" \
  -d '{
    "files": [
      {
        "des_id": 3,
        "entry_id": "20",
        "file_url": "http://127.0.0.1:8000/media/dms_files/2/153-154.pdf",
        "metadata": {"year": "1234", "issue": "12", "volume": "123", "journal": "test"}
      }
    ],
    "options": {
      "extract_metadata": true,
      "extract_full_text": true,
      "extract_references": true
    },
    "batch_id": "9",
    "webhook_url": "http://127.0.0.1:8000/api-integration/webhook/"
  }'
```

### 2. Standard Batch Processing
**Endpoint:** `POST /api/v1/batch/process`

The original batch processing API with standard format.

**Example Request:**
```bash
curl -X POST "http://127.0.0.1:9000/api/v1/batch/process" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pdf-processing-api-key-2024" \
  -d '{
    "webhook_url": "https://example.com/webhook",
    "files": [
      {"url": "https://example.com/file1.pdf", "file_id": "doc1"}
    ],
    "options": {
      "extract_references": true,
      "extract_metadata": true,
      "extract_full_text": false
    },
    "batch_id": "batch-123"
  }'
```

### 3. Batch Status Check
**Endpoint:** `GET /api/v1/batch/{batch_id}/status`

Check the status of any batch job.

**Example Request:**
```bash
curl -X GET "http://127.0.0.1:9000/api/v1/batch/batch-123/status" \
  -H "X-API-Key: pdf-processing-api-key-2024"
```

### 4. Single PDF Processing
**Endpoint:** `POST /api/v1/jobs/`

Process a single PDF file.

**Example Request:**
```bash
curl -X POST "http://127.0.0.1:9000/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pdf-processing-api-key-2024" \
  -d '{
    "url": "https://example.com/document.pdf",
    "extract_metadata": true,
    "extract_references": true
  }'
```

---

## 🧪 Testing the APIs

### Test Enhanced Batch Processing
```bash
python test_enhanced_batch.py
```

### Test Standard Batch Processing  
```bash
python test_standard_batch.py
```

---

## 🔧 Server Restart Required

**IMPORTANT:** After making changes to the API endpoints, you need to restart the FastAPI server to pick up the new enhanced batch endpoint (`/api/v1/batch/enhanced`).

### To restart the server:
1. Stop the current FastAPI server
2. Start it again with:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
   ```

### To check if all endpoints are available:
```bash
curl -s "http://127.0.0.1:9000/api/v1/openapi.json" | python -c "
import sys, json
data = json.load(sys.stdin)
batch_endpoints = [path for path in data['paths'].keys() if 'batch' in path]
print('Available batch endpoints:')
for endpoint in batch_endpoints:
    print(f'  - {endpoint}')
"
```

---

## 📚 Complete API Documentation

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for comprehensive documentation of all endpoints.

---

## 🌟 Key Features Implemented

### Enhanced Citation Extraction
- ✅ Handles citations split across pages and columns
- ✅ Merges citation fragments automatically
- ✅ Supports multi-column PDF layouts
- ✅ Enhanced prompt engineering for better accuracy

### Simple Authentication
- ✅ Constant API key authentication
- ✅ No complex JWT or user management required
- ✅ Easy to integrate with external systems

### Webhook Notifications
- ✅ Detailed results sent to webhook URL when processing completes
- ✅ Per-file status and extraction results
- ✅ Error handling and failure notifications

### Direct PDF Processing
- ✅ Uses Google Gemini API for direct PDF processing
- ✅ No intermediate text extraction step
- ✅ Better handling of document structure and formatting

---

## 🔍 Troubleshooting

### 404 Not Found for `/enhanced` endpoint
- Restart the FastAPI server to pick up the new endpoint
- Check that `app/api/endpoints/batch.py` has no syntax errors

### 401 Unauthorized
- Make sure you're including the `X-API-Key` header
- Verify the API key is: `pdf-processing-api-key-2024`

### Connection Refused
- Check that the FastAPI server is running on port 9000
- Try accessing the docs at: `http://127.0.0.1:9000/docs`

### Webhook Not Receiving Data
- Ensure your webhook URL is accessible from the server
- Check webhook logs for incoming requests
- Verify the webhook accepts POST requests with JSON payload

---

## 🎯 Next Steps

1. **Restart the FastAPI server** to enable the enhanced batch endpoint
2. **Test the enhanced batch API** using the test script
3. **Integrate the API** into your application using the documented format
4. **Set up webhook handling** to receive processing results
5. **Monitor batch processing** using the status endpoint

---

## 📞 API Summary

| Endpoint | Method | Purpose | Authentication |
|----------|--------|---------|----------------|
| `/api/v1/batch/enhanced` | POST | Enhanced batch processing | API Key |
| `/api/v1/batch/process` | POST | Standard batch processing | API Key |  
| `/api/v1/batch/{id}/status` | GET | Check batch status | API Key |
| `/api/v1/jobs/` | POST | Single PDF processing | API Key |
| `/api/v1/jobs/{id}` | GET | Get job result | API Key |
| `/docs` | GET | API Documentation | None |

**API Key:** `pdf-processing-api-key-2024`  
**Base URL:** `http://127.0.0.1:9000` 