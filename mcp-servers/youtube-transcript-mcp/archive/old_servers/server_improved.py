#!/usr/bin/env python3
"""
YouTube Transcript MCP Server - Enhanced Version
Combines the best features from multiple implementations for maximum reliability.
"""

import asyncio
import logging
import re
import subprocess
import tempfile
import os
from typing import Any, Sequence, Optional, Dict, List
from urllib.parse import urlparse, parse_qs

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.types as types

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("youtube-transcript-mcp")


class YouTubeTranscriptServer:
    """Enhanced YouTube transcript server with multiple fallback methods."""
    
    def __init__(self):
        self.server = Server("youtube-transcript")
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Set up all server handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """List available tools."""
            return [
                types.Tool(
                    name="get_transcript",
                    description="Get the transcript of a YouTube video with multiple fallback methods",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The YouTube video URL"
                            },
                            "lang": {
                                "type": "string",
                                "description": "Preferred language code (default: en)",
                                "default": "en"
                            },
                            "format": {
                                "type": "string",
                                "description": "Output format: text, json, or srt",
                                "default": "text",
                                "enum": ["text", "json", "srt"]
                            }
                        },
                        "required": ["url"]
                    }
                ),
                types.Tool(
                    name="get_transcript_languages",
                    description="Get available transcript languages for a YouTube video",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The YouTube video URL"
                            }
                        },
                        "required": ["url"]
                    }
                ),
                types.Tool(
                    name="search_transcript",
                    description="Search within a YouTube video transcript",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The YouTube video URL"
                            },
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "lang": {
                                "type": "string",
                                "description": "Preferred language code (default: en)",
                                "default": "en"
                            }
                        },
                        "required": ["url", "query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None
        ) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """Handle tool calls."""
            
            if name == "get_transcript":
                return await self._get_transcript(arguments)
            elif name == "get_transcript_languages":
                return await self._get_transcript_languages(arguments)
            elif name == "search_transcript":
                return await self._search_transcript(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    def _extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from various URL formats."""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/watch\?.*v=([^&\n?#]+)',
            r'youtube\.com/shorts/([^&\n?#]+)',
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
    
    async def _get_transcript(self, arguments: dict) -> Sequence[types.TextContent]:
        """Get transcript using multiple methods."""
        url = arguments.get("url")
        lang = arguments.get("lang", "en")
        format_type = arguments.get("format", "text")
        
        if not url:
            return [types.TextContent(
                type="text",
                text="Error: URL parameter is required"
            )]
        
        try:
            video_id = self._extract_video_id(url)
            logger.info(f"Extracting transcript for video ID: {video_id}")
            
            # Try method 1: youtube-transcript-api (if available)
            transcript = await self._try_youtube_transcript_api(video_id, lang)
            
            # Try method 2: yt-dlp
            if not transcript:
                transcript = await self._try_ytdlp(url, lang)
            
            # Try method 3: Direct API call (fallback)
            if not transcript:
                transcript = await self._try_direct_api(video_id, lang)
            
            if not transcript:
                return [types.TextContent(
                    type="text",
                    text=f"Error: Could not extract transcript. The video may not have captions available."
                )]
            
            # Format output
            formatted = self._format_transcript(transcript, format_type)
            
            return [types.TextContent(
                type="text",
                text=formatted
            )]
            
        except Exception as e:
            logger.error(f"Error getting transcript: {str(e)}")
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    
    async def _try_youtube_transcript_api(self, video_id: str, lang: str) -> Optional[List[Dict]]:
        """Try using youtube-transcript-api library."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Try to get the requested language
            try:
                transcript = transcript_list.find_transcript([lang])
            except:
                # Fall back to any available transcript
                transcript = transcript_list.find_manually_created_transcript() or \
                           transcript_list.find_generated_transcript()
            
            if transcript:
                return transcript.fetch()
                
        except Exception as e:
            logger.debug(f"youtube-transcript-api method failed: {e}")
        
        return None
    
    async def _try_ytdlp(self, url: str, lang: str) -> Optional[List[Dict]]:
        """Try using yt-dlp to extract subtitles."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download subtitles
                cmd = [
                    "yt-dlp",
                    "--write-subs",
                    "--write-auto-subs",
                    "--sub-lang", lang,
                    "--skip-download",
                    "--output", os.path.join(temp_dir, "video.%(ext)s"),
                    "--quiet",
                    url
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    logger.debug(f"yt-dlp failed: {stderr.decode()}")
                    return None
                
                # Find subtitle file
                subtitle_files = [f for f in os.listdir(temp_dir) 
                                if f.endswith(('.vtt', '.srt', '.json'))]
                
                if not subtitle_files:
                    return None
                
                # Parse subtitle file
                subtitle_path = os.path.join(temp_dir, subtitle_files[0])
                return self._parse_subtitle_file(subtitle_path)
                
        except Exception as e:
            logger.debug(f"yt-dlp method failed: {e}")
        
        return None
    
    async def _try_direct_api(self, video_id: str, lang: str) -> Optional[List[Dict]]:
        """Try direct YouTube API call using curl."""
        try:
            # This is a fallback method using YouTube's internal API
            url = f"https://www.youtube.com/api/timedtext?v={video_id}&lang={lang}&fmt=json3"
            
            cmd = ["curl", "-s", url]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0 and stdout:
                import json
                data = json.loads(stdout.decode())
                
                if "events" in data:
                    transcript = []
                    for event in data["events"]:
                        if "segs" in event:
                            text = "".join(seg.get("utf8", "") for seg in event["segs"])
                            transcript.append({
                                "text": text,
                                "start": event.get("tStartMs", 0) / 1000,
                                "duration": event.get("dDurationMs", 0) / 1000
                            })
                    return transcript
                    
        except Exception as e:
            logger.debug(f"Direct API method failed: {e}")
        
        return None
    
    def _parse_subtitle_file(self, file_path: str) -> List[Dict]:
        """Parse subtitle file to transcript format."""
        transcript = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if file_path.endswith('.json'):
                import json
                data = json.loads(content)
                # Handle JSON format from yt-dlp
                return data
            
            elif file_path.endswith('.vtt'):
                # Parse WebVTT format
                lines = content.split('\n')
                i = 0
                while i < len(lines):
                    if '-->' in lines[i]:
                        # Parse timestamp
                        time_parts = lines[i].split('-->')
                        start_time = self._parse_vtt_time(time_parts[0].strip())
                        
                        # Get text
                        i += 1
                        text_lines = []
                        while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                            text_lines.append(lines[i].strip())
                            i += 1
                        
                        if text_lines:
                            text = ' '.join(text_lines)
                            # Clean HTML tags
                            text = re.sub(r'<[^>]+>', '', text)
                            transcript.append({
                                "text": text,
                                "start": start_time,
                                "duration": 0
                            })
                    i += 1
            
            elif file_path.endswith('.srt'):
                # Parse SRT format
                blocks = content.strip().split('\n\n')
                for block in blocks:
                    lines = block.split('\n')
                    if len(lines) >= 3 and '-->' in lines[1]:
                        time_parts = lines[1].split('-->')
                        start_time = self._parse_srt_time(time_parts[0].strip())
                        text = ' '.join(lines[2:])
                        transcript.append({
                            "text": text,
                            "start": start_time,
                            "duration": 0
                        })
            
        except Exception as e:
            logger.error(f"Error parsing subtitle file: {e}")
        
        return transcript
    
    def _parse_vtt_time(self, time_str: str) -> float:
        """Parse WebVTT timestamp to seconds."""
        parts = time_str.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return float(h) * 3600 + float(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return float(m) * 60 + float(s)
        return 0
    
    def _parse_srt_time(self, time_str: str) -> float:
        """Parse SRT timestamp to seconds."""
        time_str = time_str.replace(',', '.')
        return self._parse_vtt_time(time_str)
    
    def _format_transcript(self, transcript: List[Dict], format_type: str) -> str:
        """Format transcript based on requested format."""
        if format_type == "json":
            import json
            return json.dumps(transcript, indent=2)
        
        elif format_type == "srt":
            srt_output = []
            for i, entry in enumerate(transcript, 1):
                start = self._seconds_to_srt_time(entry["start"])
                end = self._seconds_to_srt_time(entry["start"] + entry.get("duration", 3))
                srt_output.append(f"{i}\n{start} --> {end}\n{entry['text']}\n")
            return '\n'.join(srt_output)
        
        else:  # text format
            # Clean up repetitions
            full_text = ' '.join(entry["text"] for entry in transcript)
            return self._clean_repetitions(full_text)
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')
    
    def _clean_repetitions(self, text: str) -> str:
        """Clean repeated phrases from auto-captions."""
        words = text.split()
        cleaned_words = []
        i = 0
        
        while i < len(words):
            found_repeat = False
            
            # Check for phrase repetitions
            for phrase_len in range(10, 0, -1):
                if i + phrase_len * 3 <= len(words):
                    phrase1 = words[i:i + phrase_len]
                    phrase2 = words[i + phrase_len:i + phrase_len * 2]
                    phrase3 = words[i + phrase_len * 2:i + phrase_len * 3]
                    
                    if phrase1 == phrase2 == phrase3:
                        cleaned_words.extend(phrase1)
                        i += phrase_len * 3
                        found_repeat = True
                        break
            
            if not found_repeat:
                cleaned_words.append(words[i])
                i += 1
        
        return ' '.join(cleaned_words)
    
    async def _get_transcript_languages(self, arguments: dict) -> Sequence[types.TextContent]:
        """Get available languages for a video."""
        url = arguments.get("url")
        
        if not url:
            return [types.TextContent(
                type="text",
                text="Error: URL parameter is required"
            )]
        
        try:
            video_id = self._extract_video_id(url)
            
            # Try youtube-transcript-api first
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                languages = []
                for transcript in transcript_list:
                    languages.append({
                        "code": transcript.language_code,
                        "name": transcript.language,
                        "is_generated": transcript.is_generated,
                        "is_translatable": transcript.is_translatable
                    })
                
                import json
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "video_id": video_id,
                        "languages": languages
                    }, indent=2)
                )]
                
            except:
                # Fallback to yt-dlp
                cmd = ["yt-dlp", "--list-subs", url]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    return [types.TextContent(
                        type="text",
                        text=stdout.decode()
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text="Could not retrieve available languages"
                    )]
                    
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    
    async def _search_transcript(self, arguments: dict) -> Sequence[types.TextContent]:
        """Search within a transcript."""
        url = arguments.get("url")
        query = arguments.get("query")
        lang = arguments.get("lang", "en")
        
        if not url or not query:
            return [types.TextContent(
                type="text",
                text="Error: Both URL and query parameters are required"
            )]
        
        try:
            # Get the transcript first
            transcript_result = await self._get_transcript({
                "url": url,
                "lang": lang,
                "format": "json"
            })
            
            if not transcript_result:
                return [types.TextContent(
                    type="text",
                    text="Error: Could not get transcript"
                )]
            
            import json
            transcript = json.loads(transcript_result[0].text)
            
            # Search for matches
            matches = []
            query_lower = query.lower()
            
            for entry in transcript:
                if query_lower in entry["text"].lower():
                    matches.append({
                        "time": entry["start"],
                        "text": entry["text"],
                        "context": self._get_context(transcript, entry, 2)
                    })
            
            if matches:
                result = f"Found {len(matches)} matches for '{query}':\n\n"
                for i, match in enumerate(matches, 1):
                    time_str = self._seconds_to_time(match["time"])
                    result += f"{i}. [{time_str}] {match['text']}\n"
                    if match["context"]:
                        result += f"   Context: {match['context']}\n"
                    result += "\n"
                
                return [types.TextContent(type="text", text=result)]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"No matches found for '{query}'"
                )]
                
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error searching transcript: {str(e)}"
            )]
    
    def _get_context(self, transcript: List[Dict], entry: Dict, context_size: int) -> str:
        """Get surrounding context for a transcript entry."""
        index = transcript.index(entry)
        start = max(0, index - context_size)
        end = min(len(transcript), index + context_size + 1)
        
        context_entries = transcript[start:end]
        context_text = ' '.join(e["text"] for e in context_entries if e != entry)
        
        return context_text[:200] + "..." if len(context_text) > 200 else context_text
    
    def _seconds_to_time(self, seconds: float) -> str:
        """Convert seconds to readable time format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
    
    async def run(self):
        """Run the server."""
        async with self.server._transport:
            await self.server.run()


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add centralized logging if available
    sys.path.insert(0, str(Path.home() / ".claude"))
    try:
        from mcp_logging_config import setup_mcp_logging
        logger = setup_mcp_logging("youtube-transcript")
    except ImportError:
        pass
    
    # Run the server
    server = YouTubeTranscriptServer()
    asyncio.run(server.run())