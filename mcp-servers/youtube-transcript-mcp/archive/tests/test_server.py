#!/usr/bin/env python3
"""Test the YouTube transcript MCP server."""

import asyncio
import json
from server import get_transcript, get_transcript_languages

async def test_youtube_transcript():
    """Test YouTube transcript functionality."""
    print("🧪 Testing YouTube Transcript MCP Server")
    print("=" * 50)
    
    # Test URL
    test_url = "https://www.youtube.com/watch?v=Lcqat4iP_lE&t=29s"
    print(f"📺 Testing with URL: {test_url}")
    
    # Test get_transcript
    print("\n🔍 Testing get_transcript...")
    try:
        result = get_transcript(test_url, "en")
        print(f"✅ Success: {result['success']}")
        
        if result['success']:
            print(f"📹 Video ID: {result['video_id']}")
            print(f"🗣️ Language: {result['language']}")
            print(f"⏱️ Duration: {result['duration_seconds']} seconds")
            print(f"📝 Segments: {result['total_segments']}")
            print(f"📄 Transcript preview: {result['transcript'][:200]}...")
        else:
            print(f"❌ Error: {result['error']}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test get_transcript_languages
    print("\n🌍 Testing get_transcript_languages...")
    try:
        result = get_transcript_languages(test_url)
        print(f"✅ Success: {result['success']}")
        
        if result['success']:
            print(f"📹 Video ID: {result['video_id']}")
            print(f"🗣️ Available languages: {len(result['languages'])}")
            for lang in result['languages'][:3]:  # Show first 3
                print(f"   - {lang['language']} ({lang['language_code']}) - Generated: {lang['is_generated']}")
        else:
            print(f"❌ Error: {result['error']}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    print("\n✅ YouTube Transcript MCP Server test complete!")

if __name__ == "__main__":
    asyncio.run(test_youtube_transcript())