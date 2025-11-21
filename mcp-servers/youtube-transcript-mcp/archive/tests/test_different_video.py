#!/usr/bin/env python3
"""Test with different YouTube videos to identify the issue."""

from server import get_transcript, get_transcript_languages

def test_videos():
    """Test with different YouTube videos."""
    test_videos = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll (very popular)
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo (first YouTube video)
        "https://www.youtube.com/watch?v=Lcqat4iP_lE",  # Original video
    ]
    
    for i, url in enumerate(test_videos, 1):
        print(f"\n🧪 Testing video {i}: {url}")
        print("-" * 40)
        
        # Test languages first
        lang_result = get_transcript_languages(url)
        if lang_result['success']:
            print(f"✅ Languages available: {len(lang_result['languages'])}")
            for lang in lang_result['languages'][:2]:
                print(f"   - {lang['language']} ({lang['language_code']})")
        else:
            print(f"❌ Language check failed: {lang_result['error']}")
            continue
        
        # Test transcript
        transcript_result = get_transcript(url, "en")
        if transcript_result['success']:
            print(f"✅ Transcript retrieved: {len(transcript_result['transcript'])} chars")
            print(f"📄 Preview: {transcript_result['transcript'][:100]}...")
        else:
            print(f"❌ Transcript failed: {transcript_result['error']}")

if __name__ == "__main__":
    test_videos()