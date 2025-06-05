# PDF Processing API Documentation

Base URL: `http://127.0.0.1:9000/api/v1`

## Authentication

### Simple API Key Authentication
All API endpoints require a simple API key in the header:
```
X-API-Key: your-api-key-here
```

---

## 📄 Batch Processing APIs

### 1. Create Enhanced Batch Job
**POST** `/batch/enhanced`

Process multiple PDF files with detailed results and webhook notifications.

**Request Body:**
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

**Response (202 Accepted):**
```json
{
  "batch_id": "9",
  "status": "pending",
  "total_files": 3,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 2. Create Standard Batch Job
**POST** `/batch/process`

Standard batch processing with basic format.

**Request Body:**
```json
{
  "webhook_url": "https://example.com/webhook",
  "files": [
    {"url": "https://example.com/file1.pdf", "file_id": "doc1"},
    {"url": "https://example.com/file2.pdf", "file_id": "doc2"}
  ],
  "options": {
    "extract_references": true,
    "extract_metadata": true,
    "extract_full_text": false,
    "complete_references": true
  },
  "batch_id": "client-batch-123"
}
```

### 3. Get Batch Status
**GET** `/batch/{batch_id}/status`

Check the status of a batch processing job.

**Response:**
```json
{
  "batch_id": "9",
  "status": "completed",
  "total_files": 3,
  "processed_files": 2,
  "failed_files": 1,
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:35:00Z"
}
```

---

## 🔄 Job Processing APIs

### 1. Create Single PDF Processing Job
**POST** `/jobs/`

Process a single PDF file.

**Request Body:**
```json
{
  "url": "https://example.com/document.pdf",
  "extract_metadata": true,
  "extract_references": true,
  "complete_references": false,
  "webhook_url": "https://example.com/webhook"
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 2. Get Job Result
**GET** `/jobs/{job_id}`

Get the processing result for a specific job.

**Response:**
```json
{
  "job_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "metadata": {
    "title": "Sample Document",
    "authors": [...],
    "abstract": "...",
    "keywords": [...]
  },
  "references": [...],
  "created_at": "2024-01-15T10:30:00Z",
  "completed_at": "2024-01-15T10:35:00Z"
}
```

### 3. Get Raw Job Response
**GET** `/jobs/{job_id}/raw-response`

Get the raw response from the processing service.

---

## 📚 Document Management APIs

### 1. Upload Document
**POST** `/documents/`

Upload and register a new document.

**Form Data:**
- `file`: PDF file
- `title`: Document title
- `description`: Document description

**Response:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "title": "Sample Document",
  "filename": "document.pdf",
  "file_size": 1024000,
  "upload_date": "2024-01-15T10:30:00Z",
  "status": "uploaded"
}
```

### 2. List Documents
**GET** `/documents/`

Get a list of all uploaded documents.

**Query Parameters:**
- `skip`: Number of documents to skip (default: 0)
- `limit`: Maximum number of documents to return (default: 100)

### 3. Search Documents
**GET** `/documents/search`

Search documents by title or content.

**Query Parameters:**
- `query`: Search query string
- `skip`: Number of results to skip (default: 0)
- `limit`: Maximum number of results (default: 100)

### 4. Get Document by ID
**GET** `/documents/{document_id}`

Retrieve a specific document by its ID.

### 5. Update Document
**PUT** `/documents/{document_id}`

Update document metadata.

**Request Body:**
```json
{
  "title": "Updated Title",
  "description": "Updated description"
}
```

### 6. Get Document History
**GET** `/documents/{document_id}/history`

Get the processing history for a document.

### 7. Find Document by URL
**GET** `/documents/by-url`

Find a document by its URL.

**Query Parameters:**
- `url`: The document URL

---

## 📊 Processing Status APIs

### 1. Get Processing Status
**GET** `/processing/{request_id}/status`

Check the status of a processing request.

**Response:**
```json
{
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "progress": 100,
  "message": "Processing completed successfully",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

### 2. Get Processing Details
**GET** `/processing/{request_id}`

Get detailed information about a processing request.

---

## 🔐 Authentication APIs

### 1. User Login
**POST** `/auth/login`

Authenticate a user and get an access token.

**Request Body:**
```json
{
  "username": "user@example.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. User Registration
**POST** `/auth/register`

Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "your-password",
  "full_name": "John Doe"
}
```

### 3. Get Current User
**GET** `/auth/me`

Get information about the currently authenticated user.

---

## 🔑 API Key Management APIs

### 1. Create API Key
**POST** `/api-keys/`

Create a new API key.

**Request Body:**
```json
{
  "name": "My API Key",
  "key_type": "gemini",
  "key_value": "your-api-key-value",
  "description": "API key for Gemini service",
  "is_active": true
}
```

### 2. List API Keys
**GET** `/api-keys/`

Get a list of all API keys.

### 3. Get API Key by ID
**GET** `/api-keys/{key_id}`

Retrieve a specific API key by its ID.

### 4. Update API Key
**PUT** `/api-keys/{key_id}`

Update an existing API key.

### 5. Delete API Key
**DELETE** `/api-keys/{key_id}`

Delete an API key.

### 6. Update API Key by Type
**PUT** `/api-keys/type/{key_type}`

Update an API key by its type (e.g., "gemini").

---

## 🚀 Quick Start Examples

### Example 1: Process Single PDF
```bash
curl -X POST "http://127.0.0.1:9000/api/v1/jobs/" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "url": "https://example.com/document.pdf",
    "extract_metadata": true,
    "extract_references": true
  }'
```

### Example 2: Enhanced Batch Processing
```bash
curl -X POST "http://127.0.0.1:9000/api/v1/batch/enhanced" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "files": [
      {
        "des_id": 1,
        "entry_id": "doc1",
        "file_url": "https://example.com/file1.pdf",
        "metadata": {"year": "2023", "journal": "Test Journal"}
      }
    ],
    "options": {
      "extract_metadata": true,
      "extract_references": true
    },
    "batch_id": "batch_123",
    "webhook_url": "https://example.com/webhook"
  }'
```

### Example 3: Check Batch Status
```bash
curl -X GET "http://127.0.0.1:9000/api/v1/batch/batch_123/status" \
  -H "X-API-Key: your-api-key"
```

---

## Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **202 Accepted**: Request accepted for processing
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Authentication required
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error
- **500 Internal Server Error**: Server error

---

## Error Response Format

```json
{
  "detail": "Error description",
  "error_code": "ERROR_CODE",
  "timestamp": "2024-01-15T10:30:00Z"
}
``` 