#!/usr/bin/env python3
"""Test the bulletproof YouTube transcript server implementation"""

import json
import subprocess
import sys
from pathlib import Path

def test_bulletproof_server():
    """Test the bulletproof server with multiple videos"""
    print("Testing Bulletproof YouTube transcript server...")
    
    # Test videos - known to have transcripts
    test_videos = [
        "https://www.youtube.com/watch?v=fLJBzhcSWTk",  # TED talk
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll (has captions)
    ]
    
    server_path = Path("/Users/marc/Documents/Cline/MCP/youtube-transcript-mcp/server_bulletproof.py")
    
    if not server_path.exists():
        print(f"Server file not found: {server_path}")
        return
    
    for i, test_video in enumerate(test_videos):
        print(f"\n=== Testing video {i+1}: {test_video} ===")
        
        # Create test requests
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
        
        transcript_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_transcript",
                "arguments": {
                    "url": test_video,
                    "lang": "en"
                }
            }
        }
        
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
                json.dumps(transcript_request)
            ]
            
            input_text = "\n".join(inputs) + "\n"
            
            # Get responses
            stdout, stderr = process.communicate(input=input_text, timeout=90)
            
            print("STDERR (logs):")
            print(stderr[-1000:] if len(stderr) > 1000 else stderr)  # Last 1000 chars
            
            # Parse the transcript response
            responses = stdout.strip().split('\n')
            if len(responses) >= 2:
                try:
                    transcript_response = json.loads(responses[1])
                    content = transcript_response.get('result', {}).get('content', [])
                    if content:
                        transcript_data = json.loads(content[0].get('text', '{}'))
                        
                        print(f"\nResult for {test_video}:")
                        print(f"Success: {transcript_data.get('success')}")
                        print(f"Method: {transcript_data.get('method')}")
                        print(f"Length: {transcript_data.get('length', 0)}")
                        
                        transcript_text = transcript_data.get('transcript', '')
                        if transcript_text:
                            print(f"Preview: {transcript_text[:200]}{'...' if len(transcript_text) > 200 else ''}")
                        else:
                            print("Error: No transcript content!")
                            print(f"Error: {transcript_data.get('error')}")
                        
                except json.JSONDecodeError as e:
                    print(f"Failed to parse response: {e}")
                    print(f"Raw response: {responses[1] if len(responses) > 1 else 'No response'}")
            else:
                print("No transcript response received")
                print(f"All responses: {responses}")
            
        except subprocess.TimeoutExpired:
            print(f"Server test timed out for video: {test_video}")
            process.kill()
        except Exception as e:
            print(f"Error testing video {test_video}: {e}")

if __name__ == "__main__":
    test_bulletproof_server()
