# OttoMarkdown - AI-Powered Document Processing for Ottomator

## Overview
OttoMarkdown is an intelligent document processing agent that enhances Ottomator's capabilities by providing seamless file handling, smart caching, and AI-powered document analysis. Built with FastAPI and integrated with OpenRouter's LLMs, it offers a robust solution for processing and analyzing various document formats.

## Key Features

### 1. Universal Document Processing
- Supports multiple file formats (PDF, DOCX, XLSX, HTML, etc.)
- Intelligent markdown conversion using MarkItDown
- Clean and consistent output formatting

### 2. Smart Caching System
- Document-level caching in Supabase
- Hash-based content tracking
- Efficient retrieval for repeated queries
- Reduced processing time and API costs

### 3. AI-Powered Analysis
- Integration with OpenRouter's meta-llama/llama-3.2-3b-instruct model
- Context-aware document analysis
- Conversation history integration
- Multi-document processing in a single request

### 4. Production-Ready Architecture
- FastAPI for high-performance async operations
- Docker containerization
- Comprehensive error handling
- Detailed logging and monitoring
- Authentication and security measures

## Demo Video
[Link to demo video showing the agent in action]

## Installation

1. Clone the repository:
```bash
git clone [your-repo-url]
cd ottomarkdown
```

2. Set up environment variables:
```bash
# Supabase configuration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key

# API authentication
API_BEARER_TOKEN=your_bearer_token

# OpenRouter configuration
OPENAI_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
```

3. Run with Docker:
```bash
docker build -t ottomarkdown .
docker run -p 8001:8001 --env-file .env ottomarkdown
```

## Usage Example

```python
import requests
import base64

# Read file
with open("document.pdf", "rb") as f:
    base64_content = base64.b64encode(f.read()).decode()

# Process with AI
response = requests.post(
    "http://localhost:8001/api/file-agent-cached",
    headers={"Authorization": "Bearer your_token"},
    json={
        "query": "Summarize the key points of this document",
        "files": [{
            "name": "document.pdf",
            "type": "application/pdf",
            "base64": base64_content
        }],
        "session_id": "demo-session",
        "user_id": "demo-user",
        "request_id": "demo-request"
    }
)

print(response.json()["markdown"])
```

## Technical Details

### Architecture
```
┌─────────────┐     ┌──────────┐     ┌───────────┐
│ FastAPI App │ ─── │ Supabase │ ─── │ OpenRouter│
└─────────────┘     └──────────┘     └───────────┘
       │                  │                │
       │            ┌──────────┐          │
       └────────── │ Document  │ ─────────┘
                   │  Cache    │
                   └──────────┘
```

### Performance
- Average response time: ~2s for cached documents
- ~5-10s for new document processing
- Supports concurrent requests
- Efficient memory usage with stream processing

## Future Enhancements
1. Batch processing capabilities
2. Advanced document comparison
3. Custom model fine-tuning
4. Real-time collaboration features
5. Enhanced caching strategies

## Team
- [Your Name] - Developer
- Built during the Ottomator Hackathon 2025
