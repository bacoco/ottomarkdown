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

# Load environment variables
load_dotenv()

# Initialize FastAPI app and OpenAI client
app = FastAPI()
security = HTTPBearer()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize MarkItDown globally
md = MarkItDown(llm_client=openai_client, llm_model=os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.2-3b-instruct:free"))

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
    file: Dict[str, Any]

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
    message_obj = {
        "type": message_type,
        "content": content
    }
    if data:
        message_obj["data"] = data

    try:
        supabase.table("messages").insert({
            "session_id": session_id,
            "message": message_obj
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store message: {str(e)}")

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
    content = file_data.get('base64', '')
    name = file_data.get('name', '')
    return hashlib.sha256(f"{content}{name}".encode()).hexdigest()

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
        # Save base64 content to a temporary file
        decoded_content = base64.b64decode(request.file['base64'])
        temp_file_path = f"/tmp/temp_file_{request.file['name']}"
        
        try:
            with open(temp_file_path, "wb") as f:
                f.write(decoded_content)
            
            # Convert file to markdown using MarkItDown
            result = md.convert(temp_file_path)
            markdown_content = result.text_content
            
            # Clean up temporary file
            os.remove(temp_file_path)
            
            return MarkdownResponse(
                success=True,
                markdown=markdown_content
            )
            
        except Exception as e:
            # Fallback to direct text conversion if markdown conversion fails
            try:
                text_content = decoded_content.decode('utf-8')
                return MarkdownResponse(
                    success=True,
                    markdown=text_content
                )
            except:
                return MarkdownResponse(
                    success=False,
                    error=f"Failed to process file {request.file['name']}: {str(e)}"
                )
        
    except Exception as e:
        return MarkdownResponse(
            success=False,
            error=f"Error processing request: {str(e)}"
        )

@app.post("/api/file-agent-cached", response_model=AgentResponse)
async def process_files_cached(
    request: Request,
    query: str,
    files: List[Dict[str, Any]],
    session_id: str,
    user_id: str,
    request_id: str,
    use_cache: bool = True
):
    """
    Process files with AI agent, using cached markdown when available
    
    Parameters:
    - query: User's question about the documents
    - files: List of file data (name, type, base64)
    - session_id: Session identifier for conversation context
    - user_id: User identifier
    - request_id: Request identifier
    - use_cache: Whether to use cached markdown (default: True)
    """
    try:
        # Verify token
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if token != os.getenv("API_BEARER_TOKEN"):
            raise HTTPException(status_code=401, detail="Invalid token")

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
            return AgentResponse(
                success=False,
                markdown="",
                error="Failed to process any files"
            )
        
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
        
        return AgentResponse(
            success=True,
            markdown=ai_response
        )
        
    except Exception as e:
        logging.error(f"Error in process_files_cached: {str(e)}")
        return AgentResponse(
            success=False,
            markdown="",
            error=f"Error processing request: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    # Feel free to change the port here if you need
    uvicorn.run(app, host="0.0.0.0", port=8001)
