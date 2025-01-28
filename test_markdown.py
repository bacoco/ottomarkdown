#!/usr/bin/env python3
import os
import base64
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class APITester:
    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.api_token = os.getenv("API_BEARER_TOKEN")
        if not self.api_token:
            raise ValueError("API_BEARER_TOKEN not set in environment")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        # Setup directories
        self.test_dir = Path("test_files")
        self.output_dir = Path("markdown_results")
        self.output_dir.mkdir(exist_ok=True)
        
        # Test results
        self.results = {
            "markdown_conversion": [],
            "ai_processing": [],
            "cached_processing": []
        }

    def encode_file(self, file_path: Path) -> Dict[str, str]:
        """Encode a file to base64 and return file info"""
        with open(file_path, 'rb') as f:
            content = base64.b64encode(f.read()).decode()
        
        return {
            "name": file_path.name,
            "type": self._get_mime_type(file_path),
            "base64": content
        }

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type based on file extension"""
        ext_map = {
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.html': 'text/html',
            '.txt': 'text/plain',
            '.jpg': 'image/jpeg',
            '.png': 'image/png'
        }
        return ext_map.get(file_path.suffix.lower(), 'application/octet-stream')

    def save_markdown(self, content: str, original_file: Path, suffix: str = "") -> Path:
        """Save markdown content to file"""
        base_name = original_file.stem
        output_file = self.output_dir / f"{base_name}{suffix}.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return output_file

    def test_markdown_conversion(self, file_path: Path) -> Dict[str, Any]:
        """Test direct markdown conversion"""
        try:
            file_data = self.encode_file(file_path)
            response = requests.post(
                f"{self.base_url}/api/convert-to-markdown",
                headers=self.headers,
                json={"file": file_data}
            )
            
            result = {
                "file": str(file_path),
                "status_code": response.status_code,
                "success": False,
                "error": None
            }
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    output_file = self.save_markdown(data["markdown"], file_path)
                    result.update({
                        "success": True,
                        "output_file": str(output_file)
                    })
                else:
                    result["error"] = data.get("error", "Unknown error")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text}"
            
            return result
        except Exception as e:
            return {
                "file": str(file_path),
                "status_code": None,
                "success": False,
                "error": str(e)
            }

    def test_ai_processing(self, file_path: Path, query: str) -> Dict[str, Any]:
        """Test AI processing without caching"""
        try:
            file_data = self.encode_file(file_path)
            payload = {
                "query": query,
                "files": [file_data],
                "session_id": f"test_{datetime.now().timestamp()}",
                "user_id": "test_user",
                "request_id": f"req_{datetime.now().timestamp()}"
            }
            
            response = requests.post(
                f"{self.base_url}/api/file-agent",
                headers=self.headers,
                json=payload
            )
            
            result = {
                "file": str(file_path),
                "query": query,
                "status_code": response.status_code,
                "success": False,
                "error": None
            }
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    output_file = self.save_markdown(
                        data["markdown"],
                        file_path,
                        "_ai_response"
                    )
                    result.update({
                        "success": True,
                        "output_file": str(output_file)
                    })
                else:
                    result["error"] = data.get("error", "Unknown error")
            else:
                result["error"] = f"HTTP {response.status_code}: {response.text}"
            
            return result
        except Exception as e:
            return {
                "file": str(file_path),
                "query": query,
                "status_code": None,
                "success": False,
                "error": str(e)
            }

    def test_cached_processing(self, file_path: Path, query: str) -> Dict[str, Any]:
        """Test AI processing with caching"""
        try:
            file_data = self.encode_file(file_path)
            session_id = f"test_{datetime.now().timestamp()}"
            user_id = "test_user"
            request_id = f"req_{datetime.now().timestamp()}"
            
            # First request to populate cache
            response1 = requests.post(
                f"{self.base_url}/api/file-agent-cached",
                headers=self.headers,
                params={
                    "query": query,
                    "session_id": session_id,
                    "user_id": user_id,
                    "request_id": request_id
                },
                json=[file_data]
            )
            
            # Second request to test cache (using same parameters)
            response2 = requests.post(
                f"{self.base_url}/api/file-agent-cached",
                headers=self.headers,
                params={
                    "query": query,
                    "session_id": session_id,
                    "user_id": user_id,
                    "request_id": request_id
                },
                json=[file_data]
            )
            
            result = {
                "file": str(file_path),
                "query": query,
                "first_request": {
                    "status_code": response1.status_code,
                    "success": False,
                    "error": None
                },
                "cached_request": {
                    "status_code": response2.status_code,
                    "success": False,
                    "error": None
                }
            }
            
            # Process first request
            if response1.status_code == 200:
                data = response1.json()
                if data.get("success"):
                    output_file = self.save_markdown(
                        data["markdown"],
                        file_path,
                        "_cached_first"
                    )
                    result["first_request"].update({
                        "success": True,
                        "output_file": str(output_file)
                    })
                else:
                    result["first_request"]["error"] = data.get("error", "Unknown error")
            else:
                result["first_request"]["error"] = f"HTTP {response1.status_code}: {response1.text}"
            
            # Process second (cached) request
            if response2.status_code == 200:
                data = response2.json()
                if data.get("success"):
                    output_file = self.save_markdown(
                        data["markdown"],
                        file_path,
                        "_cached_second"
                    )
                    result["cached_request"].update({
                        "success": True,
                        "output_file": str(output_file)
                    })
                else:
                    result["cached_request"]["error"] = data.get("error", "Unknown error")
            else:
                result["cached_request"]["error"] = f"HTTP {response2.status_code}: {response2.text}"
            
            return result
        except Exception as e:
            return {
                "file": str(file_path),
                "query": query,
                "first_request": {"success": False, "error": str(e)},
                "cached_request": {"success": False, "error": str(e)}
            }

    def run_tests(self):
        """Run all tests"""
        logger.info("Starting API tests...")
        
        test_files = list(self.test_dir.glob('*'))
        if not test_files:
            logger.error(f"No test files found in {self.test_dir}")
            return
        
        # Test queries for AI processing
        queries = [
            "Summarize the main points of this document",
            "What are the key findings in this document?",
            "Extract the most important information"
        ]
        
        # Run tests for each file
        for file_path in test_files:
            logger.info(f"\nProcessing: {file_path.name}")
            
            # Test markdown conversion
            result = self.test_markdown_conversion(file_path)
            self.results["markdown_conversion"].append(result)
            logger.info(f" Markdown conversion: {'Success' if result['success'] else 'Failed'}")
            
            # Test AI processing
            query = queries[0]  # Use first query for consistency
            result = self.test_ai_processing(file_path, query)
            self.results["ai_processing"].append(result)
            logger.info(f" AI processing: {'Success' if result['success'] else 'Failed'}")
            
            # Test cached processing
            result = self.test_cached_processing(file_path, query)
            self.results["cached_processing"].append(result)
            logger.info(f" Cached processing: "
                      f"First: {'Success' if result['first_request']['success'] else 'Failed'}, "
                      f"Second: {'Success' if result['cached_request']['success'] else 'Failed'}")
        
        # Save test results
        self.save_test_results()

    def save_test_results(self):
        """Save test results to JSON and markdown files"""
        # Save detailed JSON results
        with open(self.output_dir / 'test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Create markdown summary
        summary = ["# API Test Results\n"]
        
        # Markdown conversion results
        summary.append("\n## Markdown Conversion Results")
        for result in self.results["markdown_conversion"]:
            summary.append(f"\n### {Path(result['file']).name}")
            summary.append(f"- Status: {'Success' if result['success'] else 'Failed'}")
            if result['error']:
                summary.append(f"- Error: {result['error']}")
            if result.get('output_file'):
                summary.append(f"- Output: {Path(result['output_file']).name}")
        
        # AI processing results
        summary.append("\n## AI Processing Results")
        for result in self.results["ai_processing"]:
            summary.append(f"\n### {Path(result['file']).name}")
            summary.append(f"- Query: {result['query']}")
            summary.append(f"- Status: {'Success' if result['success'] else 'Failed'}")
            if result['error']:
                summary.append(f"- Error: {result['error']}")
            if result.get('output_file'):
                summary.append(f"- Output: {Path(result['output_file']).name}")
        
        # Cached processing results
        summary.append("\n## Cached Processing Results")
        for result in self.results["cached_processing"]:
            summary.append(f"\n### {Path(result['file']).name}")
            summary.append(f"- Query: {result['query']}")
            summary.append("- First Request:")
            summary.append(f"  - Status: {'Success' if result['first_request']['success'] else 'Failed'}")
            if result['first_request'].get('error'):
                summary.append(f"  - Error: {result['first_request']['error']}")
            summary.append("- Cached Request:")
            summary.append(f"  - Status: {'Success' if result['cached_request']['success'] else 'Failed'}")
            if result['cached_request'].get('error'):
                summary.append(f"  - Error: {result['cached_request']['error']}")
        
        # Save markdown summary
        with open(self.output_dir / 'test_summary.md', 'w') as f:
            f.write('\n'.join(summary))

def main():
    try:
        tester = APITester()
        tester.run_tests()
        logger.info("\nTests completed. Check markdown_results/ for output files and test summary.")
    except Exception as e:
        logger.error(f"Error running tests: {e}")

if __name__ == "__main__":
    main()
