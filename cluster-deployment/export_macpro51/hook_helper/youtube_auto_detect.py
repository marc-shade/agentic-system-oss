#!/usr/bin/env python3
"""
YouTube URL Auto-Detection Hook
Automatically detects YouTube URLs in user prompts and processes them
"""

import sys
import re
import os

def detect_youtube_url(text):
    """Detect YouTube URLs in text."""
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)',
        r'https?://youtu\.be/([a-zA-Z0-9_-]+)',
        r'https?://(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]+)',
        r'https?://(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]+)',
    ]

    for pattern in youtube_patterns:
        match = re.search(pattern, text)
        if match:
            video_id = match.group(1)
            full_url = match.group(0)
            return video_id, full_url

    return None, None

def main():
    """Main hook handler"""
    try:
        # Read the user's prompt from stdin
        prompt = sys.stdin.read()

        # Check for YouTube URL
        video_id, youtube_url = detect_youtube_url(prompt)

        if youtube_url:
            # Check if prompt is ONLY a YouTube URL (no other text)
            cleaned_prompt = re.sub(r'https?://[^\s]+', '', prompt).strip()

            if not cleaned_prompt or len(cleaned_prompt) < 10:
                # Just a URL - auto-process it
                print("\n🎥 YouTube URL detected! Analyzing video...\n")
                print(f"Video ID: {video_id}")
                print(f"URL: {youtube_url}\n")

                # Check if transcript already exists
                transcript_dir = "/home/marc/Documents/Cline/MCP/youtube-transcript-mcp"
                transcript_file = f"{transcript_dir}/full_transcript_{video_id}.txt"

                if os.path.exists(transcript_file):
                    print("✅ Transcript already exists - reading cached version\n")
                    with open(transcript_file, 'r') as f:
                        transcript = f.read()

                    print(f"📝 Transcript loaded ({len(transcript)} characters)\n")
                    print("Now analyzing the video content...\n")

                    # Modify prompt to include transcript
                    enhanced_prompt = f"""Analyze this YouTube video (ID: {video_id}, URL: {youtube_url}).

TRANSCRIPT:
{transcript}

Please provide:
1. Video title and main topic
2. Key points (comprehensive bullet list)
3. Technical details, tools, or technologies mentioned
4. Relevance to AI/AGI/agentic systems (if applicable)
5. Actionable recommendations or integration suggestions

Be thorough and focus on practical insights."""

                    print(enhanced_prompt)
                    sys.exit(0)
                else:
                    print("⏳ Transcript not found - extracting now...\n")
                    # Will let the normal workflow handle extraction

                    enhanced_prompt = f"""Please analyze this YouTube video: {youtube_url}

Use the youtube-analyst agent or extract the transcript using:
/home/marc/Documents/Cline/MCP/youtube-transcript-mcp/extract_transcript.py "{youtube_url}"

Then provide a comprehensive analysis including:
1. Main topic and key points
2. Technical details
3. Relevance to current work
4. Actionable recommendations"""

                    print(enhanced_prompt)
                    sys.exit(0)
            else:
                # URL with additional context - let it through normally
                # but add a note about transcript availability
                if os.path.exists(f"{transcript_dir}/full_transcript_{video_id}.txt"):
                    print(f"\n💡 Note: Transcript for video {video_id} is already available\n")

        # No YouTube URL or mixed content - pass through
        print(prompt)
        sys.exit(0)

    except Exception as e:
        # On error, pass through original prompt
        print(prompt if 'prompt' in locals() else "", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
