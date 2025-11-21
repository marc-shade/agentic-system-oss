#!/usr/bin/env python3
"""Test YouTube transcript MCP functionality"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from extract_transcript import get_transcript

def test_youtube_transcript():
    """Test with a known public video"""
    test_url = "https://www.youtube.com/watch?v=PAPq2UypkFk"
    
    print(f"Testing YouTube transcript extraction...")
    print(f"URL: {test_url}")
    print("-" * 50)
    
    try:
        result = get_transcript(test_url)
        if result and len(result) > 0:
            print(f"✅ SUCCESS! Transcript extracted:")
            print(f"   Length: {len(result)} characters")
            print(f"   First 200 chars: {result[:200]}...")
            return True
        else:
            print("❌ FAILED: No transcript returned")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_youtube_transcript()
    sys.exit(0 if success else 1)