#!/usr/bin/env python3
"""Test the robust server methods directly"""

import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from robust_server import RobustYouTubeTranscriptServer

def test_innertube_method():
    """Test the InnerTube API method specifically"""
    server = RobustYouTubeTranscriptServer()
    video_id = "HPYq-VUoBkE"
    
    print(f"Testing InnerTube API method for video: {video_id}")
    result = server.method_3_innertube_api(video_id, "en")
    
    if result.get("success"):
        print(f"✓ Success with InnerTube API!")
        print(f"  Transcript length: {result.get('length', 0)} chars")
        print(f"  First 300 chars: {result.get('transcript', '')[:300]}...")
    else:
        print(f"✗ Failed: {result.get('error')}")
    
    return result

def test_direct_api_method():
    """Test the direct API method"""
    server = RobustYouTubeTranscriptServer()
    video_id = "HPYq-VUoBkE"
    
    print(f"\nTesting Direct API method for video: {video_id}")
    result = server.method_1_direct_api(video_id, "en")
    
    if result.get("success"):
        print(f"✓ Success with Direct API!")
        print(f"  Transcript length: {result.get('length', 0)} chars")
        print(f"  First 300 chars: {result.get('transcript', '')[:300]}...")
    else:
        print(f"✗ Failed: {result.get('error')}")
    
    return result

def test_full_server():
    """Test the full server with all methods"""
    server = RobustYouTubeTranscriptServer()
    
    print("\n" + "="*60)
    print("Testing full server with all fallback methods")
    print("="*60)
    
    result = server.get_transcript({
        "url": "https://www.youtube.com/watch?v=HPYq-VUoBkE",
        "lang": "en"
    })
    
    print("\nFinal Result:")
    print(json.dumps(result, indent=2))
    
    if result.get("success"):
        print(f"\n✓ SUCCESS! Method used: {result.get('method')}")
        print(f"Transcript preview: {result.get('transcript', '')[:500]}...")
    else:
        print(f"\n✗ All methods failed")
        if result.get("details"):
            print("\nError details:")
            for error in result.get("details", []):
                print(f"  - {error}")

if __name__ == "__main__":
    # Test individual methods first
    test_innertube_method()
    test_direct_api_method()
    
    # Then test the full server
    test_full_server()