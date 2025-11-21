#!/usr/bin/env python3
"""
Test script for YouTube Transcript MCP integration
"""

import sys
import os
sys.path.insert(0, '.')

from server import get_transcript, get_transcript_languages

def test_youtube_transcript():
    """Test YouTube transcript extraction with the original video URL"""
    test_url = "https://www.youtube.com/watch?v=8r6LPAOlowM"
    
    print("🎬 Testing YouTube Transcript MCP Integration")
    print(f"📹 Video URL: {test_url}")
    print("=" * 60)
    
    # Test transcript retrieval
    print("📝 Testing transcript retrieval...")
    result = get_transcript(test_url, lang="en")
    
    if result["success"]:
        print("✅ SUCCESS: Transcript retrieved successfully!")
        print(f"📊 Video ID: {result['video_id']}")
        print(f"🌍 Language: {result['language']}")
        print(f"📏 Character count: {result['character_count']}")
        print(f"🔧 Method: {result['method']}")
        print("📄 First 200 characters of transcript:")
        print("-" * 40)
        print(result['transcript'][:200] + "...")
        print("-" * 40)
    else:
        print("❌ FAILED: Could not retrieve transcript")
        print(f"🚫 Error: {result['error']}")
        return False
    
    # Test language detection
    print("\n🌐 Testing language detection...")
    lang_result = get_transcript_languages(test_url)
    
    if lang_result["success"]:
        print("✅ SUCCESS: Languages detected!")
        print(f"🎯 Available languages: {len(lang_result['languages'])}")
        for lang in lang_result['languages'][:3]:  # Show first 3 languages
            print(f"   • {lang['language']} ({lang['language_code']}) - Generated: {lang['is_generated']}")
    else:
        print("❌ FAILED: Could not detect languages")
        print(f"🚫 Error: {lang_result['error']}")
    
    print("\n🎉 YouTube Transcript MCP integration test completed!")
    return True

if __name__ == "__main__":
    test_youtube_transcript()