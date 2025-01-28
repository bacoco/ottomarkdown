# File Processing Agent for Live Agent Studio

Author: [Cole Medin](https://www.youtube.com/@ColeMedin)

This is a specialized Python FastAPI agent that demonstrates how to handle file uploads in the Live Agent Studio. It shows how to process, store, and leverage file content in conversations with AI models.

This agent builds upon the foundation laid out in [`~sample-python-agent~/sample_supabase_agent.py`](../~sample-python-agent~/sample_supabase_agent.py), extending it with file handling capabilities.

Not all agents need file handling which is why the sample Python agent is kept simple and this one is available to help you build agents with file handling capabilities. The Live Agent Studio has file uploading built in and the files are sent in the exact format shown in this agent.

## Overview

This agent extends the base Python agent template to showcase file handling capabilities:
- Process uploaded files in base64 format
- Store file content with conversation history
- Integrate file content into AI model context
- Maintain conversation continuity with file references
- Handle multiple files in a single conversation

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Supabase account (for conversation storage)
- OpenRouter API key (for LLM access)
- Basic understanding of:
  - FastAPI and async Python
  - Base64 encoding/decoding
  - OpenRouter API
  - Supabase

## Core Components

### 1. File Processing

The agent includes robust file handling:
- Base64 decoding of uploaded files
- Text extraction and formatting using MarkItDown
- Persistent storage of file data in Supabase
- Document caching for faster subsequent queries

### 2. Conversation Management

Built on the sample Supabase agent template, this agent adds:
- File metadata storage with messages
- File content integration in conversation history
- Contextual file reference handling
- Document caching for improved performance

### 3. AI Integration

Seamless integration with OpenRouter's LLM models:
- File content as conversation context
- Maintained context across multiple messages
- Intelligent responses based on file content
- Efficient caching of document conversions

## API Routes

### 1. File to Markdown Conversion
```bash
POST /api/convert-to-markdown
```
Converts a single file to markdown format. Simple and direct conversion.

Request:
```json
{
    "file": {
        "name": "document.pdf",
        "type": "application/pdf",
        "base64": "base64_encoded_content"
    }
}
```

Response:
```json
{
    "success": true,
    "markdown": "# Converted Content\n\nYour markdown content here...",
    "error": ""
}
```

### 2. AI Agent Processing
```bash
POST /api/file-agent
```
Processes files with an AI agent, providing enhanced responses and analysis.

Request:
```json
{
    "query": "Please analyze this document and summarize key points",
    "files": [{
        "name": "document.pdf",
        "type": "application/pdf",
        "base64": "base64_encoded_content"
    }],
    "session_id": "unique_session_id",
    "user_id": "user_id",
    "request_id": "request_id"
}
```

Response:
```json
{
    "success": true,
    "markdown": "# Analysis\n\nAI-generated analysis and response..."
}
```

### 3. AI Agent with Caching
```bash
POST /api/file-agent-cached
```
Process files with AI agent, using cached markdown when available. This route stores converted markdown in Supabase for faster subsequent queries.

Request:
```json
{
    "query": "Please analyze this document and summarize key points",
    "files": [{
        "name": "document.pdf",
        "type": "application/pdf",
        "base64": "base64_encoded_content"
    }],
    "session_id": "unique_session_id",
    "user_id": "user_id",
    "request_id": "request_id",
    "use_cache": true
}
```

| Field | Type | Description |
|-------|------|-------------|
| query | string | Instructions for the AI agent |
| files | array | List of files to process |
| session_id | string | Unique session identifier |
| user_id | string | User identifier |
| request_id | string | Request identifier |
| use_cache | boolean | Whether to use cached markdown (optional, default: true) |

Response:
```json
{
    "success": true,
    "markdown": "AI-generated response based on cached or newly converted markdown"
}
```

Features:
- Stores converted markdown in Supabase for reuse
- Faster responses for subsequent queries on the same document
- Updates last_accessed timestamp for cache management
- Option to bypass cache with use_cache=false

Example curl:
```bash
curl -X POST http://localhost:8001/api/file-agent-cached \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main points?",
    "files": [{
      "name": "document.pdf",
      "type": "application/pdf",
      "base64": "'$(base64 -i document.pdf)'"
    }],
    "session_id": "session_123",
    "user_id": "user_456",
    "request_id": "req_789",
    "use_cache": true
  }'
```

## Detailed API Documentation

### Authentication
All endpoints require Bearer token authentication:
```http
Authorization: Bearer your_token_here
```

### 1. File to Markdown Conversion
```http
POST /api/convert-to-markdown
```

#### Request Body
```json
{
    "file": {
        "name": "example.pdf",
        "type": "application/pdf",
        "base64": "base64_encoded_content"
    }
}
```

| Field | Type | Description |
|-------|------|-------------|
| file.name | string | Original filename with extension |
| file.type | string | MIME type of the file |
| file.base64 | string | Base64-encoded file content |

#### Response
```json
{
    "success": true,
    "markdown": "# Converted Content\n\nMarkdown content here...",
    "error": ""
}
```

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether the conversion was successful |
| markdown | string | Converted markdown content |
| error | string | Error message if conversion failed |

#### Supported File Types
- Documents: `.pdf`, `.docx`, `.txt`
- Spreadsheets: `.xlsx`, `.csv`
- Presentations: `.pptx`
- Web: `.html`
- Images: Not supported (will return error)

### 2. AI Agent File Processing
```http
POST /api/file-agent
```

#### Request Body
```json
{
    "query": "Please analyze this document and extract key information",
    "files": [{
        "name": "document.pdf",
        "type": "application/pdf",
        "base64": "base64_encoded_content"
    }],
    "session_id": "session_123",
    "user_id": "user_456",
    "request_id": "req_789"
}
```

| Field | Type | Description |
|-------|------|-------------|
| query | string | Instructions for the AI agent |
| files | array | List of files to process |
| files[].name | string | Original filename with extension |
| files[].type | string | MIME type of the file |
| files[].base64 | string | Base64-encoded file content |
| session_id | string | Unique session identifier for conversation context |
| user_id | string | User identifier |
| request_id | string | Unique request identifier |

#### Response
```json
{
    "success": true,
    "markdown": "# Analysis Results\n\nAI-generated analysis..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether the processing was successful |
| markdown | string | AI-generated response in markdown format |

#### Features
- Maintains conversation context using session_id
- Supports multiple files in a single request
- Converts files to markdown before AI processing
- Uses OpenRouter's LLM models for enhanced analysis
- Stores conversation history in Supabase

### Error Responses
Both endpoints return similar error structures:

```json
{
    "success": false,
    "error": "Detailed error message",
    "markdown": ""
}
```

Common HTTP Status Codes:
- 200: Success
- 400: Bad Request (invalid input)
- 401: Unauthorized (invalid token)
- 500: Internal Server Error

### Rate Limiting
- Maximum file size: 10MB per file
- Maximum files per request: 5
- Maximum requests per minute: 60

## Setup Instructions

### Using Docker (Recommended)

1. Build the Docker image:
```bash
docker build -t file-agent .
```

2. Create a `.env` file with your configuration:
```bash
# Supabase configuration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key

# API authentication
API_BEARER_TOKEN=your_bearer_token

# OpenRouter configuration
OPENAI_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free  # Default model
```

3. Run the container:
```bash
docker run -p 8001:8001 --env-file .env file-agent
```

### Manual Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up environment variables in `.env`:
   ```
   # Supabase configuration
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_KEY=your_supabase_service_key

   # API authentication
   API_BEARER_TOKEN=your_bearer_token

   # OpenRouter configuration
   OPENAI_API_KEY=your_openrouter_api_key
   OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free  # Default model
   ```

## Project Structure

```
ottomarkdown/
├── file_agent.py          # Main FastAPI application with all routes
├── test_markdown.py       # Test script for markdown conversion
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables
├── Dockerfile           # Docker configuration
├── .dockerignore        # Docker ignore rules
├── README.md           # Documentation
├── supabase/           # Supabase configuration
│   └── migrations/     # Database migrations
│       └── 20250128_document_cache.sql  # Document cache table setup
├── test_files/         # Test files for conversion
└── markdown_results/   # Output directory for converted files

```

## Database Setup

### 1. Supabase Setup

1. Create a new Supabase project at [https://supabase.com](https://supabase.com)

2. Get your project credentials:
   - Project URL
   - Service Role Key (for admin access)
   - anon/public key (for client access)

3. Create the document cache table:
   ```sql
   -- Run this in Supabase SQL editor or use migrations
   create table if not exists document_cache (
       id bigint generated by default as identity primary key,
       doc_hash text not null unique,
       file_name text not null,
       file_type text not null,
       markdown_content text not null,
       created_at timestamp with time zone not null,
       last_accessed timestamp with time zone not null
   );

   -- Create index for faster lookups
   create index if not exists idx_document_cache_hash on document_cache(doc_hash);

   -- Add RLS policies
   alter table document_cache enable row level security;

   -- Allow read access to authenticated users
   create policy "Users can read document cache"
       on document_cache for select
       using (true);

   -- Allow insert/update access to authenticated users
   create policy "Users can insert document cache"
       on document_cache for insert
       with check (true);

   create policy "Users can update document cache"
       on document_cache for update
       using (true);
   ```

4. Using migrations (recommended for production):
   ```bash
   # Create migrations directory
   mkdir -p supabase/migrations

   # Copy SQL file
   cp supabase/migrations/20250128_document_cache.sql to your project

   # Apply migration using Supabase CLI
   supabase migration up
   ```

### 2. Environment Variables

Create a `.env` file with your Supabase credentials:
```bash
# Supabase configuration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key

# API authentication
API_BEARER_TOKEN=your_bearer_token

# OpenRouter configuration
OPENAI_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free  # Default model
```

### 3. Database Management

The document cache table includes:
- `doc_hash`: Unique identifier for each document (based on content)
- `file_name`: Original filename
- `file_type`: MIME type of the file
- `markdown_content`: Converted markdown content
- `created_at`: When the document was first cached
- `last_accessed`: Last time the document was accessed

Cache cleanup (optional):
```sql
-- Delete entries not accessed in the last 30 days
DELETE FROM document_cache
WHERE last_accessed < NOW() - INTERVAL '30 days';
```

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ottomarkdown.git
cd ottomarkdown
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. Create required directories:
```bash
mkdir -p test_files markdown_results
```

6. Run the application:
```bash
uvicorn file_agent:app --reload --port 8001
```

## Testing

1. Add test files to `test_files/` directory

2. Run conversion tests:
```bash
python test_markdown.py
```

3. Test the API with curl:
```bash
# Test markdown conversion
curl -X POST http://localhost:8001/api/convert-to-markdown \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d @test_payload.json

# Test AI agent with caching
curl -X POST http://localhost:8001/api/file-agent-cached \
  -H "Authorization: Bearer your_token" \
  -H "Content-Type: application/json" \
  -d @test_payload.json
```

## Running the Agent

Start the agent with:
```bash
python file_agent.py
```

The agent will be available at `http://localhost:8001`.

## API Usage

Send requests to `/api/file-agent` with:
- `query`: Your question or prompt
- `files`: Array of file objects with:
  - `name`: Filename
  - `type`: MIME type
  - `base64`: Base64-encoded file content

Example request:
```json
{
  "query": "What does this file contain?",
  "files": [{
    "name": "example.txt",
    "type": "text/plain",
    "base64": "VGhpcyBpcyBhIHRlc3QgZmlsZS4="
  }],
  "session_id": "unique-session-id",
  "user_id": "user-id",
  "request_id": "request-id"
}
```

## Contributing

This agent is part of the oTTomator agents collection. For contributions or issues, please refer to the main repository guidelines.

## Curl Examples

### Quick Reference

```bash
# 1. Convert a file to markdown
curl -X POST http://localhost:8001/api/convert-to-markdown \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "file": {
      "name": "document.pdf",
      "type": "application/pdf",
      "base64": "'$(base64 -i document.pdf)'"
    }
  }'

# 2. Process with AI agent
curl -X POST http://localhost:8001/api/file-agent \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Please analyze this document",
    "files": [{
      "name": "document.pdf",
      "type": "application/pdf",
      "base64": "'$(base64 -i document.pdf)'"
    }],
    "session_id": "session_123",
    "user_id": "user_456",
    "request_id": "req_789"
  }'
```

### Helper Script
Save this as `call_api.sh`:

```bash
#!/bin/bash

TOKEN="your_token_here"
API_URL="http://localhost:8001"

# Function to convert file to markdown
convert_to_markdown() {
    local file_path=$1
    local file_name=$(basename "$file_path")
    local mime_type=$(file --mime-type -b "$file_path")
    
    curl -X POST "$API_URL/api/convert-to-markdown" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "file": {
                "name": "'$file_name'",
                "type": "'$mime_type'",
                "base64": "'$(base64 -i "$file_path")'"
            }
        }'
}

# Function to process with AI agent
process_with_agent() {
    local file_path=$1
    local query=$2
    local file_name=$(basename "$file_path")
    local mime_type=$(file --mime-type -b "$file_path")
    
    curl -X POST "$API_URL/api/file-agent" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "query": "'$query'",
            "files": [{
                "name": "'$file_name'",
                "type": "'$mime_type'",
                "base64": "'$(base64 -i "$file_path")'"
            }],
            "session_id": "session_'$(date +%s)'",
            "user_id": "user_test",
            "request_id": "req_'$(date +%s)'"
        }'
}

# Usage examples:
# ./call_api.sh convert document.pdf
# ./call_api.sh process document.pdf "Summarize this document"

case "$1" in
    "convert")
        convert_to_markdown "$2"
        ;;
    "process")
        process_with_agent "$2" "$3"
        ;;
    *)
        echo "Usage:"
        echo "  Convert to markdown: $0 convert <file_path>"
        echo "  Process with agent: $0 process <file_path> \"query\""
        exit 1
        ;;
esac
```

### Example Usage

1. Make the script executable:
```bash
chmod +x call_api.sh
```

2. Convert a file to markdown:
```bash
./call_api.sh convert path/to/document.pdf
```

3. Process a file with AI:
```bash
./call_api.sh process path/to/document.pdf "Analyze this document and summarize key points"
```

4. Process multiple files (raw curl):
```bash
curl -X POST http://localhost:8001/api/file-agent \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare these documents",
    "files": [
      {
        "name": "document1.pdf",
        "type": "application/pdf",
        "base64": "'$(base64 -i document1.pdf)'"
      },
      {
        "name": "document2.pdf",
        "type": "application/pdf",
        "base64": "'$(base64 -i document2.pdf)'"
      }
    ],
    "session_id": "session_123",
    "user_id": "user_456",
    "request_id": "req_789"
  }'
```

5. Convert HTML (raw curl):
```bash
curl -X POST http://localhost:8001/api/convert-to-markdown \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "file": {
      "name": "page.html",
      "type": "text/html",
      "base64": "'$(base64 -i page.html)'"
    }
  }'

```
