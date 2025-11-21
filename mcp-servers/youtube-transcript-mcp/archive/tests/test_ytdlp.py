#!/usr/bin/env python3
"""Test the yt-dlp alternative YouTube transcript approach."""

from alternative_server import get_transcript_ytdlp

def test_ytdlp_transcript():
    """Test yt-dlp transcript extraction."""
    print("🧪 Testing yt-dlp YouTube Transcript Extraction")
    print("=" * 50)
    
    test_url = "https://www.youtube.com/watch?v=Lcqat4iP_lE&t=29s"
    print(f"📺 Testing with URL: {test_url}")
    
    print("\n🔍 Testing get_transcript_ytdlp...")
    result = get_transcript_ytdlp(test_url, "en")
    
    print(f"✅ Success: {result['success']}")
    
    if result['success']:
        print(f"📹 Video ID: {result['video_id']}")
        print(f"🗣️ Language: {result['language']}")
        print(f"📄 Subtitle format: {result['subtitle_format']}")
        print(f"📝 Transcript length: {len(result['transcript'])} characters")
        print(f"📄 Transcript preview: {result['transcript'][:300]}...")
        print(f"🔧 Raw content preview: {result['raw_content'][:200]}...")
    else:
        print(f"❌ Error: {result['error']}")
    
    print("\n✅ yt-dlp test complete!")

if __name__ == "__main__":
    test_ytdlp_transcript()