#!/usr/bin/env python3
"""
YouTube Transcript MCP Server - Bulletproof Version
Focused on reliability and simplicity.
"""

import sys
import os
import json
import re
import subprocess
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs

# Import MCP SDK
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server.stdio import stdio_server


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from any YouTube URL format."""
    # Handle direct video ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
    
    # Parse URL
    parsed = urlparse(url)
    
    # youtube.com/watch?v=VIDEO_ID
    if parsed.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
        if parsed.path == '/watch':
            return parse_qs(parsed.query).get('v', [None])[0]
    
    # youtu.be/VIDEO_ID
    elif parsed.hostname == 'youtu.be':
        return parsed.path[1:]
    
    # youtube.com/embed/VIDEO_ID
    elif parsed.path.startswith('/embed/'):
        return parsed.path.split('/')[2]
    
    # youtube.com/v/VIDEO_ID
    elif parsed.path.startswith('/v/'):
        return parsed.path.split('/')[2]
    
    # Try regex as last resort
    patterns = [
        r'(?:v=|/)([0-9A-Za-z_-]{11}).*',
        r'(?:embed/)([0-9A-Za-z_-]{11})',
        r'(?:watch\?v=)([0-9A-Za-z_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError(f"Could not extract video ID from: {url}")


def get_transcript_youtube_api(video_id: str, lang: str = 'en') -> Optional[Dict]:
    """Try to get transcript using youtube-transcript-api."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        
        # Get available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Try to get requested language
        try:
            transcript = transcript_list.find_transcript([lang])
        except:
            # Get any available transcript
            try:
                transcript = transcript_list.find_manually_created_transcript()
            except:
                transcript = transcript_list.find_generated_transcript()
        
        # Fetch the transcript
        entries = transcript.fetch()
        
        # Convert to our format
        result = {
            'success': True,
            'video_id': video_id,
            'language': transcript.language_code,
            'is_generated': transcript.is_generated,
            'entries': entries,
            'text': ' '.join(entry['text'] for entry in entries)
        }
        
        return result
        
    except Exception as e:
        print(f"youtube-transcript-api failed: {e}", file=sys.stderr)
        return None


def get_transcript_ytdlp(url: str, lang: str = 'en') -> Optional[Dict]:
    """Get transcript using yt-dlp (most reliable method)."""
    import tempfile
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, 'transcript')
            
            # Build yt-dlp command
            cmd = [
                'yt-dlp',
                '--skip-download',
                '--write-auto-subs',
                '--write-subs',
                '--sub-lang', lang,
                '--sub-format', 'json3/vtt/srt/best',
                '--output', output_path,
                '--quiet',
                '--no-warnings',
                url
            ]
            
            # Run yt-dlp
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"yt-dlp error: {result.stderr}", file=sys.stderr)
                return None
            
            # Find the subtitle file
            subtitle_files = []
            for ext in ['.json3', '.vtt', '.srt']:
                for lang_variant in [f'.{lang}', f'.{lang}-orig', '']:
                    path = f"{output_path}{lang_variant}{ext}"
                    if os.path.exists(path):
                        subtitle_files.append(path)
            
            if not subtitle_files:
                # Try to find any subtitle file
                import glob
                subtitle_files = glob.glob(f"{output_path}*")
                subtitle_files = [f for f in subtitle_files if any(f.endswith(ext) for ext in ['.json3', '.vtt', '.srt'])]
            
            if not subtitle_files:
                return None
            
            # Parse the subtitle file
            subtitle_path = subtitle_files[0]
            
            if subtitle_path.endswith('.json3'):
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                entries = []
                text_parts = []
                
                for event in data.get('events', []):
                    if 'segs' in event:
                        text = ''.join(seg.get('utf8', '') for seg in event['segs'])
                        if text.strip():
                            entries.append({
                                'text': text,
                                'start': event.get('tStartMs', 0) / 1000.0,
                                'duration': event.get('dDurationMs', 0) / 1000.0
                            })
                            text_parts.append(text)
                
                return {
                    'success': True,
                    'video_id': extract_video_id(url),
                    'language': lang,
                    'entries': entries,
                    'text': ' '.join(text_parts)
                }
            
            else:
                # Parse VTT or SRT
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                entries = []
                text_parts = []
                
                # Simple parsing - just extract text
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('WEBVTT') and '-->' not in line and not line.isdigit():
                        # Remove tags
                        line = re.sub(r'<[^>]+>', '', line)
                        if line:
                            entries.append({'text': line})
                            text_parts.append(line)
                
                return {
                    'success': True,
                    'video_id': extract_video_id(url),
                    'language': lang,
                    'entries': entries,
                    'text': ' '.join(text_parts)
                }
                
    except Exception as e:
        print(f"yt-dlp method failed: {e}", file=sys.stderr)
        return None


def clean_transcript_text(text: str) -> str:
    """Clean up transcript text by removing repetitions."""
    # Remove triple repetitions (common in auto-captions)
    words = text.split()
    cleaned = []
    i = 0
    
    while i < len(words):
        # Check for repeated sequences
        found_repeat = False
        for length in range(10, 0, -1):
            if i + length * 3 <= len(words):
                seq1 = words[i:i+length]
                seq2 = words[i+length:i+length*2]
                seq3 = words[i+length*2:i+length*3]
                
                if seq1 == seq2 == seq3:
                    cleaned.extend(seq1)
                    i += length * 3
                    found_repeat = True
                    break
        
        if not found_repeat:
            cleaned.append(words[i])
            i += 1
    
    return ' '.join(cleaned)


# Create the MCP server
server = Server("youtube-transcript")


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="get_transcript",
            description="Get the transcript/captions of a YouTube video",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "YouTube video URL or video ID"
                    },
                    "lang": {
                        "type": "string",
                        "description": "Language code (e.g., 'en' for English)",
                        "default": "en"
                    }
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="get_available_transcripts",
            description="Get list of available transcript languages for a YouTube video",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "YouTube video URL or video ID"
                    }
                },
                "required": ["url"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict) -> List[types.TextContent]:
    """Handle tool calls."""
    
    if name == "get_transcript":
        url = arguments.get("url")
        lang = arguments.get("lang", "en")
        
        if not url:
            return [types.TextContent(
                type="text",
                text="Error: URL is required"
            )]
        
        try:
            # Extract video ID
            video_id = extract_video_id(url)
            
            # Try method 1: youtube-transcript-api (fastest)
            result = get_transcript_youtube_api(video_id, lang)
            
            # Try method 2: yt-dlp (most reliable)
            if not result:
                result = get_transcript_ytdlp(url, lang)
            
            if result and result.get('success'):
                # Clean the text
                clean_text = clean_transcript_text(result['text'])
                
                return [types.TextContent(
                    type="text",
                    text=f"Video ID: {result['video_id']}\n"
                         f"Language: {result['language']}\n"
                         f"Length: {len(clean_text)} characters\n\n"
                         f"Transcript:\n{clean_text}"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text="Error: Could not retrieve transcript. The video may not have captions available."
                )]
                
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    
    elif name == "get_available_transcripts":
        url = arguments.get("url")
        
        if not url:
            return [types.TextContent(
                type="text",
                text="Error: URL is required"
            )]
        
        try:
            video_id = extract_video_id(url)
            
            # Try youtube-transcript-api
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                languages = []
                for transcript in transcript_list:
                    lang_info = f"{transcript.language_code} - {transcript.language}"
                    if transcript.is_generated:
                        lang_info += " (auto-generated)"
                    else:
                        lang_info += " (manual)"
                    languages.append(lang_info)
                
                return [types.TextContent(
                    type="text",
                    text=f"Available transcripts for video {video_id}:\n" + "\n".join(languages)
                )]
                
            except:
                # Fallback to yt-dlp
                cmd = ['yt-dlp', '--list-subs', url]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    return [types.TextContent(
                        type="text",
                        text=result.stdout
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text="Could not retrieve available transcripts"
                    )]
                    
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    
    else:
        return [types.TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]


async def main():
    """Run the server."""
    # Run the server using stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="youtube-transcript",
                server_version="1.0.0"
            )
        )


if __name__ == "__main__":
    import asyncio
    
    # Set up logging
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Add centralized logging if available
    sys.path.insert(0, os.path.expanduser("~/.claude"))
    try:
        from mcp_logging_config import setup_mcp_logging
        logger = setup_mcp_logging("youtube-transcript")
    except ImportError:
        pass
    
    # Run the server
    asyncio.run(main())