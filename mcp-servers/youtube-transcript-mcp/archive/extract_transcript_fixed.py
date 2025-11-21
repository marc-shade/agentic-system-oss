#!/usr/bin/env python3

import subprocess
import tempfile
import os
import re
import sys
import json

def extract_video_id(url):
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)',
        r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError(f"Could not extract video ID from URL: {url}")

def parse_vtt_content(content):
    """Parse VTT content and extract clean text."""
    lines = content.split('\n')
    transcript_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip metadata and timing lines
        if (line.startswith('WEBVTT') or 
            line.startswith('NOTE') or
            '-->' in line or
            line.startswith('STYLE') or
            not line):
            continue
            
        # Clean HTML tags and formatting
        clean_line = re.sub(r'<[^>]+>', '', line)
        clean_line = re.sub(r'&nbsp;', ' ', clean_line)
        clean_line = re.sub(r'&amp;', '&', clean_line)
        clean_line = re.sub(r'&lt;', '<', clean_line)
        clean_line = re.sub(r'&gt;', '>', clean_line)
        
        if clean_line and not clean_line.isdigit():
            transcript_lines.append(clean_line)
    
    return ' '.join(transcript_lines)

def get_transcript_with_api(video_id):
    """Try to get transcript using youtube_transcript_api as fallback."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Combine all text segments
        full_text = ' '.join([segment['text'] for segment in transcript_list])
        return full_text
    except Exception as e:
        print(f"youtube_transcript_api error: {e}")
        return None

def get_transcript(url, lang="en"):
    """Get transcript using yt-dlp with improved error handling."""
    try:
        video_id = extract_video_id(url)
        print(f"Extracting transcript for video ID: {video_id}")
        
        # First try with yt-dlp
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to get available subtitles first
            info_cmd = [
                "/opt/homebrew/Caskroom/miniconda/base/bin/yt-dlp",
                "--list-subs",
                url
            ]
            
            print("Checking available subtitles...")
            info_result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
            
            if info_result.returncode == 0:
                print("Available subtitles info:")
                print(info_result.stdout[:500])  # Print first 500 chars
            
            # Now try to download subtitles
            cmd = [
                "/opt/homebrew/Caskroom/miniconda/base/bin/yt-dlp",
                "--write-subs",
                "--write-auto-subs", 
                "--sub-lang", f"{lang},{lang}-*,en,en-*",  # Try multiple language codes
                "--skip-download",
                "--no-warnings",
                "--quiet",
                "--output", os.path.join(temp_dir, f"{video_id}.%(ext)s"),
                url
            ]
            
            print("Attempting to download subtitles...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                print(f"yt-dlp error: {result.stderr}")
                # Try fallback method
                print("Trying youtube_transcript_api as fallback...")
                transcript = get_transcript_with_api(video_id)
                if transcript:
                    return {
                        "success": True,
                        "video_id": video_id,
                        "language": lang,
                        "transcript": transcript,
                        "length": len(transcript),
                        "method": "youtube_transcript_api"
                    }
                return None
                
            # Find subtitle file
            subtitle_files = []
            for f in os.listdir(temp_dir):
                if f.startswith(video_id) and ('.vtt' in f or '.srt' in f):
                    subtitle_files.append(f)
            
            print(f"Found subtitle files: {subtitle_files}")
            
            if not subtitle_files:
                print("No subtitle files found with yt-dlp, trying fallback...")
                transcript = get_transcript_with_api(video_id)
                if transcript:
                    return {
                        "success": True,
                        "video_id": video_id,
                        "language": lang,
                        "transcript": transcript,
                        "length": len(transcript),
                        "method": "youtube_transcript_api"
                    }
                return None
                
            subtitle_file = os.path.join(temp_dir, subtitle_files[0])
            
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            transcript = parse_vtt_content(content)
            return {
                "success": True,
                "video_id": video_id,
                "language": lang,
                "transcript": transcript,
                "length": len(transcript),
                "method": "yt-dlp"
            }
            
    except Exception as e:
        print(f"Error: {e}")
        # Last resort - try the API method
        try:
            video_id = extract_video_id(url)
            transcript = get_transcript_with_api(video_id)
            if transcript:
                return {
                    "success": True,
                    "video_id": video_id,
                    "language": lang,
                    "transcript": transcript,
                    "length": len(transcript),
                    "method": "youtube_transcript_api_fallback"
                }
        except:
            pass
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        print("❌ No URL provided")
        sys.exit(1)
    
    result = get_transcript(url)
    if result:
        print(f"\n✅ Successfully extracted transcript!")
        print(f"📹 Video ID: {result['video_id']}")
        print(f"🗣️ Language: {result['language']}")
        print(f"📝 Length: {result['length']} characters")
        print(f"🔧 Method: {result['method']}")
        print(f"\n📄 Transcript:")
        print("=" * 50)
        print(result['transcript'])
        print("=" * 50)
        
        # Also save to file for easy access
        output_file = f"/Users/marc/Documents/Cline/MCP/youtube-transcript-mcp/transcript_{result['video_id']}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result['transcript'])
        print(f"\n💾 Saved to: {output_file}")
    else:
        print("❌ Failed to extract transcript")