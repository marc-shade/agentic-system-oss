#!/usr/bin/env python3
"""Test the YouTube Transcript API directly"""

from youtube_transcript_api import YouTubeTranscriptApi
import sys

def test_transcript(video_id="HPYq-VUoBkE"):
    """Test getting transcript for a video"""
    print(f"Testing video ID: {video_id}")
    
    try:
        # This is the correct way to call it
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        if transcript:
            print(f"Success! Got {len(transcript)} segments")
            # Show first 3 segments as sample
            for i, segment in enumerate(transcript[:3]):
                print(f"Segment {i}: {segment}")
            
            # Get full text
            full_text = " ".join([s['text'] for s in transcript])
            print(f"\nTotal transcript length: {len(full_text)} characters")
            print(f"First 500 chars: {full_text[:500]}...")
            return True
        else:
            print("No transcript returned")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        print(f"Error type: {type(e)}")
        return False

if __name__ == "__main__":
    video_id = sys.argv[1] if len(sys.argv) > 1 else "HPYq-VUoBkE"
    success = test_transcript(video_id)
    sys.exit(0 if success else 1)