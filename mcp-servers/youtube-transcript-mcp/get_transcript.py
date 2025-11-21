#!/usr/bin/env python3
"""
Standalone YouTube Transcript Extractor
Run this directly to get transcripts without MCP
"""

import sys
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import RobustYouTubeTranscriptServer

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 get_transcript.py <youtube_url>")
        print("Example: python3 get_transcript.py https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        sys.exit(1)
    
    url = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else "en"
    
    print(f"Fetching transcript for: {url}")
    print(f"Language: {lang}")
    print("-" * 60)
    
    server = RobustYouTubeTranscriptServer()
    result = server.get_transcript({
        'url': url,
        'lang': lang
    })
    
    if result.get('success'):
        print(f"✓ SUCCESS!")
        print(f"Method used: {result.get('method')}")
        print(f"Transcript length: {result.get('length')} characters")
        print("-" * 60)
        
        # Save to file
        video_id = server.extract_video_id(url)
        output_file = f"transcript_{video_id}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result.get('transcript', ''))
        
        print(f"Full transcript saved to: {output_file}")
        print("-" * 60)
        print("Preview (first 1000 characters):")
        print(result.get('transcript', '')[:1000])
        
    else:
        print(f"✗ FAILED to get transcript")
        print(f"Error: {result.get('error')}")
        if result.get('details'):
            print("\nDetailed errors:")
            for detail in result.get('details', []):
                print(f"  - {detail}")
        
        print("\n" + "="*60)
        print("TROUBLESHOOTING:")
        print("1. YouTube may be rate-limiting your IP")
        print("2. Try waiting 15-30 minutes")
        print("3. Use a VPN to get a different IP")
        print("4. Try a different video")
        print("5. Save YouTube cookies to ~/.youtube-cookies.txt")

if __name__ == "__main__":
    main()