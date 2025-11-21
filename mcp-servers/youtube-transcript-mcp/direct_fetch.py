#!/usr/bin/env python3
"""
Direct YouTube transcript fetcher using multiple methods
"""

import sys
import subprocess
import json

def fetch_with_ytdlp(video_id):
    """Try fetching with yt-dlp"""
    try:
        # Try to get subtitles with yt-dlp
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-auto-subs',
            '--sub-langs', 'en',
            '--sub-format', 'vtt',
            '--print', '%(subtitles)s',
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Now get the actual subtitle file
            subtitle_cmd = [
                'yt-dlp',
                '--skip-download',
                '--write-auto-subs',
                '--sub-langs', 'en',
                '--sub-format', 'vtt',
                '-o', '/tmp/%(id)s.%(ext)s',
                f'https://www.youtube.com/watch?v={video_id}'
            ]
            
            subprocess.run(subtitle_cmd, capture_output=True, timeout=30)
            
            # Read the subtitle file
            import os
            vtt_file = f'/tmp/{video_id}.en.vtt'
            if os.path.exists(vtt_file):
                with open(vtt_file, 'r') as f:
                    content = f.read()
                
                # Clean up VTT content
                lines = []
                for line in content.split('\n'):
                    # Skip WEBVTT header, timestamps, and empty lines
                    if line.strip() and not line.startswith('WEBVTT') and '-->' not in line and not line[0].isdigit():
                        lines.append(line.strip())
                
                transcript = ' '.join(lines)
                
                # Clean up file
                os.remove(vtt_file)
                
                if transcript:
                    return {"success": True, "transcript": transcript, "method": "yt-dlp"}
        
        return {"success": False, "error": "No transcript available via yt-dlp"}
    
    except Exception as e:
        return {"success": False, "error": f"yt-dlp error: {str(e)}"}

def fetch_with_api(video_id):
    """Try fetching with youtube-transcript-api"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        # Try to get transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Combine all text
        text = ' '.join([entry['text'] for entry in transcript_list])
        
        if text:
            return {"success": True, "transcript": text, "method": "youtube-transcript-api"}
        
        return {"success": False, "error": "Empty transcript from API"}
    
    except Exception as e:
        return {"success": False, "error": f"API error: {str(e)}"}

def main(url):
    """Main function to fetch transcript"""
    # Extract video ID
    video_id = None
    if 'youtube.com/watch?v=' in url:
        video_id = url.split('v=')[1].split('&')[0]
    elif 'youtu.be/' in url:
        video_id = url.split('youtu.be/')[1].split('?')[0]
    
    if not video_id:
        print("❌ Could not extract video ID from URL")
        return
    
    print(f"🎥 Video ID: {video_id}")
    print("🔍 Attempting to fetch transcript...\n")
    
    # Try yt-dlp first
    print("Method 1: Trying yt-dlp...")
    result = fetch_with_ytdlp(video_id)
    
    if not result['success']:
        # Try API as fallback
        print("Method 2: Trying youtube-transcript-api...")
        result = fetch_with_api(video_id)
    
    # Display results
    if result['success']:
        print(f"\n✅ Success! Transcript retrieved using {result['method']}")
        print(f"📊 Length: {len(result['transcript'])} characters")
        print("\n" + "="*60)
        print("TRANSCRIPT:")
        print("="*60 + "\n")
        print(result['transcript'][:1000] + "..." if len(result['transcript']) > 1000 else result['transcript'])
    else:
        print(f"\n❌ Failed to get transcript")
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.youtube.com/watch?v=1_twhMU9AxM"
    main(url)