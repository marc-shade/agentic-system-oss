#!/usr/bin/env python3
"""
YouTube Transcript MCP Server - Alternative Implementation
Uses yt-dlp for more robust transcript extraction.
"""

import asyncio
import logging
import subprocess
import json
import tempfile
import os
from typing import Any, Sequence
from urllib.parse import urlparse, parse_qs
import re

from mcp.server.fastmcp import FastMCP

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("youtube-transcript-alternative")

# Create the MCP server
mcp = FastMCP("YouTube Transcript Alternative")

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
        r'youtube\.com/watch\?.*v=([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com', 'm.youtube.com']:
        if 'v' in parse_qs(parsed_url.query):
            return parse_qs(parsed_url.query)['v'][0]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path.lstrip('/')
    
    raise ValueError(f"Could not extract video ID from URL: {url}")

@mcp.tool()
def get_transcript_ytdlp(url: str, lang: str = "en") -> dict:
    """
    Retrieves the transcript of a YouTube video using yt-dlp.
    
    Args:
        url: The URL of the YouTube video
        lang: The preferred language for the transcript (default: "en")
    
    Returns:
        Dictionary containing transcript text and metadata
    """
    try:
        video_id = extract_video_id(url)
        logger.info(f"Extracting transcript for video ID: {video_id} using yt-dlp")
        
        # Use yt-dlp to extract subtitles
        with tempfile.TemporaryDirectory() as temp_dir:
            subtitle_file = os.path.join(temp_dir, f"{video_id}.{lang}.vtt")
            
            # Try to download subtitles with yt-dlp
            cmd = [
                "yt-dlp",
                "--write-subs",
                "--write-auto-subs",
                "--sub-lang", lang,
                "--skip-download",
                "--output", os.path.join(temp_dir, f"{video_id}.%(ext)s"),
                url
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode != 0:
                    logger.error(f"yt-dlp error: {result.stderr}")
                    return {
                        "success": False,
                        "error": f"yt-dlp failed: {result.stderr}",
                        "video_url": url,
                        "transcript": ""
                    }
                
                # Find the subtitle file (it might have different extensions)
                subtitle_files = [f for f in os.listdir(temp_dir) if f.startswith(video_id) and ('.vtt' in f or '.srt' in f)]
                
                if not subtitle_files:
                    return {
                        "success": False,
                        "error": "No subtitle files found. Video may not have captions available.",
                        "video_url": url,
                        "transcript": ""
                    }
                
                # Read the subtitle file
                subtitle_path = os.path.join(temp_dir, subtitle_files[0])
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Parse VTT/SRT content to extract text
                transcript_text = parse_subtitle_content(content)
                
                return {
                    "success": True,
                    "video_id": video_id,
                    "video_url": url,
                    "language": lang,
                    "transcript": transcript_text,
                    "subtitle_format": subtitle_files[0].split('.')[-1],
                    "raw_content": content[:1000]  # First 1000 chars of raw content
                }
                
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": "yt-dlp timeout - video may be too long or unavailable",
                    "video_url": url,
                    "transcript": ""
                }
            except FileNotFoundError:
                return {
                    "success": False,
                    "error": "yt-dlp not found. Please install with: pip install yt-dlp",
                    "video_url": url,
                    "transcript": ""
                }
                
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error getting transcript: {error_msg}")
        
        return {
            "success": False,
            "error": error_msg,
            "video_url": url,
            "transcript": ""
        }

def parse_subtitle_content(content: str) -> str:
    """Parse VTT or SRT subtitle content to extract clean text."""
    lines = content.split('\n')
    transcript_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines, timing lines, and WEBVTT headers
        if not line or line.startswith('WEBVTT') or '-->' in line or line.isdigit():
            continue
        
        # Skip style and position tags
        if line.startswith('<') and line.endswith('>'):
            continue
            
        # Remove HTML tags and formatting
        clean_line = re.sub(r'<[^>]+>', '', line)
        clean_line = clean_line.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        
        if clean_line and not clean_line.isdigit():
            transcript_lines.append(clean_line)
    
    return ' '.join(transcript_lines)

@mcp.tool()
def get_transcript_fallback(url: str, lang: str = "en") -> dict:
    """
    Fallback method using the original youtube-transcript-api.
    
    Args:
        url: The URL of the YouTube video
        lang: The preferred language for the transcript (default: "en")
    
    Returns:
        Dictionary containing transcript text and metadata
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api.formatters import TextFormatter
        
        video_id = extract_video_id(url)
        logger.info(f"Fallback: Extracting transcript for video ID: {video_id}")
        
        # Try original API
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
        formatter = TextFormatter()
        transcript_text = formatter.format_transcript(transcript_list)
        
        return {
            "success": True,
            "video_id": video_id,
            "video_url": url,
            "language": lang,
            "transcript": transcript_text,
            "method": "youtube-transcript-api",
            "total_segments": len(transcript_list)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Fallback method also failed: {str(e)}",
            "video_url": url,
            "transcript": ""
        }

if __name__ == "__main__":
    mcp.run()