from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
import sys
import os
import base64
from openai import OpenAI
from markitdown import MarkItDown
import hashlib
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)  # Force reload environment variables

# Initialize FastAPI app and OpenRouter client
app = FastAPI()
security = HTTPBearer()
openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "http://localhost:8001",  # Required for OpenRouter
        "X-Title": "MarkItDown App",  # Optional, for OpenRouter analytics
    }
)

# Initialize MarkItDown globally
md = MarkItDown(
    llm_client=openai_client,
    llm_model=os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")
)

# Supabase setup
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class AgentRequest(BaseModel):
    query: str
    user_id: str
    request_id: str
    session_id: str
    files: Optional[List[Dict[str, Any]]] = None

class AgentResponse(BaseModel):
    success: bool
    markdown: str = ""
    error: Optional[str] = ""

class FileRequest(BaseModel):
    file: Dict[str, Any]  # Should include name, base64, type, and optionally model

class MarkdownResponse(BaseModel):
    success: bool
    markdown: str = ""
    error: str = ""

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """Verify the bearer token against environment variable."""
    expected_token = os.getenv("API_BEARER_TOKEN")
    if not expected_token:
        raise HTTPException(
            status_code=500,
            detail="API_BEARER_TOKEN environment variable not set"
        )
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )
    return True

async def fetch_conversation_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch the most recent conversation history for a session."""
    try:
        response = supabase.table("messages") \
            .select("*") \
            .eq("session_id", session_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        # Convert to list and reverse to get chronological order
        messages = response.data[::-1]
        return messages
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversation history: {str(e)}")

async def store_message(session_id: str, message_type: str, content: str, data: Optional[Dict] = None):
    """Store a message in the Supabase messages table."""
    try:
        # Truncate content if it's too large (100KB limit)
        max_content_size = 100000  # 100KB
        if len(content) > max_content_size:
            content = content[:max_content_size] + "\n...(truncated)"
            logger.warning(f"Message content truncated to {max_content_size} characters")

        # Ensure data is a valid JSON object
        if data is None:
            data = {}

        # Create message object
        message = {
            "session_id": session_id,
            "message_type": message_type,
            "content": content,
            "data": data
        }
        
        # Insert message into Supabase
        response = supabase.table("messages").insert(message).execute()
        
        # Check for errors
        if hasattr(response, 'error') and response.error is not None:
            raise Exception(f"Failed to store message: {response.error}")
            
    except Exception as e:
        logger.error(f"Failed to store message: {e}")
        # Don't raise the exception, just log it
        # This prevents message storage failures from breaking the main functionality

async def process_files_to_string(files: Optional[List[Dict[str, Any]]]) -> str:
    """Convert a list of files with base64 content into a formatted string using MarkItDown."""
    if not files:
        return ""
        
    file_content = "File content to use as context:\n\n"
    
    for i, file in enumerate(files, 1):
        try:
            # Save base64 content to a temporary file
            decoded_content = base64.b64decode(file['base64'])
            temp_file_path = f"/tmp/temp_file_{i}"
            with open(temp_file_path, "wb") as f:
                f.write(decoded_content)
            
            # Convert file to markdown using MarkItDown
            result = md.convert(temp_file_path)
            markdown_content = result.text_content
            
            # Clean up temporary file
            os.remove(temp_file_path)
            
            file_content += f"{i}. {file['name']}:\n\n{markdown_content}\n\n"
        except Exception as e:
            print(f"Error processing file {file['name']}: {str(e)}")
            # Fallback to direct text conversion if markdown conversion fails
            try:
                text_content = decoded_content.decode('utf-8')
                file_content += f"{i}. {file['name']} (plain text):\n\n{text_content}\n\n"
            except:
                file_content += f"{i}. {file['name']} (failed to process)\n\n"
    
    return file_content

async def get_document_hash(file_data: Dict[str, Any]) -> str:
    """Generate a unique hash for a document based on its content"""
    content = file_data.get('base64', '') or file_data.get('content', '')
    name = file_data.get('name', '')
    file_type = file_data.get('type', '')
    
    # Combine all fields to create a unique hash
    hash_input = f"{content}{name}{file_type}".encode('utf-8')
    return hashlib.sha256(hash_input).hexdigest()

async def store_document_markdown(
    supabase_client,
    doc_hash: str,
    markdown: str,
    file_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Store document markdown in Supabase"""
    doc_data = {
        'doc_hash': doc_hash,
        'file_name': file_data.get('name'),
        'file_type': file_data.get('type'),
        'markdown_content': markdown,
        'created_at': datetime.utcnow().isoformat(),
        'last_accessed': datetime.utcnow().isoformat()
    }
    
    result = supabase_client.table('document_cache').upsert(doc_data).execute()
    return result.data[0] if result.data else None

async def get_cached_markdown(
    supabase_client,
    doc_hash: str
) -> Optional[str]:
    """Retrieve cached markdown from Supabase"""
    result = supabase_client.table('document_cache')\
        .select('markdown_content')\
        .eq('doc_hash', doc_hash)\
        .execute()
    
    if result.data:
        # Update last accessed timestamp
        supabase_client.table('document_cache')\
            .update({'last_accessed': datetime.utcnow().isoformat()})\
            .eq('doc_hash', doc_hash)\
            .execute()
        return result.data[0]['markdown_content']
    return None

@app.post("/api/file-agent", response_model=AgentResponse)
async def file_agent(
    request: AgentRequest,
    authenticated: bool = Depends(verify_token)
):
    try:
        # Fetch conversation history from the DB
        conversation_history = await fetch_conversation_history(request.session_id)
        
        # Convert conversation history to format expected by agent
        messages = []
        for msg in conversation_history:
            msg_data = msg["message"]
            msg_type = "user" if msg_data["type"] == "human" else "assistant"
            msg_content = msg_data["content"]
            
            messages.append({"role": msg_type, "content": msg_content})

        # Store user's query with files if present
        message_data = {"request_id": request.request_id}
        if request.files:
            message_data["files"] = request.files

        await store_message(
            session_id=request.session_id,
            message_type="human",
            content=request.query,
            data=message_data
        )

        # Get markdown content from files
        markdown_content = ""
        if request.files:
            markdown_content = await process_files_to_string(request.files)

        # Store agent's response
        await store_message(
            session_id=request.session_id,
            message_type="ai",
            content=markdown_content,
            data={"request_id": request.request_id}
        )

        return AgentResponse(success=True, markdown=markdown_content)

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        # Store error message in conversation
        await store_message(
            session_id=request.session_id,
            message_type="ai",
            content="I apologize, but I encountered an error processing your request.",
            data={"error": str(e), "request_id": request.request_id}
        )
        return AgentResponse(success=False, markdown="")

@app.post("/api/convert-to-markdown", response_model=MarkdownResponse)
async def convert_to_markdown(
    request: FileRequest,
    authenticated: bool = Depends(verify_token)
):
    """Convert a single file to markdown format."""
    try:
        logger.info(f"Processing file: {request.file['name']}")
        
        # Save base64 content to a temporary file
        decoded_content = base64.b64decode(request.file['base64'])
        temp_file_path = f"/tmp/temp_file_{request.file['name']}"
        
        try:
            with open(temp_file_path, "wb") as f:
                f.write(decoded_content)
            logger.info(f"Saved content to temporary file: {temp_file_path}")
            
            # Create a new MarkItDown instance with appropriate model
            if 'model' in request.file:
                logger.info(f"Using vision model: {os.getenv('OPENROUTER_VLM_MODEL')}")
                try:
                    # Create a new MarkItDown instance with the vision model
                    temp_md = MarkItDown(
                        llm_client=openai_client,
                        llm_model=os.getenv("OPENROUTER_VLM_MODEL")
                    )
                    result = temp_md.convert(temp_file_path, use_llm=True)
                    if not result.text_content:
                        raise Exception("Vision model returned empty response")
                    logger.info("Successfully used vision model")
                except Exception as vision_error:
                    if "401" in str(vision_error):
                        logger.error(f"Vision model access unauthorized: {str(vision_error)}")
                        return MarkdownResponse(
                            success=False,
                            error=f"API key does not have access to vision model {os.getenv('OPENROUTER_VLM_MODEL')}"
                        )
                    logger.error(f"Vision model error: {str(vision_error)}")
                    return MarkdownResponse(
                        success=False,
                        error=f"Error using vision model: {str(vision_error)}"
                    )
            else:
                # Use default model for non-image files
                temp_md = MarkItDown(
                    llm_client=openai_client,
                    llm_model=os.getenv("OPENROUTER_MODEL")
                )
                result = temp_md.convert(temp_file_path, use_llm=True)
            
            markdown_content = result.text_content
            if not markdown_content:
                raise Exception("No markdown content generated")
            
            logger.info(f"Successfully converted file. Output length: {len(markdown_content)}")
            
            # Clean up temporary file
            os.remove(temp_file_path)
            logger.info("Cleaned up temporary file")
            
            return MarkdownResponse(
                success=True,
                markdown=markdown_content
            )
            
        except Exception as e:
            logger.error(f"Error converting file: {str(e)}")
            # Fallback to direct text conversion if markdown conversion fails
            try:
                text_content = decoded_content.decode('utf-8')
                logger.info("Fallback: Using direct text conversion")
                return MarkdownResponse(
                    success=True,
                    markdown=text_content
                )
            except:
                error_msg = f"Failed to process file {request.file['name']}: {str(e)}"
                logger.error(error_msg)
                return MarkdownResponse(
                    success=False,
                    error=error_msg
                )
        
    except Exception as e:
        error_msg = f"Error processing request: {str(e)}"
        logger.error(error_msg)
        return MarkdownResponse(
            success=False,
            error=error_msg
        )

@app.post("/api/file-agent-cached", response_model=AgentResponse)
async def process_files_cached(
    request: Request,
    query: str,
    files: List[Dict[str, Any]] = [],
    session_id: str = "",
    user_id: str = "",
    request_id: str = "",
    use_cache: bool = True
):
    """Process files with an AI agent, utilizing cached markdown when available."""
    try:
        # Verify token
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != os.getenv("API_BEARER_TOKEN"):
            raise HTTPException(status_code=401, detail="Invalid token")

        # Check if files list is empty
        if not files:
            return {
                "success": False,
                "error": "No files provided. Please provide at least one file to process.",
                "markdown": ""
            }

        markdown_contents = []
        
        for file_data in files:
            doc_hash = await get_document_hash(file_data)
            
            if use_cache:
                # Try to get cached markdown
                cached_markdown = await get_cached_markdown(supabase, doc_hash)
                if cached_markdown:
                    markdown_contents.append(cached_markdown)
                    continue
            
            # Convert file if not in cache
            try:
                # Process single file
                markdown = await process_files_to_string([file_data])
                if markdown:
                    # Store in cache
                    await store_document_markdown(supabase, doc_hash, markdown, file_data)
                    markdown_contents.append(markdown)
            except Exception as e:
                logging.error(f"Error processing file {file_data.get('name')}: {str(e)}")
                continue
        
        if not markdown_contents:
            return {
                "success": False,
                "error": "Failed to process any files. Please check the file formats and try again.",
                "markdown": ""
            }

        # Combine all markdown contents
        combined_markdown = "\n\n---\n\n".join(markdown_contents)
        
        # Store the query and response in conversation history
        await store_message(session_id, "user", query)
        
        # Get conversation history
        history = await fetch_conversation_history(session_id)
        
        # Create a prompt with context
        prompt = f"Context:\n{combined_markdown}\n\nConversation History:\n{history}\n\nUser Question: {query}\n\nAnswer:"
        
        # Save prompt to temporary file for MarkItDown
        temp_file = "/tmp/prompt.txt"
        with open(temp_file, "w") as f:
            f.write(prompt)
        
        # Get AI response using MarkItDown
        result = md.convert(temp_file)
        ai_response = result.text_content
        
        # Clean up
        os.remove(temp_file)
        
        # Store AI response in conversation history
        await store_message(session_id, "assistant", ai_response)
        
        return {
            "success": True,
            "markdown": ai_response
        }

    except Exception as e:
        logging.error(f"Error in process_files_cached: {str(e)}")
        return {
            "success": False,
            "error": f"Error processing request: {str(e)}",
            "markdown": ""
        }

if __name__ == "__main__":
    import uvicorn
    # Feel free to change the port here if you need
    uvicorn.run(app, host="0.0.0.0", port=8001)
