#!/usr/bin/env python3
"""
YouTube URL detector hook - Auto-fetch transcripts when YouTube URLs are provided.
"""
import sys
import re
import json
import subprocess

def detect_youtube_url(prompt):
    """Detect YouTube URLs in user prompt."""
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'https?://youtu\.be/([a-zA-Z0-9_-]+)',
        r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in youtube_patterns:
        match = re.search(pattern, prompt)
        if match:
            return match.group(0)  # Return the full URL
    return None

def main():
    try:
        if len(sys.argv) < 2:
            sys.exit(0)  # No prompt provided
            
        user_prompt = sys.argv[1]
        youtube_url = detect_youtube_url(user_prompt)
        
        if youtube_url:
            # Check if the prompt ONLY contains a YouTube URL (no other text)
            cleaned_prompt = re.sub(r'https?://[^\s]+', '', user_prompt).strip()
            if not cleaned_prompt:
                print(f"🎥 YouTube URL detected: {youtube_url}")
                print("⚡ Auto-fetching transcript...")
                
                # Use YouTube transcript MCP to fetch transcript
                try:
                    cmd = f'python3 /Users/marc/Documents/Cline/MCP/youtube-transcript-mcp/extract_transcript.py "{youtube_url}"'
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print("✅ Transcript fetched successfully!")
                        # Output the transcript for Claude to process
                        print(result.stdout)
                    else:
                        print(f"❌ Failed to fetch transcript: {result.stderr}")
                        
                except Exception as e:
                    print(f"⚠️ Error fetching transcript: {e}")
                
                # Exit with code 2 to indicate "handled"
                sys.exit(2)
        
        # No YouTube URL or mixed content - continue normally
        sys.exit(0)
        
    except Exception as e:
        print(f"Error in YouTube detector: {e}", file=sys.stderr)
        sys.exit(0)  # Continue normally on error

if __name__ == "__main__":
    main()