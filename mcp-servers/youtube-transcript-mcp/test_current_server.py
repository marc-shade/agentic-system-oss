#!/usr/bin/env python3
"""Test the current YouTube transcript server implementation"""

import json
import subprocess
import sys
from pathlib import Path

def test_server_directly():
    """Test the server by running it directly"""
    print("Testing YouTube transcript server...")
    
    # Test with a known working video (TED talk with captions)
    test_video = "https://www.youtube.com/watch?v=fLJBzhcSWTk"  # Popular TED talk
    
    server_path = Path("/Users/marc/Documents/Cline/MCP/youtube-transcript-mcp/server.py")
    
    if not server_path.exists():
        print(f"Server file not found: {server_path}")
        return
    
    # Create test request
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        }
    }
    
    tools_list_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }
    
    transcript_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "get_transcript",
            "arguments": {
                "url": test_video,
                "lang": "en"
            }
        }
    }
    
    # Test the server
    try:
        # Run server process
        process = subprocess.Popen(
            [sys.executable, str(server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send requests
        inputs = [
            json.dumps(initialize_request),
            json.dumps(tools_list_request),
            json.dumps(transcript_request)
        ]
        
        input_text = "\n".join(inputs) + "\n"
        
        # Get responses
        stdout, stderr = process.communicate(input=input_text, timeout=60)
        
        print("STDERR (logs):")
        print(stderr)
        print("\nSTDOUT (responses):")
        print(stdout)
        
        # Parse responses
        for line in stdout.strip().split('\n'):
            if line.strip():
                try:
                    response = json.loads(line)
                    print(f"Response: {json.dumps(response, indent=2)}")
                except json.JSONDecodeError:
                    print(f"Invalid JSON: {line}")
        
    except subprocess.TimeoutExpired:
        print("Server test timed out")
        process.kill()
    except Exception as e:
        print(f"Error testing server: {e}")

if __name__ == "__main__":
    test_server_directly()