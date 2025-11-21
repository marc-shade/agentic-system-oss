#!/usr/bin/env python3
"""
Direct transcript fetcher for YouTube videos
"""

import sys
import json
from server import BulletproofYouTubeTranscriptServer

def fetch_transcript(url):
    """Fetch transcript directly using the server implementation"""
    server = BulletproofYouTubeTranscriptServer()
    
    # Extract video ID from URL
    video_id = None
    if 'youtube.com/watch?v=' in url:
        video_id = url.split('v=')[1].split('&')[0]
    elif 'youtu.be/' in url:
        video_id = url.split('youtu.be/')[1].split('?')[0]
    
    if not video_id:
        return {"error": "Could not extract video ID from URL"}
    
    # Get transcript
    result = server.get_transcript(url, "en", True)
    
    # Pretty print result
    if result.get("success"):
        print(f"✅ Success! Transcript retrieved")
        print(f"📊 Length: {result.get('length', 0)} characters")
        print(f"🔧 Method: {result.get('method', 'unknown')}")
        print(f"🌐 Language: {result.get('language', 'en')}")
        print("\n" + "="*60)
        print("TRANSCRIPT:")
        print("="*60 + "\n")
        print(result.get("transcript", ""))
    else:
        print(f"❌ Failed to get transcript")
        print(f"Error: {result.get('error', 'Unknown error')}")
    
    return result

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=1_twhMU9AxM"
    fetch_transcript(url)