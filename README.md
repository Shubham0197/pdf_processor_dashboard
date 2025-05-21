# PDF Processing API

A robust API service for processing PDF documents using Google's Gemini AI model to extract metadata, references, and full text.

## Features

- **Batch Processing**: Process multiple PDFs in a single request
- **Metadata Extraction**: Extract article metadata (title, authors, abstract, etc.)
- **Reference Extraction**: Extract and structure references from academic papers
- **Secure API Key Management**: Store and manage API keys securely
- **Dashboard**: Monitor processing jobs and view results
- **Webhook Integration**: Send results back to your application

## Requirements

- Python 3.8+
- PostgreSQL
- Google Gemini API key

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/pdf-processing-api.git
cd pdf-processing-api
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

5. Edit the `.env` file with your configuration:

```
# Database settings
DATABASE_URL=postgresql://user:password@localhost/pdf_processing

# Security settings
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# API settings
API_HOST=0.0.0.0
API_PORT=8000

# Default admin user
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=changeme
```

## Running the Application

1. Start the application:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2. Access the dashboard at http://localhost:8000/dashboard
3. Access the API documentation at http://localhost:8000/api/v1/docs

## API Usage

### Authentication

All API endpoints require authentication. You can obtain an access token by logging in:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=changeme"
```

### Process a Batch of PDFs

```bash
curl -X POST "http://localhost:8000/api/v1/batch/process" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://your-app.com/webhook",
    "files": [
      {"url": "https://example.com/file1.pdf", "file_id": "doc1"},
      {"url": "https://example.com/file2.pdf", "file_id": "doc2"}
    ],
    "options": {
      "extract_references": true,
      "extract_metadata": true,
      "extract_full_text": false
    },
    "batch_id": "client-batch-123"
  }'
```

### Check Batch Status

```bash
curl -X GET "http://localhost:8000/api/v1/batch/client-batch-123/status" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Webhook Integration

When processing is complete, the API will send a POST request to your webhook URL with the following structure:

```json
{
  "batch_id": "client-batch-123",
  "status": "completed",
  "total_files": 2,
  "processed_files": 2,
  "failed_files": 0,
  "completed_at": "2025-05-20T04:30:45.123456",
  "files": [
    {
      "job_id": "job-id-1",
      "status": "completed",
      "file_url": "https://example.com/file1.pdf",
      "file_name": "doc1",
      "metadata": {
        "title": "Example Paper Title",
        "authors": [
          {"name": "John Doe", "affiliation": "University of Example"}
        ],
        "abstract": "This is an example abstract...",
        "keywords": ["keyword1", "keyword2"],
        "journal": "Journal of Examples",
        "volume": "10",
        "issue": "2",
        "year": "2023",
        "doi": "10.1234/example.2023"
      },
      "references": [
        {
          "text": "Smith, J. (2022). Example reference.",
          "doi": "10.1234/ref.2022"
        }
      ],
      "processing_time": 5432
    },
    {
      "job_id": "job-id-2",
      "status": "completed",
      "file_url": "https://example.com/file2.pdf",
      "file_name": "doc2",
      "metadata": { /* ... */ },
      "references": [ /* ... */ ],
      "processing_time": 4321
    }
  ]
}
```

## API Key Management

The system requires a Google Gemini API key to function. You can add this through the dashboard:

1. Log in to the dashboard
2. Navigate to "API Keys"
3. Click "Create New Key"
4. Select "gemini" as the key type
5. Enter your Google Gemini API key

## Integration with Django

This API is designed to work with your existing Django bibliographic data management system. Configure your Django application to:

1. Send batch requests to this API with PDF files that need processing
2. Set up a webhook endpoint to receive the processing results
3. Update your Article records with the extracted metadata

## Docker Deployment

A Dockerfile and docker-compose.yml are provided for easy deployment:

```bash
docker-compose up -d
```

## License

MIT
