import os
from openai import OpenAI
import json
from dotenv import load_dotenv, find_dotenv
import base64
from markitdown import MarkItDown
from pathlib import Path
import io
import requests
import mimetypes
import time

# Load environment variables from .env file
print("Loading .env file from:", find_dotenv())
load_dotenv(override=True)  # Force reload of environment variables

# Get and clean environment variables
api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
model = os.getenv("OPENROUTER_MODEL", "").strip()

print("\nEnvironment variables loaded:")
print("OPENROUTER_API_KEY =", api_key)
print("OPENROUTER_MODEL =", model)

# Remove any duplicated API key
if len(api_key) > 100:  # API keys are typically around 73 characters
    api_key = api_key[:73]  # Take only the first part

if not api_key:
    raise ValueError("OPENROUTER_API_KEY not found in environment variables")
if not model:
    raise ValueError("OPENROUTER_MODEL not found in environment variables")

# Validate API key format
if not api_key.startswith("sk-or-v1-"):
    raise ValueError("Invalid API key format. Should start with 'sk-or-v1-'")

def ensure_dir(directory):
    """Ensure a directory exists, create it if it doesn't"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def test_openrouter_api():
    """Test OpenRouter API connection with Llama vision model."""
    print("\nStarting OpenRouter API test...")
    
    # Load environment variables
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_VLM_MODEL")
    
    if not api_key:
        print("Error: OPENROUTER_API_KEY not found in environment variables")
        return
        
    print("Using API key:", api_key)
    print("Using VLM model:", model)
    
    try:
        # Initialize OpenRouter client
        openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "http://localhost:8001",
                "X-Title": "MarkItDown Test",
            }
        )
        
        print("\nSending request to OpenRouter API...")
        
        # Simple test prompt
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Say hello and confirm you can process images!"}
            ]
        )
        
        print("\nRaw API Response:")
        print(json.dumps(response.model_dump(), indent=2))
        
        print("\nProcessed Response:")
        print("Content:", response.choices[0].message.content)
        print("Model used:", response.model)
        
        print("\nTest completed successfully!")
        
    except Exception as e:
        print("\nError occurred during API test:")
        print("Error type:", type(e).__name__)
        print("Error message:", str(e))

def test_file_processing():
    """Test file processing capabilities without LLM calls"""
    print("\nStarting file processing test...")
    
    # Initialize MarkItDown without LLM
    md = MarkItDown(llm_client=None)
    
    # Test directory path
    test_dir = Path(__file__).parent / "test_files"
    results_dir = Path(__file__).parent / "markdown_results"
    ensure_dir(results_dir)
    
    # Process each file in the test directory
    for file_path in test_dir.glob("*"):
        # Skip .DS_Store and other hidden files
        if file_path.name.startswith('.'):
            print(f"Skipping hidden file: {file_path.name}")
            continue
            
        try:
            print(f"\nProcessing {file_path.name}...")
            
            # Convert file using MarkItDown
            result = md.convert(str(file_path))
            
            # Validate result
            if result and hasattr(result, 'text_content') and result.text_content:
                print(f"✓ Successfully processed {file_path.name}")
                print(f"  Output length: {len(result.text_content)} characters")
                print(f"  First 100 characters: {result.text_content[:100]}...")
                
                # Create markdown file name
                file_type = file_path.suffix.lower()[1:]  # Remove the dot
                base_name = file_path.stem
                md_file = results_dir / f"{base_name}_{file_type}.md"
                
                # Save markdown content
                with open(md_file, 'w', encoding='utf-8') as f:
                    if hasattr(result, 'title') and result.title:
                        print(f"  Title: {result.title}")
                        f.write(f"# {result.title}\n\n")
                    f.write(result.text_content)
                
                print(f"  Saved markdown to: {md_file}")
            else:
                print(f"✗ Failed to process {file_path.name}")
                print(f"  Result: {result}")
            
        except Exception as e:
            print(f"✗ Error processing {file_path.name}")
            print(f"  Error type: {type(e).__name__}")
            print(f"  Error message: {str(e)}")

def test_file_processing_with_llm():
    """Test processing various file types with LLM integration."""
    test_files = {
        'test_docx.docx': 'test_files/test.docx',
        'test_html.html': 'test_files/test_wikipedia.html',
        'test_pptx.pptx': 'test_files/test.pptx',
        'test_pdf.pdf': 'test_files/test.pdf',
        'test_xlsx.xlsx': 'test_files/test.xlsx'
    }
    
    # Initialize OpenRouter client with Llama vision model
    openai_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        default_headers={
            "HTTP-Referer": "http://localhost:8001",
            "X-Title": "MarkItDown Test",
        }
    )

    # Initialize MarkItDown with Llama vision model
    md = MarkItDown(
        llm_client=openai_client,
        llm_model=os.getenv("OPENROUTER_VLM_MODEL")
    )
    
    # Create output directory if it doesn't exist
    os.makedirs('markdown_results', exist_ok=True)
    
    for output_name, input_path in test_files.items():
        try:
            print(f"\nProcessing {input_path} with LLM...")
            # Convert file to markdown with LLM enabled
            result = md.convert(input_path, use_llm=True)
            
            # Save the markdown content
            output_path = f'markdown_results/{output_name.rsplit(".", 1)[0]}.md'
            with open(output_path, 'w') as f:
                if hasattr(result, 'title') and result.title:
                    f.write(f"# {result.title}\n\n")
                f.write(result.text_content)
                
            print(f"Successfully processed {input_path}")
            print(f"Output saved to: {output_path}")
            print(f"First 100 characters: {result.text_content[:100]}...")
            
        except Exception as e:
            print(f"Error processing {input_path}: {str(e)}")
            print(f"Error type: {type(e).__name__}")

def test_image_processing_with_llm():
    """Test processing image files with LLM integration for descriptions."""
    print("\nTesting image processing with LLM...")
    
    # Initialize OpenRouter client with Llama vision model
    openai_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        default_headers={
            "HTTP-Referer": "http://localhost:8001",
            "X-Title": "MarkItDown Test",
        }
    )

    # Initialize MarkItDown with Llama vision model
    md = MarkItDown(
        llm_client=openai_client,
        llm_model=os.getenv("OPENROUTER_VLM_MODEL")
    )
    
    # Create output directory if it doesn't exist
    os.makedirs('markdown_results', exist_ok=True)
    
    # Test with an image file
    try:
        image_path = 'test_files/image.jpg'
        print(f"Processing image: {image_path}")
        result = md.convert(image_path, use_llm=True)
        
        # Save the markdown content
        output_path = 'markdown_results/test_image.md'
        with open(output_path, 'w') as f:
            f.write(result.text_content)
            
        print(f"Successfully processed {image_path} with Llama Vision")
        print(f"Output saved to: {output_path}")
        print(f"Generated description: {result.text_content[:200]}...")
        
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        print(f"Error type: {type(e).__name__}")

def test_api_file_agent_cached():
    print("\nTesting /api/file-agent-cached endpoint...")
    
    # Get list of test files
    test_files = os.listdir('test_files')
    print(f"Processing {len(test_files)} files:")
    for f in test_files:
        print(f"- {f}")
    print()
    
    # Process one file at a time to avoid timeouts
    batch_size = 1
    max_retries = 5  # Increased from 3 to 5
    content_size_limit = 100000  # Reduced from 200KB to 100KB
    
    for i in range(0, len(test_files), batch_size):
        batch = test_files[i:i + batch_size]
        files_data = []
        
        for file_name in batch:
            file_path = os.path.join('test_files', file_name)
            if os.path.getsize(file_path) > content_size_limit:
                print(f"⚠️ {file_name} exceeds size limit ({os.path.getsize(file_path)} bytes). Content will be truncated.")
            
            try:
                with open(file_path, 'rb') as f:
                    content = f.read(content_size_limit)
                    base64_content = base64.b64encode(content).decode('utf-8')
                    print(f"✓ Successfully encoded {file_name}")
                    files_data.append({
                        'name': file_name,
                        'base64': base64_content,
                        'type': os.path.splitext(file_name)[1][1:]  # Get file extension without dot
                    })
            except Exception as e:
                print(f"✗ Failed to encode {file_name}: {str(e)}")
                continue
        
        if not files_data:
            continue
            
        # Try the request with retries and exponential backoff
        success = False
        for retry in range(max_retries):
            try:
                response = requests.post(
                    'http://localhost:8001/api/file-agent-cached',
                    params={
                        'query': '',
                        'session_id': 'test_session_123',
                        'user_id': 'test_user_123',
                        'request_id': 'test_request_123',
                        'use_cache': 'true'
                    },
                    json=files_data,
                    headers={'Authorization': f'Bearer {os.getenv("API_BEARER_TOKEN")}'}
                )
                
                print(f"\nStatus Code: {response.status_code}")
                
                if response.status_code == 200:
                    success = True
                    break
                else:
                    print(f"Attempt {retry + 1} failed. Status: {response.status_code}")
                    if retry < max_retries - 1:
                        delay = min(30, (2 ** retry) * 5)  # Exponential backoff, max 30 seconds
                        print(f"Waiting {delay} seconds before retry...")
                        time.sleep(delay)
            except Exception as e:
                print(f"Request failed: {str(e)}")
                if retry < max_retries - 1:
                    delay = min(30, (2 ** retry) * 5)  # Exponential backoff, max 30 seconds
                    print(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)
        
        if success and 'application/json' in response.headers.get('content-type', ''):
            result = response.json()
            print("Success! Response:\n")
            
            if 'markdown' in result:
                print("\nMarkdown content (first 100 chars for each file):")
                content = result['markdown']
                current_file = None
                current_content = []
                
                for line in content.split('\n'):
                    # Skip metadata lines and embedded content
                    if (line.startswith('[') or line.startswith('{') or 
                        'data:' in line or '[![' in line or '![' in line):
                        continue
                        
                    if line.startswith('1. ') and ':' in line:
                        # If we have a previous file, save it
                        if current_file and current_content:
                            # Clean up the content
                            clean_content = []
                            for c in current_content:
                                if not (c.startswith('[') or c.startswith('{') or 
                                      'Context:' in c or 'data:' in c or '[![' in c or '![' in c):
                                    clean_content.append(c)
                            
                            # Only save if we have actual content and it's a real file
                            if clean_content and current_file in test_files:
                                name_without_ext = os.path.splitext(current_file)[0]
                                file_type = os.path.splitext(current_file)[1][1:]  # Remove the dot
                                output_file = os.path.join('markdown_results', f'file_{name_without_ext}_{file_type}.md')
                                with open(output_file, 'w') as f:
                                    f.write('\n'.join(clean_content))
                                print(f"\nSaved {current_file} content to: {output_file}")
                        
                        # Start new file
                        current_file = line.split(':')[0].split('1. ')[1].strip()
                        current_content = [line]
                    else:
                        if current_content:  # Only append if we have started a file
                            current_content.append(line)
                
                # Save the last file
                if current_file and current_content:
                    # Clean up the content
                    clean_content = []
                    for c in current_content:
                        if not (c.startswith('[') or c.startswith('{') or 
                              'Context:' in c or 'data:' in c or '[![' in c or '![' in c):
                            clean_content.append(c)
                    
                    # Only save if we have actual content and it's a real file
                    if clean_content and current_file in test_files:
                        name_without_ext = os.path.splitext(current_file)[0]
                        file_type = os.path.splitext(current_file)[1][1:]  # Remove the dot
                        output_file = os.path.join('markdown_results', f'file_{name_without_ext}_{file_type}.md')
                        with open(output_file, 'w') as f:
                            f.write('\n'.join(clean_content))
                        print(f"\nSaved {current_file} content to: {output_file}")
            else:
                print(f"Error: {response.text}")
            
            # Add a delay between requests to avoid overwhelming the server
            # Use a longer delay for larger files
            if i + batch_size < len(test_files):
                delay = 5 if len(files_data[0]['base64']) > 500000 else 2
                print(f"\nWaiting {delay} seconds before next request...")
                time.sleep(delay)
        
        # Add a delay between requests to avoid overwhelming the server
        # if i + batch_size < len(test_files):
        #     print("\nWaiting 2 seconds before next request...")
        #     time.sleep(2)

def test_convert_to_markdown():
    print("\nTesting /api/convert-to-markdown endpoint...")
    
    # Test each file individually
    test_files = os.listdir('test_files')
    content_size_limit = 500000  # 500KB limit for text files
    binary_size_limit = 5000000  # 5MB limit for binary files
    
    for file_name in test_files:
        try:
            # Skip system files
            if file_name.startswith('.'):
                print(f"Skipping system file: {file_name}")
                continue
                
            print(f"\nProcessing {file_name}...")
            file_path = os.path.join('test_files', file_name)
            
            # Determine file type
            file_ext = os.path.splitext(file_name)[1][1:].lower()
            is_binary = file_ext in ['pptx', 'xlsx', 'docx', 'pdf']
            size_limit = binary_size_limit if is_binary else content_size_limit
            
            # Check file size
            if os.path.getsize(file_path) > size_limit:
                print(f"⚠️ File exceeds size limit ({os.path.getsize(file_path)} bytes). Content will be truncated.")
            
            # Read and encode file
            with open(file_path, 'rb') as f:
                content = f.read(size_limit)
                base64_content = base64.b64encode(content).decode('utf-8')
                print(f"✓ Successfully encoded file")
                
                # Prepare request
                file_data = {
                    'name': file_name,
                    'base64': base64_content,
                    'type': file_ext
                }
                
                # Add VLM model for images
                if file_ext.lower() in ['jpg', 'jpeg', 'png', 'gif']:
                    file_data['model'] = 'meta-llama/llama-3.2-11b-vision-instruct:free'
                    print(f"Note: Using vision model {file_data['model']} - requires appropriate API access")
                
                # Make request with retries
                max_retries = 5
                success = False
                
                for retry in range(max_retries):
                    try:
                        response = requests.post(
                            'http://localhost:8001/api/convert-to-markdown',
                            json={'file': file_data},
                            headers={'Authorization': f'Bearer {os.getenv("API_BEARER_TOKEN")}'}
                        )
                        
                        print(f"Status Code: {response.status_code}")
                        
                        if response.status_code == 200:
                            success = True
                            break
                        else:
                            print(f"Attempt {retry + 1} failed. Status: {response.status_code}")
                            if retry < max_retries - 1:
                                delay = min(30, (2 ** retry) * 5)  # Exponential backoff, max 30 seconds
                                print(f"Waiting {delay} seconds before retry...")
                                time.sleep(delay)
                    except Exception as e:
                        print(f"Request failed: {str(e)}")
                        if retry < max_retries - 1:
                            delay = min(30, (2 ** retry) * 5)
                            print(f"Waiting {delay} seconds before retry...")
                            time.sleep(delay)
                
                if success and 'application/json' in response.headers.get('content-type', ''):
                    result = response.json()
                    if result.get('success'):
                        # Save markdown to file
                        name_without_ext = os.path.splitext(file_name)[0]
                        file_type = os.path.splitext(file_name)[1][1:]
                        output_file = os.path.join('markdown_results', f'api_convert_{name_without_ext}_{file_type}.md')
                        
                        with open(output_file, 'w') as f:
                            f.write(result['markdown'])
                        print(f"✓ Successfully converted and saved to: {output_file}")
                        
                        # Show preview
                        preview = result['markdown'][:100] + '...' if len(result['markdown']) > 100 else result['markdown']
                        print(f"\nPreview:\n{preview}")
                    else:
                        print(f"✗ Conversion failed: {result.get('error', 'Unknown error')}")
                else:
                    print("✗ Request failed or invalid response")
                    
        except Exception as e:
            print(f"✗ Failed to process {file_name}: {str(e)}")
            continue
        
        # Add delay between files
        if file_name != test_files[-1]:  # Don't wait after the last file
            time.sleep(5)  # 5 second delay between files

def test_file_agent():
    """Test the /api/file-agent endpoint with query context."""
    print("\nTesting /api/file-agent endpoint with query...")
    
    # Test each file individually
    test_files = os.listdir('test_files')
    content_size_limit = 500000  # 500KB limit for text files
    binary_size_limit = 5000000  # 5MB limit for binary files
    
    # Test query to provide context
    test_query = "Please provide a summary of these files focusing on the main points and key information."
    print(f"\nUsing query: {test_query}")
    
    files_data = []
    for file_name in test_files:
        # Skip system files
        if file_name.startswith('.'):
            print(f"Skipping system file: {file_name}")
            continue
            
        print(f"\nProcessing {file_name}...")
        file_path = os.path.join('test_files', file_name)
        
        # Determine file type
        file_ext = os.path.splitext(file_name)[1][1:].lower()
        is_binary = file_ext in ['pptx', 'xlsx', 'docx', 'pdf']
        size_limit = binary_size_limit if is_binary else content_size_limit
        
        try:
            # Read and encode file
            with open(file_path, 'rb') as f:
                content = f.read(size_limit)
                base64_content = base64.b64encode(content).decode('utf-8')
                print(f"✓ Successfully encoded {file_name}")
                
                # Add file to list
                files_data.append({
                    'name': file_name,
                    'type': file_ext,
                    'base64': base64_content
                })
                
        except Exception as e:
            print(f"✗ Failed to process {file_name}: {str(e)}")
            continue
    
    if files_data:
        try:
            print(f"\nSending request with {len(files_data)} files...")
            
            # Prepare request data
            request_data = {
                'query': test_query,
                'files': files_data,
                'session_id': 'test_session_123',
                'user_id': 'test_user_123',
                'request_id': 'test_request_123'
            }
            
            # Send request
            response = requests.post(
                'http://localhost:8001/api/file-agent',
                json=request_data,
                headers={'Authorization': f'Bearer {os.getenv("API_BEARER_TOKEN")}'}
            )
            
            print(f"\nStatus Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result['success']:
                    # Save markdown to file
                    output_file = os.path.join('markdown_results', 'file_agent_summary.md')
                    
                    with open(output_file, 'w') as f:
                        f.write(result['markdown'])
                    print(f"✓ Successfully saved summary to: {output_file}")
                    
                    # Show preview
                    preview = result['markdown'][:200] + '...' if len(result['markdown']) > 200 else result['markdown']
                    print(f"\nPreview of summary:\n{preview}")
                else:
                    print(f"✗ Processing failed: {result.get('error', 'Unknown error')}")
                    print(f"Full response: {json.dumps(result, indent=2)}")
            else:
                print("✗ Request failed")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"✗ Error making request: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("No files to process")
    
    print("\nTest completed.")

def test_file_agent_cached():
    """Test the /api/file-agent-cached endpoint with caching enabled and disabled."""
    print("\nTesting /api/file-agent-cached endpoint...")
    
    # Test files to process
    test_files = [
        ('test.docx', 'docx'),
        ('test_wikipedia.html', 'html'),
        ('test_serp.html', 'html'),
        ('test.pptx', 'pptx'),
        ('test.pdf', 'pdf'),
        ('test.xlsx', 'xlsx'),
        ('test_blog.html', 'html'),
        ('image.jpg', 'jpg')
    ]
    
    # Generate a unique session ID for this test
    session_id = f"test_session_{int(time.time())}"
    user_id = "test_user"
    request_id = f"test_request_{int(time.time())}"
    
    # Test with caching enabled (default)
    print("\nTest 1: With caching enabled...")
    files_data = []
    for file_name, file_type in test_files:
        try:
            # Read and encode file
            file_path = os.path.join('test_files', file_name)
            with open(file_path, 'rb') as f:
                content = f.read()
                base64_content = base64.b64encode(content).decode('utf-8')
                
                file_data = {
                    'name': file_name,
                    'type': file_type,
                    'base64': base64_content
                }
                
                # Add model for images
                if file_type.lower() in ['jpg', 'jpeg', 'png', 'gif']:
                    file_data['model'] = os.getenv("OPENROUTER_VLM_MODEL")
                
                files_data.append(file_data)
                print(f"✓ Successfully encoded {file_name}")
                
        except Exception as e:
            print(f"✗ Error encoding {file_name}: {str(e)}")
    
    # First request (should cache the results)
    try:
        response = requests.post(
            'http://localhost:8001/api/file-agent-cached',
            json={
                'query': 'What are the main topics discussed in these documents?',
                'files': files_data,
                'session_id': session_id,
                'user_id': user_id,
                'request_id': request_id,
                'use_cache': True
            },
            headers={'Authorization': f'Bearer {os.getenv("API_BEARER_TOKEN")}'}
        )
        
        print(f"\nFirst request (with caching):")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Success: {result['success']}")
            print(f"Response length: {len(result['markdown'])} characters")
            print(f"First 100 characters: {result['markdown'][:100]}...")
        else:
            print(f"✗ Error: {response.text}")
            
        # Second request with same files (should use cache)
        print("\nTest 2: Second request (should use cache)...")
        start_time = time.time()
        response = requests.post(
            'http://localhost:8001/api/file-agent-cached',
            json={
                'query': 'Give me a different perspective on these documents.',
                'files': files_data,
                'session_id': session_id,
                'user_id': user_id,
                'request_id': request_id,
                'use_cache': True
            },
            headers={'Authorization': f'Bearer {os.getenv("API_BEARER_TOKEN")}'}
        )
        cached_time = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Success: {result['success']}")
            print(f"Response time: {cached_time:.2f} seconds")
            print(f"Response length: {len(result['markdown'])} characters")
            print(f"First 100 characters: {result['markdown'][:100]}...")
        else:
            print(f"✗ Error: {response.text}")
        
        # Test with caching disabled
        print("\nTest 3: With caching disabled...")
        start_time = time.time()
        response = requests.post(
            'http://localhost:8001/api/file-agent-cached',
            json={
                'query': 'Summarize these documents.',
                'files': files_data,
                'session_id': session_id,
                'user_id': user_id,
                'request_id': request_id,
                'use_cache': False
            },
            headers={'Authorization': f'Bearer {os.getenv("API_BEARER_TOKEN")}'}
        )
        uncached_time = time.time() - start_time
        
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Success: {result['success']}")
            print(f"Response time: {uncached_time:.2f} seconds")
            print(f"Response length: {len(result['markdown'])} characters")
            print(f"First 100 characters: {result['markdown'][:100]}...")
        else:
            print(f"✗ Error: {response.text}")
        
        # Test error cases
        print("\nTest 4: Error cases...")
        
        # Test invalid token
        response = requests.post(
            'http://localhost:8001/api/file-agent-cached',
            json={
                'query': 'This should fail.',
                'files': files_data,
                'session_id': session_id,
                'user_id': user_id,
                'request_id': request_id
            },
            headers={'Authorization': 'Bearer invalid_token'}
        )
        print(f"\nInvalid token test:")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("✓ Successfully rejected invalid token")
        else:
            print(f"✗ Unexpected response: {response.text}")
        
        # Test missing files
        response = requests.post(
            'http://localhost:8001/api/file-agent-cached',
            json={
                'query': 'This should fail.',
                'session_id': session_id,
                'user_id': user_id,
                'request_id': request_id
            },
            headers={'Authorization': f'Bearer {os.getenv("API_BEARER_TOKEN")}'}
        )
        print(f"\nMissing files test:")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 422:
            print("✓ Successfully handled missing files with 422 error")
        else:
            print(f"✗ Expected status code 422 but got {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error during test: {str(e)}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    print("\nStarting tests...")
    
    # Load environment variables
    load_dotenv(find_dotenv())
    print(f"\nLoading .env file from: {find_dotenv()}")
    
    print("\nEnvironment variables loaded:")
    print(f"OPENROUTER_API_KEY = {os.getenv('OPENROUTER_API_KEY')}")
    print(f"OPENROUTER_MODEL = {os.getenv('OPENROUTER_MODEL')}\n")
    
    # Run tests
    test_openrouter_api()
    test_file_processing()
    test_file_processing_with_llm()
    test_image_processing_with_llm()
    test_api_file_agent_cached()
    test_convert_to_markdown()
    test_file_agent()
    test_file_agent_cached()
    
    print("\nCleaning up...")
    print("Done!")
