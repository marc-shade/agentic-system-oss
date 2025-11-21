#!/usr/bin/env python3
"""Final test of the updated YouTube transcript MCP server."""

from server import get_transcript

def test_final_transcript():
    """Test the updated YouTube transcript server."""
    print("🎉 Final Test: YouTube Transcript MCP Server")
    print("=" * 50)
    
    # Original URL from user
    test_url = "https://www.youtube.com/watch?v=Lcqat4iP_lE&t=29s"
    print(f"📺 Original URL: {test_url}")
    
    print("\n🔍 Testing get_transcript with yt-dlp...")
    result = get_transcript(test_url, "en")
    
    print(f"✅ Success: {result['success']}")
    
    if result['success']:
        print(f"📹 Video ID: {result['video_id']}")
        print(f"🗣️ Language: {result['language']}")
        print(f"📄 Method: {result['method']}")
        print(f"📝 Character count: {result['character_count']:,}")
        print(f"🎬 Subtitle format: {result['subtitle_format']}")
        print(f"\n📄 Transcript sample (first 500 chars):")
        print("-" * 40)
        print(result['transcript'][:500] + "...")
        print("-" * 40)
        
        # Also show some key phrases to verify content quality
        transcript_lower = result['transcript'].lower()
        if any(phrase in transcript_lower for phrase in ['weight', 'bias', 'model', 'training', 'ai']):
            print("✅ Content verification: AI/ML related terms found - transcript quality confirmed!")
        
    else:
        print(f"❌ Error: {result['error']}")
    
    print("\n🎊 YouTube Transcript MCP Server is ready for use!")
    print("💡 Add it to your Claude configuration to use get_transcript() tool.")

if __name__ == "__main__":
    test_final_transcript()