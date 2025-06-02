# Enhanced PDF Processing Data Schema

## Overview

The PDF processing system has been upgraded to use an enhanced document-centric schema that provides better tracking of processing requests, AI responses, and analytics. This new schema replaces the previous simple approach with a more robust and scalable design.

## Database Schema

### Core Tables

#### 1. `pdf_documents`
Stores core document information:
```sql
CREATE TABLE pdf_documents (
    id CHAR(36) PRIMARY KEY,
    file_url VARCHAR NOT NULL,
    file_hash VARCHAR,
    file_size INTEGER,
    page_count INTEGER,
    original_filename VARCHAR,
    upload_source VARCHAR,
    created_at DATETIME,
    updated_at DATETIME
);
```

#### 2. `processing_requests`
Tracks each processing request (single or batch):
```sql
CREATE TABLE processing_requests (
    id CHAR(36) PRIMARY KEY,
    document_id CHAR(36) NOT NULL,
    batch_id CHAR(36),
    batch_document_id CHAR(36),
    request_type VARCHAR NOT NULL,  -- 'single' or 'batch'
    requested_operations JSON,      -- What was requested (metadata, references, etc.)
    status VARCHAR,                 -- 'processing', 'completed', 'failed'
    created_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    webhook_url VARCHAR,
    webhook_sent_at DATETIME,
    webhook_response JSON,
    user_id VARCHAR,
    FOREIGN KEY(document_id) REFERENCES pdf_documents (id),
    FOREIGN KEY(batch_id) REFERENCES batch_jobs (id)
);
```

#### 3. `ai_processing_results`
Stores individual AI processing results with raw responses:
```sql
CREATE TABLE ai_processing_results (
    id CHAR(36) PRIMARY KEY,
    processing_request_id CHAR(36) NOT NULL,
    document_id CHAR(36) NOT NULL,
    processing_type VARCHAR NOT NULL,  -- 'metadata', 'references', 'processing_error'
    status VARCHAR,                    -- 'completed', 'failed'
    processing_time_ms INTEGER,
    raw_ai_response JSON,             -- Complete raw AI response with metadata
    processed_result JSON,            -- Parsed and structured result
    error_message TEXT,
    error_type VARCHAR,
    error_step VARCHAR,
    ai_model_used VARCHAR,           -- e.g., 'gemini-2.0-flash-lite'
    ai_tokens_used INTEGER,
    created_at DATETIME,
    FOREIGN KEY(processing_request_id) REFERENCES processing_requests (id),
    FOREIGN KEY(document_id) REFERENCES pdf_documents (id)
);
```

#### 4. `batch_jobs`
Manages batch processing jobs:
```sql
CREATE TABLE batch_jobs (
    id CHAR(36) PRIMARY KEY,
    batch_id VARCHAR(36) UNIQUE,
    status VARCHAR(20),              -- 'pending', 'processing', 'completed', 'failed'
    webhook_url VARCHAR(255),
    source VARCHAR(50),
    batch_metadata JSON,
    created_at DATETIME,
    updated_at DATETIME,
    completed_at DATETIME,
    total_files INTEGER,
    processed_files INTEGER,
    failed_files INTEGER,
    request_data JSON
);
```

#### 5. `batch_documents`
Links documents to batch jobs:
```sql
CREATE TABLE batch_documents (
    id CHAR(36) PRIMARY KEY,
    batch_id CHAR(36) NOT NULL,
    document_id CHAR(36) NOT NULL,
    status VARCHAR,                  -- 'pending', 'processing', 'completed', 'failed'
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY(batch_id) REFERENCES batch_jobs (id),
    FOREIGN KEY(document_id) REFERENCES pdf_documents (id)
);
```

## Data Flow

### Single Document Processing
1. **Document Creation**: Create or find existing document in `pdf_documents`
2. **Processing Request**: Create `processing_requests` record with status='processing'
3. **AI Processing**: For each requested operation (metadata, references):
   - Call Gemini API
   - Store raw response and processed result in `ai_processing_results`
4. **Completion**: Update `processing_requests` status to 'completed'

### Batch Processing
1. **Batch Creation**: Create `batch_jobs` record
2. **Document Processing**: For each document:
   - Create `pdf_documents` record
   - Create `batch_documents` link
   - Create `processing_requests` record
   - Process and store results in `ai_processing_results`
3. **Batch Completion**: Update counters and status in `batch_jobs`

## Raw AI Response Storage

The `raw_ai_response` field in `ai_processing_results` stores the complete AI response with metadata:

```json
{
  "text": "Complete raw response text from AI...",
  "model": "gemini-2.0-flash-lite",
  "processing_time_ms": 1500,
  "timestamp": "2025-06-02T14:08:49.807172",
  "request_type": "metadata_extraction",
  "processing_service": "enhanced_processing_service",
  "extraction_options": {
    "complete_references": false
  },
  "usage_metadata": {
    "prompt_token_count": 1234,
    "candidates_token_count": 567,
    "total_token_count": 1801
  },
  "candidates": [...],
  "detail_extraction_error": "..." // if any
}
```

## Analytics Queries

### Dashboard Analytics
```sql
-- Total processing requests by status
SELECT status, COUNT(*) as count 
FROM processing_requests 
GROUP BY status;

-- Processing time analytics
SELECT 
    processing_type,
    AVG(processing_time_ms) as avg_time,
    MIN(processing_time_ms) as min_time,
    MAX(processing_time_ms) as max_time
FROM ai_processing_results 
GROUP BY processing_type;

-- AI model usage
SELECT 
    ai_model_used,
    COUNT(*) as usage_count,
    SUM(ai_tokens_used) as total_tokens
FROM ai_processing_results 
GROUP BY ai_model_used;

-- Daily processing volume
SELECT 
    DATE(created_at) as date,
    COUNT(*) as requests,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
FROM processing_requests 
GROUP BY DATE(created_at) 
ORDER BY date DESC;
```

### Batch Analytics
```sql
-- Batch completion rates
SELECT 
    status,
    COUNT(*) as batch_count,
    AVG(processed_files) as avg_processed,
    AVG(failed_files) as avg_failed
FROM batch_jobs 
GROUP BY status;

-- Batch processing efficiency
SELECT 
    id,
    batch_id,
    total_files,
    processed_files,
    failed_files,
    ROUND((processed_files * 100.0 / total_files), 2) as success_rate
FROM batch_jobs 
WHERE total_files > 0;
```

## API Endpoints

### Processing Status
- `GET /api/v1/processing/{request_id}` - Get processing status with results
- Returns complete raw AI responses and processed results

### Batch Status  
- `GET /dashboard/batch/{batch_id}` - Batch details page
- Shows individual document processing results and analytics

## Benefits of New Schema

1. **Complete AI Response Storage**: Raw responses are preserved for debugging and analysis
2. **Better Error Tracking**: Detailed error information with context
3. **Performance Analytics**: Processing times, token usage, model performance
4. **Scalable Architecture**: Supports both single and batch processing
5. **Audit Trail**: Complete history of processing requests and results
6. **Rich Analytics**: Dashboard insights into processing performance

## Migration Notes

- Old single-table approach replaced with relational design
- All processing now goes through `processing_service.py`
- Raw AI responses are captured and stored automatically
- Batch processing integrated with same schema
- Frontend updated to use new API endpoints 