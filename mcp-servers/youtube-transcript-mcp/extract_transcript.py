#!/usr/bin/env python3

import subprocess
import tempfile
import os
import re
import sys

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
    """Parse VTT content and extract clean text with deduplication."""
    lines = content.split('\n')
    transcript_lines = []
    seen_lines = set()  # For deduplication
    
    for line in lines:
        line = line.strip()
        
        # Skip metadata and timing lines
        if (line.startswith('WEBVTT') or 
            line.startswith('NOTE') or
            '-->' in line or
            line.startswith('STYLE') or
            line.startswith('Kind:') or  # Skip caption metadata
            not line):
            continue
            
        # Clean HTML tags and formatting
        clean_line = re.sub(r'<[^>]+>', '', line)
        clean_line = re.sub(r'&nbsp;', ' ', clean_line)
        clean_line = re.sub(r'&amp;', '&', clean_line)
        clean_line = re.sub(r'&lt;', '<', clean_line)
        clean_line = re.sub(r'&gt;', '>', clean_line)
        clean_line = clean_line.strip()
        
        # Skip empty lines, digits, and duplicates
        if clean_line and not clean_line.isdigit() and clean_line not in seen_lines:
            transcript_lines.append(clean_line)
            seen_lines.add(clean_line)
    
    return ' '.join(transcript_lines)

def get_transcript(url, lang="en"):
    """Get transcript using yt-dlp."""
    try:
        video_id = extract_video_id(url)
        print(f"Extracting transcript for video ID: {video_id}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            cmd = [
                "yt-dlp",
                "--write-subs",
                "--write-auto-subs", 
                "--sub-lang", lang,
                "--skip-download",
                "--output", os.path.join(temp_dir, f"{video_id}.%(ext)s"),
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                print(f"yt-dlp error: {result.stderr}")
                return None
                
            # Find subtitle file
            subtitle_files = [f for f in os.listdir(temp_dir) if f.startswith(video_id) and ('.vtt' in f or '.srt' in f)]
            
            if not subtitle_files:
                print("No subtitle files found")
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
                "length": len(transcript)
            }
            
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "https://youtu.be/Lcqat4iP_lE?si=Ni_ubOplQKK51pd1"
    
    result = get_transcript(url)
    if result:
        print(f"\n✅ Successfully extracted transcript!")
        print(f"📹 Video ID: {result['video_id']}")
        print(f"🗣️ Language: {result['language']}")
        print(f"📝 Length: {result['length']} characters")
        print(f"\n📄 Full transcript:")
        print("=" * 50)
        print(result['transcript'])
        print("=" * 50)
        
        # Also save to file for MCP server to read
        with open(f"full_transcript_{result['video_id']}.txt", 'w', encoding='utf-8') as f:
            f.write(result['transcript'])
    else:
        print("❌ Failed to extract transcript")