#!/usr/bin/env python3
"""Test pytube directly"""

from pytube import YouTube
import sys

def test_pytube(video_id="HPYq-VUoBkE"):
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"Testing pytube with video: {video_id}")
        print(f"URL: {url}")
        
        yt = YouTube(url)
        print(f"Video title: {yt.title}")
        
        # Check available captions
        print(f"Available captions: {list(yt.captions.keys())}")
        
        if yt.captions:
            # Get English caption or first available
            if 'en' in yt.captions:
                caption = yt.captions['en']
                print("Using English captions")
            else:
                caption = list(yt.captions.values())[0]
                print(f"Using captions in: {caption.code}")
            
            # Get the transcript
            transcript = caption.generate_srt_captions()
            
            # Show first 500 chars
            print(f"\nTranscript length: {len(transcript)} chars")
            print(f"First 500 chars:\n{transcript[:500]}")
            
            return True
        else:
            print("No captions available")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    video_id = sys.argv[1] if len(sys.argv) > 1 else "HPYq-VUoBkE"
    test_pytube(video_id)