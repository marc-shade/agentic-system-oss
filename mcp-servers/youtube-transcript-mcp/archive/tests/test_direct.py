#!/usr/bin/env python3
"""Direct test of YouTube transcript extraction."""

from server import get_transcript, get_transcript_languages

def test_direct():
    """Test the transcript extraction directly."""
    # Test with the video URL you provided
    test_url = "https://youtu.be/fD8NLPU0WYU"
    
    print("🎥 Testing YouTube Transcript Extraction")
    print("=" * 50)
    print(f"📺 Video URL: {test_url}")
    print(f"📌 Title: Agile Coding Is HERE… 90% AI Coding Is Already Done With This")
    
    # Test transcript extraction
    print("\n🔍 Extracting transcript...")
    result = get_transcript(test_url, "en")
    
    if result['success']:
        print(f"✅ Success!")
        print(f"📹 Video ID: {result['video_id']}")
        print(f"🗣️ Language: {result['language']}")
        print(f"📊 Character count: {result['character_count']}")
        print(f"📝 Word count: {result['word_count']}")
        print(f"🔧 Method: {result['method']}")
        print(f"\n📄 Transcript preview (first 500 chars):")
        print("-" * 50)
        print(result['transcript'][:500] + "...")
        
        # Save full transcript
        with open('agile_ai_coding_transcript.txt', 'w') as f:
            f.write(result['transcript'])
        print("\n✅ Full transcript saved to: agile_ai_coding_transcript.txt")
    else:
        print(f"❌ Error: {result['error']}")
        print("🔧 Troubleshooting suggestions:")
        print("  1. Check if yt-dlp is installed: pip install yt-dlp")
        print("  2. Make sure the video has captions/subtitles")
        print("  3. Try updating yt-dlp: pip install --upgrade yt-dlp")

if __name__ == "__main__":
    test_direct()