#!/usr/bin/env python3
"""
YouTube Transcript MCP Server - Fixed Implementation
Prioritizes yt-dlp to avoid rate limiting issues
"""

import sys
import json
import logging
import subprocess
import asyncio
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Set up logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("youtube-transcript")

# Try to use centralized logging
try:
    sys.path.insert(0, str(Path.home() / ".claude"))
    from mcp_logging_config import setup_mcp_logging
    logger = setup_mcp_logging("youtube-transcript")
    logger.info("Centralized logging initialized successfully")
except ImportError:
    logger.info("Using basic logging configuration")

class YouTubeTranscriptServer:
    """YouTube Transcript MCP Server Implementation"""
    
    def __init__(self):
        self.name = "youtube-transcript"
        self.version = "3.0.0"
        logger.info(f"Initializing {self.name} v{self.version}")
    
    def extract_video_id(self, url: str) -> str:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]+)',
            r'^([a-zA-Z0-9_-]+)$'  # Direct video ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from URL: {url}")
    
    def get_transcript_via_ytdlp(self, video_id: str, lang: str = "en") -> Dict[str, Any]:
        """Get transcript using yt-dlp as primary method."""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # First, try to get subtitles with yt-dlp
            # Use --write-sub for manual subtitles and --write-auto-sub for auto-generated
            cmd = [
                "yt-dlp",
                "--write-sub",           # Get manual subtitles if available
                "--write-auto-sub",      # Fall back to auto-generated subtitles
                "--sub-lang", f"{lang},{lang}-*,en,en-*",  # Try requested language and English
                "--skip-download",       # Don't download the video
                "--no-warnings",         # Suppress warnings
                "--quiet",              # Reduce output noise
                "--output", f"%(id)s",  # Use video ID as filename
                url
            ]
            
            logger.info(f"Running yt-dlp for video {video_id}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd="/tmp")
            
            # Look for generated subtitle files in /tmp
            subtitle_patterns = [
                f"/tmp/{video_id}.{lang}.vtt",
                f"/tmp/{video_id}.{lang}-*.vtt",
                f"/tmp/{video_id}.en.vtt",
                f"/tmp/{video_id}.en-*.vtt",
                f"/tmp/{video_id}*.vtt"
            ]
            
            subtitle_file = None
            for pattern in subtitle_patterns:
                files = list(Path("/tmp").glob(pattern.split("/")[-1]))
                if files:
                    subtitle_file = files[0]
                    logger.info(f"Found subtitle file: {subtitle_file}")
                    break
            
            if subtitle_file and subtitle_file.exists():
                transcript = self.parse_vtt_file(subtitle_file)
                
                # Clean up the file
                subtitle_file.unlink(missing_ok=True)
                
                return {
                    "success": True,
                    "video_id": video_id,
                    "language": lang,
                    "transcript": transcript,
                    "method": "yt-dlp",
                    "length": len(transcript)
                }
            else:
                logger.warning(f"No subtitle file found for video {video_id}")
                # Try alternative extraction method
                return self.get_transcript_via_ytdlp_json(video_id, lang)
                
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp timeout")
            return {
                "success": False,
                "error": "yt-dlp timeout after 60 seconds"
            }
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            return {
                "success": False,
                "error": f"yt-dlp failed: {str(e)}"
            }
    
    def get_transcript_via_ytdlp_json(self, video_id: str, lang: str = "en") -> Dict[str, Any]:
        """Get transcript using yt-dlp JSON output."""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Get video info with subtitles in JSON format
            cmd = [
                "yt-dlp",
                "--dump-json",
                "--write-sub",
                "--write-auto-sub",
                "--sub-lang", f"{lang},{lang}-*,en,en-*",
                "--skip-download",
                url
            ]
            
            logger.info(f"Getting video info via yt-dlp JSON for {video_id}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout:
                video_info = json.loads(result.stdout)
                
                # Check for subtitles in the JSON
                subtitles = video_info.get('subtitles', {})
                automatic_captions = video_info.get('automatic_captions', {})
                
                # Try to find subtitles for requested language
                sub_data = None
                for lang_code in [lang, f"{lang}-US", f"{lang}-GB", "en", "en-US", "en-GB"]:
                    if lang_code in subtitles:
                        sub_data = subtitles[lang_code]
                        break
                    elif lang_code in automatic_captions:
                        sub_data = automatic_captions[lang_code]
                        break
                
                if sub_data:
                    # Download the subtitle file
                    for sub_format in sub_data:
                        if sub_format.get('ext') in ['vtt', 'srv3', 'srv2', 'srv1', 'json3']:
                            sub_url = sub_format.get('url')
                            if sub_url:
                                # Download subtitle content
                                import urllib.request
                                with urllib.request.urlopen(sub_url) as response:
                                    content = response.read().decode('utf-8')
                                    
                                # Parse based on format
                                if sub_format.get('ext') == 'json3':
                                    transcript = self.parse_json3_subtitle(content)
                                else:
                                    transcript = self.parse_vtt_content(content)
                                
                                return {
                                    "success": True,
                                    "video_id": video_id,
                                    "language": lang,
                                    "transcript": transcript,
                                    "method": "yt-dlp-json",
                                    "length": len(transcript)
                                }
            
            return {
                "success": False,
                "error": "Could not extract subtitles from video"
            }
            
        except Exception as e:
            logger.error(f"yt-dlp JSON method failed: {e}")
            return {
                "success": False,
                "error": f"yt-dlp JSON method failed: {str(e)}"
            }
    
    def parse_json3_subtitle(self, content: str) -> str:
        """Parse JSON3 subtitle format."""
        try:
            data = json.loads(content)
            events = data.get('events', [])
            transcript_parts = []
            
            for event in events:
                if 'segs' in event:
                    for seg in event['segs']:
                        text = seg.get('utf8', '')
                        if text and text.strip():
                            transcript_parts.append(text.strip())
            
            return ' '.join(transcript_parts)
        except Exception as e:
            logger.error(f"Error parsing JSON3 subtitle: {e}")
            return ""
    
    def parse_vtt_content(self, content: str) -> str:
        """Parse VTT subtitle content."""
        lines = content.split('\n')
        transcript_lines = []
        seen_lines = set()
        
        for line in lines:
            line = line.strip()
            
            # Skip metadata and timing lines
            if (line.startswith('WEBVTT') or 
                line.startswith('NOTE') or
                '-->' in line or
                line.startswith('STYLE') or
                line.startswith('Kind:') or
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
    
    def parse_vtt_file(self, vtt_path: Path) -> str:
        """Parse VTT subtitle file and extract clean text with deduplication."""
        content = vtt_path.read_text(encoding='utf-8')
        return self.parse_vtt_content(content)
    
    def get_transcript_via_api_with_retry(self, video_id: str, lang: str = "en") -> Dict[str, Any]:
        """Get transcript using youtube-transcript-api with rate limit handling."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import YouTubeRequestFailed
            
            max_retries = 3
            retry_delay = 5  # seconds
            
            for attempt in range(max_retries):
                try:
                    # Try to get transcript
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang, 'en'])
                    
                    if transcript_list and isinstance(transcript_list, list):
                        full_transcript = " ".join([item.get('text', '') for item in transcript_list])
                        
                        return {
                            "success": True,
                            "video_id": video_id,
                            "language": lang,
                            "transcript": full_transcript.strip(),
                            "segments": len(transcript_list),
                            "method": "youtube-transcript-api"
                        }
                    
                except YouTubeRequestFailed as e:
                    if "429" in str(e):  # Rate limit error
                        logger.warning(f"Rate limited on attempt {attempt + 1}, waiting {retry_delay} seconds...")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                            continue
                    raise e
            
            return {
                "success": False,
                "error": "Rate limited after multiple attempts",
                "method": "youtube-transcript-api"
            }
            
        except ImportError:
            logger.warning("youtube-transcript-api not available")
            return {
                "success": False,
                "error": "youtube-transcript-api not installed",
                "method": "youtube-transcript-api"
            }
        except Exception as e:
            logger.error(f"API method failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "youtube-transcript-api"
            }
    
    def get_transcript(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Main transcript retrieval method - prioritizes yt-dlp to avoid rate limits."""
        url = arguments.get("url", "")
        lang = arguments.get("lang", "en")
        
        if not url:
            return {
                "success": False,
                "error": "URL is required"
            }
        
        try:
            # Extract video ID
            video_id = self.extract_video_id(url)
            logger.info(f"Extracting transcript for video ID: {video_id}")
            
            # Try yt-dlp first (avoids rate limiting)
            result = self.get_transcript_via_ytdlp(video_id, lang)
            
            if result.get("success"):
                logger.info(f"Successfully retrieved transcript using yt-dlp")
                return result
            
            # If yt-dlp fails, try the API with rate limit handling
            logger.info("yt-dlp failed, trying youtube-transcript-api")
            api_result = self.get_transcript_via_api_with_retry(video_id, lang)
            
            if api_result.get("success"):
                return api_result
            
            # Return the most informative error
            return {
                "success": False,
                "error": f"All methods failed. yt-dlp: {result.get('error', 'unknown')}, API: {api_result.get('error', 'unknown')}",
                "video_id": video_id
            }
                
        except Exception as e:
            logger.error(f"Error getting transcript: {e}")
            return {
                "success": False,
                "error": str(e),
                "video_id": getattr(locals(), 'video_id', 'unknown')
            }
    
    def handle_initialize(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request."""
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": self.name,
                    "version": self.version
                }
            }
        }
    
    def handle_tools_list(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/list request."""
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "tools": [
                    {
                        "name": "get_transcript",
                        "description": "Get the transcript/captions of a YouTube video using yt-dlp (primary) or youtube-transcript-api (fallback)",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "YouTube video URL or video ID"
                                },
                                "lang": {
                                    "type": "string",
                                    "description": "Language code for transcript (default: en)",
                                    "default": "en"
                                }
                            },
                            "required": ["url"]
                        }
                    }
                ]
            }
        }
    
    def handle_tools_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "get_transcript":
            result = self.get_transcript(arguments)
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }]
                }
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
            }
    
    def handle_notification(self, request: Dict[str, Any]) -> None:
        """Handle notification requests (no response needed)."""
        method = request.get("method", "")
        logger.info(f"Received notification: {method}")
    
    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Main request handler."""
        method = request.get("method", "")
        request_id = request.get("id")
        
        logger.info(f"Handling request: {method}")
        
        # Handle notifications (no response needed)
        if "notifications/" in method:
            self.handle_notification(request)
            return None
        
        try:
            if method == "initialize":
                return self.handle_initialize(request)
            elif method == "tools/list":
                return self.handle_tools_list(request)
            elif method == "tools/call":
                return self.handle_tools_call(request)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
        except Exception as e:
            logger.error(f"Error handling request {method}: {e}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
    
    def run(self):
        """Main server loop."""
        logger.info(f"{self.name} v{self.version} starting")
        
        # Configure stdio for MCP communication
        try:
            sys.stdin.reconfigure(encoding='utf-8', newline='')
            sys.stdout.reconfigure(encoding='utf-8', newline='')
        except AttributeError:
            # Python < 3.7 compatibility
            pass
        
        logger.info("MCP server ready - listening for requests")
        
        # Main request processing loop
        for line in sys.stdin:
            try:
                line = line.strip()
                if not line:
                    continue
                
                request = json.loads(line)
                response = self.handle_request(request)
                
                if response is not None:
                    print(json.dumps(response), flush=True)
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
                
            except KeyboardInterrupt:
                logger.info("Server shutting down")
                break
                
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                error_response = {
                    "jsonrpc": "2.0", 
                    "id": None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)

def main():
    """Main entry point."""
    server = YouTubeTranscriptServer()
    server.run()

if __name__ == "__main__":
    main()