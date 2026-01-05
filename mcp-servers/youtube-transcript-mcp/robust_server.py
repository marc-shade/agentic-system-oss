#!/usr/bin/env python3
"""
Robust YouTube Transcript MCP Server
Tries multiple methods to extract transcripts, avoiding rate limits
"""

import sys
import json
import logging
import subprocess
import re
import time
import hashlib
import pickle
import os
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("youtube-transcript-robust")

# Try to use centralized logging
try:
    sys.path.insert(0, str(Path.home() / ".claude"))
    from mcp_logging_config import setup_mcp_logging
    logger = setup_mcp_logging("youtube-transcript-robust")
    logger.info("Centralized logging initialized")
except ImportError:
    pass

class RobustYouTubeTranscriptServer:
    """Robust YouTube Transcript MCP Server with multiple fallback methods"""
    
    def __init__(self):
        self.name = "youtube-transcript-robust"
        self.version = "4.0.0"
        self.cache_dir = Path.home() / ".cache" / "youtube-transcripts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(days=7)  # Cache for 7 days
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
    
    def get_cache_key(self, video_id: str, lang: str) -> str:
        """Generate cache key for a video/language combination."""
        return hashlib.md5(f"{video_id}_{lang}".encode(), usedforsecurity=False).hexdigest()
    
    def get_from_cache(self, video_id: str, lang: str) -> Optional[Dict[str, Any]]:
        """Get transcript from cache if available and not expired."""
        cache_key = self.get_cache_key(video_id, lang)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                
                # Check if cache is still valid
                if datetime.now() - cached_data['timestamp'] < self.cache_ttl:
                    logger.info(f"Cache hit for {video_id} ({lang})")
                    cached_data['result']['method'] = 'cache'
                    return cached_data['result']
                else:
                    logger.info(f"Cache expired for {video_id} ({lang})")
                    cache_file.unlink()
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        return None
    
    def save_to_cache(self, video_id: str, lang: str, result: Dict[str, Any]):
        """Save successful result to cache."""
        if result.get('success'):
            cache_key = self.get_cache_key(video_id, lang)
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump({
                        'timestamp': datetime.now(),
                        'result': result
                    }, f)
                logger.info(f"Cached result for {video_id} ({lang})")
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
    
    def method_1_direct_api(self, video_id: str, lang: str) -> Dict[str, Any]:
        """Method 1: Direct YouTube API request (no external libraries)."""
        try:
            # Build the direct API URL
            base_url = "https://www.youtube.com/api/timedtext"
            
            # Try to get the page first to extract necessary parameters
            page_url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            
            # Get video page to extract player response
            response = requests.get(page_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Look for caption tracks in the page
                import re
                
                # Try to find captionTracks in the page
                caption_match = re.search(r'"captionTracks":\[(.*?)\]', response.text)
                if caption_match:
                    try:
                        # Parse the caption tracks
                        caption_data = json.loads('[' + caption_match.group(1) + ']')
                        
                        # Find the right language track
                        for track in caption_data:
                            if lang in track.get('languageCode', ''):
                                caption_url = track.get('baseUrl')
                                if caption_url:
                                    # Download the captions
                                    caption_response = requests.get(caption_url, headers=headers, timeout=10)
                                    if caption_response.status_code == 200:
                                        # Parse the response (usually XML or JSON3)
                                        transcript = self.parse_caption_response(caption_response.text)
                                        
                                        return {
                                            "success": True,
                                            "video_id": video_id,
                                            "language": lang,
                                            "transcript": transcript,
                                            "method": "direct-api",
                                            "length": len(transcript)
                                        }
                    except Exception as e:
                        logger.warning(f"Error parsing caption tracks: {e}")
            
            return {
                "success": False,
                "error": "Could not extract captions from page"
            }
            
        except Exception as e:
            logger.warning(f"Direct API method failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def method_2_ytdlp_cookies(self, video_id: str, lang: str) -> Dict[str, Any]:
        """Method 2: Use yt-dlp with cookies to avoid rate limits."""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Try with cookies and different user agent
            cmd = [
                "yt-dlp",
                "--write-sub",
                "--write-auto-sub",
                "--sub-lang", f"{lang},en",
                "--skip-download",
                "--quiet",
                "--no-warnings",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "--output", f"/tmp/%(id)s",
                url
            ]
            
            # Add cookies if available
            cookies_file = Path.home() / ".youtube-cookies.txt"
            if cookies_file.exists():
                cmd.extend(["--cookies", str(cookies_file)])
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Look for subtitle files
            for ext in ['vtt', 'srt', 'ass']:
                subtitle_file = Path(f"/tmp/{video_id}.{lang}.{ext}")
                if not subtitle_file.exists():
                    subtitle_file = Path(f"/tmp/{video_id}.en.{ext}")
                
                if subtitle_file.exists():
                    transcript = self.parse_subtitle_file(subtitle_file)
                    subtitle_file.unlink(missing_ok=True)
                    
                    return {
                        "success": True,
                        "video_id": video_id,
                        "language": lang,
                        "transcript": transcript,
                        "method": "ytdlp-cookies",
                        "length": len(transcript)
                    }
            
            return {
                "success": False,
                "error": "No subtitle files generated"
            }
            
        except Exception as e:
            logger.warning(f"yt-dlp with cookies failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def method_3_innertube_api(self, video_id: str, lang: str) -> Dict[str, Any]:
        """Method 3: Use YouTube's InnerTube API directly."""
        try:
            # InnerTube API endpoint
            url = "https://www.youtube.com/youtubei/v1/player"
            
            # API key (public, used by YouTube web)
            api_key = os.getenv("YOUTUBE_INNERTUBE_API_KEY", "")
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Request body
            data = {
                "videoId": video_id,
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": "2.20240101.00.00",
                        "hl": lang,
                        "gl": "US",
                        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    }
                }
            }
            
            response = requests.post(
                f"{url}?key={api_key}",
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                player_response = response.json()
                
                # Extract captions
                captions = player_response.get('captions', {})
                caption_tracks = captions.get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
                
                for track in caption_tracks:
                    if lang in track.get('languageCode', ''):
                        caption_url = track.get('baseUrl')
                        if caption_url:
                            # Download captions
                            caption_response = requests.get(caption_url, timeout=10)
                            if caption_response.status_code == 200:
                                transcript = self.parse_caption_response(caption_response.text)
                                
                                return {
                                    "success": True,
                                    "video_id": video_id,
                                    "language": lang,
                                    "transcript": transcript,
                                    "method": "innertube-api",
                                    "length": len(transcript)
                                }
            
            return {
                "success": False,
                "error": "InnerTube API did not return captions"
            }
            
        except Exception as e:
            logger.warning(f"InnerTube API failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def method_4_pytube(self, video_id: str, lang: str) -> Dict[str, Any]:
        """Method 4: Use pytube library as fallback."""
        try:
            from pytube import YouTube
            
            url = f"https://www.youtube.com/watch?v={video_id}"
            yt = YouTube(url)
            
            # Try to get captions
            if lang in yt.captions:
                caption = yt.captions[lang]
            elif 'en' in yt.captions:
                caption = yt.captions['en']
            elif yt.captions:
                # Get any available caption
                caption = list(yt.captions.values())[0]
            else:
                return {
                    "success": False,
                    "error": "No captions available"
                }
            
            # Get the caption text
            transcript = caption.generate_srt_captions()
            
            # Clean SRT format to plain text
            transcript = self.clean_srt_transcript(transcript)
            
            return {
                "success": True,
                "video_id": video_id,
                "language": lang,
                "transcript": transcript,
                "method": "pytube",
                "length": len(transcript)
            }
            
        except ImportError:
            logger.warning("pytube not installed")
            return {
                "success": False,
                "error": "pytube not installed"
            }
        except Exception as e:
            logger.warning(f"pytube failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def method_5_youtube_dl(self, video_id: str, lang: str) -> Dict[str, Any]:
        """Method 5: Use youtube-dl (older but sometimes works when yt-dlp doesn't)."""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            cmd = [
                "youtube-dl",
                "--write-auto-sub",
                "--sub-lang", lang,
                "--skip-download",
                "--quiet",
                "--output", f"/tmp/%(id)s",
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            # Look for subtitle files
            subtitle_file = Path(f"/tmp/{video_id}.{lang}.vtt")
            if not subtitle_file.exists():
                subtitle_file = Path(f"/tmp/{video_id}.en.vtt")
            
            if subtitle_file.exists():
                transcript = self.parse_subtitle_file(subtitle_file)
                subtitle_file.unlink(missing_ok=True)
                
                return {
                    "success": True,
                    "video_id": video_id,
                    "language": lang,
                    "transcript": transcript,
                    "method": "youtube-dl",
                    "length": len(transcript)
                }
            
            return {
                "success": False,
                "error": "youtube-dl did not generate subtitle file"
            }
            
        except Exception as e:
            logger.warning(f"youtube-dl failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def parse_caption_response(self, content: str) -> str:
        """Parse caption response (XML or JSON3 format)."""
        try:
            # Try JSON3 format first
            if content.startswith('{'):
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
            
            # Try XML format
            elif '<?xml' in content or '<transcript>' in content:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(content)
                
                transcript_parts = []
                for text_elem in root.findall('.//text'):
                    text = text_elem.text
                    if text:
                        transcript_parts.append(text.strip())
                
                return ' '.join(transcript_parts)
            
            # Fallback to raw text
            return content
            
        except Exception as e:
            logger.warning(f"Error parsing caption response: {e}")
            return content
    
    def parse_subtitle_file(self, file_path: Path) -> str:
        """Parse subtitle file (VTT, SRT, etc.) to plain text."""
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        
        if '.vtt' in str(file_path):
            return self.parse_vtt_content(content)
        elif '.srt' in str(file_path):
            return self.clean_srt_transcript(content)
        else:
            # Generic parsing
            lines = content.split('\n')
            transcript_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip timing lines and metadata
                if ('-->' in line or 
                    line.isdigit() or 
                    not line or
                    line.startswith('WEBVTT')):
                    continue
                transcript_lines.append(line)
            
            return ' '.join(transcript_lines)
    
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
    
    def clean_srt_transcript(self, content: str) -> str:
        """Clean SRT format to plain text."""
        lines = content.split('\n')
        transcript_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip numbers and timestamps
            if (line.isdigit() or 
                '-->' in line or 
                not line):
                continue
            transcript_lines.append(line)
        
        return ' '.join(transcript_lines)
    
    def get_transcript(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Main method that tries all available methods in order."""
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
            
            # Check cache first
            cached_result = self.get_from_cache(video_id, lang)
            if cached_result:
                return cached_result
            
            # Try all methods in order
            methods = [
                ("Direct API", self.method_1_direct_api),
                ("yt-dlp with cookies", self.method_2_ytdlp_cookies),
                ("InnerTube API", self.method_3_innertube_api),
                ("pytube", self.method_4_pytube),
                ("youtube-dl", self.method_5_youtube_dl),
            ]
            
            errors = []
            
            for method_name, method_func in methods:
                logger.info(f"Trying method: {method_name}")
                result = method_func(video_id, lang)
                
                if result.get("success"):
                    logger.info(f"Success with method: {method_name}")
                    # Cache the successful result
                    self.save_to_cache(video_id, lang, result)
                    return result
                else:
                    error_msg = f"{method_name}: {result.get('error', 'unknown error')}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                
                # Small delay between methods to avoid rate limiting
                time.sleep(0.5)
            
            # All methods failed
            return {
                "success": False,
                "error": "All methods failed",
                "details": errors,
                "video_id": video_id
            }
            
        except Exception as e:
            logger.error(f"Error getting transcript: {e}")
            return {
                "success": False,
                "error": str(e)
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
                        "description": "Get YouTube video transcript using multiple robust methods with caching",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "YouTube video URL or video ID"
                                },
                                "lang": {
                                    "type": "string",
                                    "description": "Language code (default: en)",
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
        """Handle notification requests."""
        method = request.get("method", "")
        logger.info(f"Received notification: {method}")
    
    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Main request handler."""
        method = request.get("method", "")
        request_id = request.get("id")
        
        logger.info(f"Handling request: {method}")
        
        # Handle notifications
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
            logger.error(f"Error handling request: {e}")
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
        
        # Configure stdio for MCP
        try:
            sys.stdin.reconfigure(encoding='utf-8', newline='')
            sys.stdout.reconfigure(encoding='utf-8', newline='')
        except AttributeError:
            pass
        
        logger.info("MCP server ready")
        
        # Main request loop
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
    server = RobustYouTubeTranscriptServer()
    server.run()

if __name__ == "__main__":
    main()