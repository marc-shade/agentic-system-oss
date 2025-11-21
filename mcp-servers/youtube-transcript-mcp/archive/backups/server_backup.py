#!/usr/bin/env python3
"""
YouTube Transcript MCP Server
A reliable MCP server for extracting YouTube video transcripts.
"""

import asyncio
import logging
from typing import Any, Sequence
from urllib.parse import urlparse, parse_qs
import re

from mcp.server.fastmcp import FastMCP

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("youtube-transcript-mcp")

# Create the MCP server with explicit settings
mcp = FastMCP("YouTube Transcript", log_level="INFO")

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    # Regular YouTube URL patterns
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
        r'youtube\.com/watch\?.*v=([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If no pattern matches, try parsing as query parameter
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com', 'm.youtube.com']:
        if 'v' in parse_qs(parsed_url.query):
            return parse_qs(parsed_url.query)['v'][0]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path.lstrip('/')
    
    raise ValueError(f"Could not extract video ID from URL: {url}")

@mcp.tool()
def get_transcript(url: str, lang: str = "en", max_length: int = None, offset: int = 0, page_size: int = None) -> dict:
    """
    Retrieves the transcript of a YouTube video using yt-dlp (robust method).
    
    Args:
        url: The URL of the YouTube video
        lang: The preferred language for the transcript (default: "en")
        max_length: Maximum characters to return (default: None for full transcript)
        offset: Starting character position for pagination (default: 0)
        page_size: Number of characters per page for pagination (default: None)
    
    Returns:
        Dictionary containing transcript text and metadata
    """
    import subprocess
    import tempfile
    import os
    
    try:
        video_id = extract_video_id(url)
        logger.info(f"Extracting transcript for video ID: {video_id} using yt-dlp")
        
        # Use yt-dlp to extract subtitles
        with tempfile.TemporaryDirectory() as temp_dir:
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
                
                # Find the subtitle file
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
                full_transcript = parse_subtitle_content(content)
                
                # Apply pagination and limiting
                total_length = len(full_transcript)
                
                # Calculate pagination
                if page_size and page_size > 0:
                    end_pos = offset + page_size
                    transcript_text = full_transcript[offset:end_pos]
                    has_more = end_pos < total_length
                    next_offset = end_pos if has_more else None
                elif max_length and max_length > 0:
                    end_pos = min(offset + max_length, total_length)
                    transcript_text = full_transcript[offset:end_pos]
                    has_more = end_pos < total_length
                    next_offset = end_pos if has_more else None
                else:
                    # Return full transcript from offset
                    transcript_text = full_transcript[offset:]
                    has_more = False
                    next_offset = None
                
                result = {
                    "success": True,
                    "video_id": video_id,
                    "video_url": url,
                    "language": lang,
                    "transcript": transcript_text,
                    "subtitle_format": subtitle_files[0].split('.')[-1],
                    "character_count": len(transcript_text),
                    "word_count": len(transcript_text.split()),
                    "method": "yt-dlp",
                    "total_length": total_length,
                    "offset": offset,
                    "has_more": has_more
                }
                
                if next_offset is not None:
                    result["next_offset"] = next_offset
                    
                if page_size:
                    result["page_size"] = page_size
                    result["current_page"] = (offset // page_size) + 1
                    result["total_pages"] = (total_length + page_size - 1) // page_size
                
                return result
                
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
    import re
    
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
    
    # Join lines and handle repeated phrases
    full_text = ' '.join(transcript_lines)
    
    # Remove duplicate phrases that appear 3 times in a row
    # This handles YouTube's auto-caption repetition issue
    words = full_text.split()
    cleaned_words = []
    i = 0
    
    while i < len(words):
        # Look for repeated sequences
        found_repeat = False
        
        # Check for phrase repetitions of various lengths (1-10 words)
        for phrase_len in range(10, 0, -1):
            if i + phrase_len * 3 <= len(words):
                # Get three consecutive phrases
                phrase1 = words[i:i + phrase_len]
                phrase2 = words[i + phrase_len:i + phrase_len * 2]
                phrase3 = words[i + phrase_len * 2:i + phrase_len * 3]
                
                # Check if all three phrases are identical
                if phrase1 == phrase2 == phrase3:
                    # Add the phrase only once
                    cleaned_words.extend(phrase1)
                    i += phrase_len * 3
                    found_repeat = True
                    break
        
        if not found_repeat:
            cleaned_words.append(words[i])
            i += 1
    
    return ' '.join(cleaned_words)

@mcp.tool()
def get_transcript_languages(url: str) -> dict:
    """
    Get available transcript languages for a YouTube video.
    
    Args:
        url: The URL of the YouTube video
    
    Returns:
        Dictionary containing available languages
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return {
            "success": False,
            "error": "youtube-transcript-api not installed",
            "languages": []
        }
    
    try:
        video_id = extract_video_id(url)
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        languages = []
        for transcript in transcript_list:
            languages.append({
                "language_code": transcript.language_code,
                "language": transcript.language,
                "is_generated": transcript.is_generated,
                "is_translatable": transcript.is_translatable
            })
        
        return {
            "success": True,
            "video_id": video_id,
            "languages": languages
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "languages": []
        }

@mcp.tool()
def get_transcript_summary(url: str, lang: str = "en", summary_length: int = 5000) -> dict:
    """
    Get a summary of a YouTube video transcript, useful for very long videos.
    
    Args:
        url: The URL of the YouTube video
        lang: The preferred language for the transcript (default: "en")
        summary_length: Target length for summary (default: 5000 characters)
    
    Returns:
        Dictionary containing transcript summary and metadata
    """
    try:
        # Get the full transcript info first (just metadata)
        full_result = get_transcript(url, lang, max_length=1000)  # Get first 1000 chars for metadata
        
        if not full_result["success"]:
            return full_result
            
        total_length = full_result.get("total_length", 0)
        
        if total_length <= summary_length:
            # If transcript is short enough, return full transcript
            return get_transcript(url, lang)
        
        # For long transcripts, get strategic samples
        # Take beginning, middle, and end sections
        section_size = summary_length // 3
        
        beginning = get_transcript(url, lang, max_length=section_size, offset=0)
        middle_offset = total_length // 2 - section_size // 2
        middle = get_transcript(url, lang, max_length=section_size, offset=middle_offset)
        end_offset = max(0, total_length - section_size)
        end = get_transcript(url, lang, max_length=section_size, offset=end_offset)
        
        # Combine sections
        combined_transcript = (
            f"[BEGINNING]\n{beginning['transcript']}\n\n"
            f"[MIDDLE]\n{middle['transcript']}\n\n"
            f"[END]\n{end['transcript']}"
        )
        
        return {
            "success": True,
            "video_id": full_result["video_id"],
            "video_url": url,
            "language": lang,
            "transcript": combined_transcript,
            "character_count": len(combined_transcript),
            "word_count": len(combined_transcript.split()),
            "total_length": total_length,
            "summary_type": "strategic_sampling",
            "method": "yt-dlp",
            "is_summary": True,
            "compression_ratio": round(len(combined_transcript) / total_length, 2)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "video_url": url,
            "transcript": ""
        }

if __name__ == "__main__":
    # Centralized logging configuration
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path.home() / ".claude"))
    try:
        from mcp_logging_config import setup_mcp_logging
        # Initialize centralized logging
        logger = setup_mcp_logging("youtube-transcript")
    except ImportError:
        # Fallback to basic logging if centralized logging not available
        pass
    
    mcp.run()