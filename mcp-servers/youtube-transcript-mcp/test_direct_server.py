#!/usr/bin/env python3
"""Test the server directly without MCP protocol"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import YouTubeTranscriptServer

def test_server():
    server = YouTubeTranscriptServer()
    
    # Test with the video
    result = server.get_transcript({
        "url": "https://www.youtube.com/watch?v=HPYq-VUoBkE",
        "lang": "en"
    })
    
    print("Result:", result)
    
    if result.get("success"):
        print(f"\nSuccess! Method used: {result.get('method')}")
        print(f"Transcript length: {result.get('length', len(result.get('transcript', '')))}")
        print(f"First 500 chars: {result.get('transcript', '')[:500]}...")
    else:
        print(f"\nFailed: {result.get('error')}")

if __name__ == "__main__":
    test_server()