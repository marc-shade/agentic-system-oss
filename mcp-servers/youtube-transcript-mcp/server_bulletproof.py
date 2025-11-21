#!/usr/bin/env python3
"""
BULLETPROOF YouTube Transcript MCP Server
Fixed implementation with proper transcript extraction
"""

import sys
import json
import logging
import subprocess
import re
import time
import hashlib
import pickle
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from urllib.parse import unquote

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("youtube-transcript-bulletproof")

# Try to use centralized logging
try:
    sys.path.insert(0, str(Path.home() / ".claude"))
    from mcp_logging_config import setup_mcp_logging
    logger = setup_mcp_logging("youtube-transcript-bulletproof")
    logger.info("Centralized logging initialized")
except ImportError:
    pass

class BulletproofYouTubeTranscriptServer:
    """Bulletproof YouTube Transcript MCP Server with working transcript extraction"""
    
    def __init__(self):
        self.name = "youtube-transcript-bulletproof"
        self.version = "5.0.0"
        self.cache_dir = Path.home() / ".cache" / "youtube-transcripts"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(days=7)
        logger.info(f"Initializing {self.name} v{self.version}")
    
    def extract_video_id(self, url: str) -> str:
        """Extract video ID from various YouTube URL formats."""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]+)',
            r'^([a-zA-Z0-9_-]+)$'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        raise ValueError(f"Could not extract video ID from URL: {url}")
    
    def get_cache_key(self, video_id: str, lang: str) -> str:
        """Generate cache key for a video/language combination."""
        return hashlib.md5(f"{video_id}_{lang}".encode()).hexdigest()
    
    def get_from_cache(self, video_id: str, lang: str) -> Optional[Dict[str, Any]]:
        """Get transcript from cache if available and not expired."""
        cache_key = self.get_cache_key(video_id, lang)
        cache_file = self.cache_dir / f"{cache_key}.pkl"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    cached_data = pickle.load(f)
                
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
        if result.get('success') and result.get('transcript'):
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
    
    def method_1_ytdlp(self, video_id: str, lang: str) -> Dict[str, Any]:
        """Method 1: Use yt-dlp - most reliable method."""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Use yt-dlp to extract subtitles
            cmd = [
                "yt-dlp",
                "--write-sub",
                "--write-auto-sub",
                "--sub-lang", f"{lang},en",
                "--skip-download",
                "--no-warnings",
                "--quiet",
                "--output", f"/tmp/%(id)s",
                url
            ]
            
            logger.info(f"Running yt-dlp for video {video_id}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=45, cwd="/tmp")
            
            # Look for generated subtitle files
            subtitle_patterns = [
                f"{video_id}.{lang}.vtt",
                f"{video_id}.{lang}-*.vtt", 
                f"{video_id}.en.vtt",
                f"{video_id}.en-*.vtt",
                f"{video_id}*.vtt"
            ]
            
            subtitle_file = None
            tmp_path = Path("/tmp")
            
            for pattern in subtitle_patterns:
                files = list(tmp_path.glob(pattern))
                if files:
                    subtitle_file = files[0]
                    logger.info(f"Found subtitle file: {subtitle_file}")
                    break
            
            if subtitle_file and subtitle_file.exists():
                transcript = self.parse_vtt_file(subtitle_file)
                subtitle_file.unlink(missing_ok=True)  # Clean up
                
                if transcript and len(transcript) > 50:  # Ensure we got real content
                    return {
                        "success": True,
                        "video_id": video_id,
                        "language": lang,
                        "transcript": transcript,
                        "method": "yt-dlp",
                        "length": len(transcript)
                    }
            
            return {
                "success": False,
                "error": "No subtitle file generated by yt-dlp or content too short"
            }
            
        except subprocess.TimeoutExpired:
            logger.error("yt-dlp timeout")
            return {
                "success": False,
                "error": "yt-dlp timeout after 45 seconds"
            }
        except Exception as e:
            logger.warning(f"yt-dlp method failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def method_2_youtube_transcript_api(self, video_id: str, lang: str) -> Dict[str, Any]:
        """Method 2: Use youtube-transcript-api library."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
            
            # Try to get transcript in preferred language, fallback to English
            languages = [lang]
            if lang != 'en':
                languages.append('en')
            
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
            
            if transcript_list and isinstance(transcript_list, list):
                # Join all transcript segments
                full_transcript = " ".join([item.get('text', '') for item in transcript_list if item.get('text')])
                
                if full_transcript and len(full_transcript) > 50:  # Ensure real content
                    return {
                        "success": True,
                        "video_id": video_id,
                        "language": lang,
                        "transcript": full_transcript.strip(),
                        "method": "youtube-transcript-api",
                        "length": len(full_transcript)
                    }
            
            return {
                "success": False,
                "error": "No transcript content found"
            }
            
        except TranscriptsDisabled:
            return {
                "success": False,
                "error": "Transcripts are disabled for this video"
            }
        except NoTranscriptFound:
            return {
                "success": False,
                "error": "No transcript found for this video"
            }
        except ImportError:
            logger.warning("youtube-transcript-api not available")
            return {
                "success": False,
                "error": "youtube-transcript-api not installed"
            }
        except Exception as e:
            logger.warning(f"youtube-transcript-api failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def method_3_direct_api(self, video_id: str, lang: str) -> Dict[str, Any]:
        """Method 3: Direct YouTube page scraping - FIXED VERSION."""
        try:
            page_url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
            
            logger.info(f"Fetching page for video {video_id}")
            response = requests.get(page_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                page_content = response.text
                
                # Look for player response in the page
                # Try multiple patterns for finding the player response
                patterns = [
                    r'var ytInitialPlayerResponse = ({.+?});',
                    r'"playerResponse":({.+?}),"playerAds"',
                    r'ytInitialPlayerResponse":\s*({.+?}),"playerAds"',
                    r'ytInitialPlayerResponse\s*=\s*({.+?});'
                ]
                
                player_response = None
                for pattern in patterns:
                    match = re.search(pattern, page_content)
                    if match:
                        try:
                            player_response = json.loads(match.group(1))
                            logger.info("Successfully parsed player response")
                            break
                        except json.JSONDecodeError:
                            continue
                
                if player_response:
                    # Extract captions from player response
                    captions = player_response.get('captions', {})
                    track_list = captions.get('playerCaptionsTracklistRenderer', {})
                    caption_tracks = track_list.get('captionTracks', [])
                    
                    # Find the best caption track
                    selected_track = None
                    for track in caption_tracks:
                        track_lang = track.get('languageCode', '')
                        if lang in track_lang or (lang == 'en' and track_lang.startswith('en')):
                            selected_track = track
                            break
                    
                    # Fallback to any English track
                    if not selected_track:
                        for track in caption_tracks:
                            if track.get('languageCode', '').startswith('en'):
                                selected_track = track
                                break
                    
                    # Use any available track as last resort
                    if not selected_track and caption_tracks:
                        selected_track = caption_tracks[0]
                    
                    if selected_track:
                        caption_url = selected_track.get('baseUrl')
                        if caption_url:
                            logger.info(f"Downloading captions from: {caption_url[:100]}...")
                            caption_response = requests.get(caption_url, headers=headers, timeout=10)
                            
                            if caption_response.status_code == 200:
                                transcript = self.parse_caption_response(caption_response.text)
                                
                                if transcript and len(transcript) > 50:
                                    return {
                                        "success": True,
                                        "video_id": video_id,
                                        "language": lang,
                                        "transcript": transcript,
                                        "method": "direct-api",
                                        "length": len(transcript)
                                    }
            
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
    
    def method_4_innertube_api(self, video_id: str, lang: str) -> Dict[str, Any]:
        """Method 4: Use YouTube's InnerTube API."""
        try:
            url = "https://www.youtube.com/youtubei/v1/player"
            api_key = "***REMOVED***"
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            data = {
                "videoId": video_id,
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": "2.20240101.00.00",
                        "hl": lang,
                        "gl": "US"
                    }
                }
            }
            
            response = requests.post(f"{url}?key={api_key}", headers=headers, json=data, timeout=15)
            
            if response.status_code == 200:
                player_response = response.json()
                
                # Extract captions
                captions = player_response.get('captions', {})
                caption_tracks = captions.get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
                
                for track in caption_tracks:
                    track_lang = track.get('languageCode', '')
                    if lang in track_lang or (lang == 'en' and track_lang.startswith('en')):
                        caption_url = track.get('baseUrl')
                        if caption_url:
                            caption_response = requests.get(caption_url, timeout=10)
                            if caption_response.status_code == 200:
                                transcript = self.parse_caption_response(caption_response.text)
                                
                                if transcript and len(transcript) > 50:
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
    
    def parse_caption_response(self, content: str) -> str:
        """Parse caption response - IMPROVED VERSION."""
        try:
            logger.info(f"Parsing caption response, length: {len(content)}, starts with: {content[:100]}")
            
            # Handle JSON3 format (YouTube's timeline format)
            if content.strip().startswith('{'):
                try:
                    data = json.loads(content)
                    events = data.get('events', [])
                    transcript_parts = []
                    
                    for event in events:
                        # Look for segments with text
                        if 'segs' in event:
                            for seg in event['segs']:
                                text = seg.get('utf8', '')
                                if text and text.strip():
                                    # Clean the text
                                    text = text.strip()
                                    text = re.sub(r'\n+', ' ', text)  # Replace newlines with spaces
                                    transcript_parts.append(text)
                        # Also check for direct text in events
                        elif 'dDurationMs' in event and event.get('segs'):
                            for seg in event['segs']:
                                text = seg.get('utf8', '')
                                if text and text.strip():
                                    transcript_parts.append(text.strip())
                    
                    if transcript_parts:
                        result = ' '.join(transcript_parts)
                        logger.info(f"Parsed JSON3 format, got {len(result)} characters")
                        return result
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse as JSON3: {e}")
                    pass
            
            # Handle XML format (Traditional subtitle format)
            if '<?xml' in content or '<transcript>' in content or '<text ' in content:
                try:
                    import xml.etree.ElementTree as ET
                    
                    # Clean up the XML first
                    xml_content = content
                    if not xml_content.startswith('<?xml'):
                        xml_content = '<?xml version="1.0" encoding="UTF-8"?><transcript>' + xml_content + '</transcript>'
                    
                    root = ET.fromstring(xml_content)
                    transcript_parts = []
                    
                    # Look for text elements
                    for text_elem in root.findall('.//text'):
                        text_content = text_elem.text
                        if text_content:
                            # Decode HTML entities and clean
                            text_content = unquote(text_content)
                            text_content = re.sub(r'&amp;', '&', text_content)
                            text_content = re.sub(r'&lt;', '<', text_content)
                            text_content = re.sub(r'&gt;', '>', text_content)
                            text_content = re.sub(r'&quot;', '"', text_content)
                            text_content = re.sub(r'&#39;', "'", text_content)
                            text_content = text_content.strip()
                            
                            if text_content:
                                transcript_parts.append(text_content)
                    
                    if transcript_parts:
                        result = ' '.join(transcript_parts)
                        logger.info(f"Parsed XML format, got {len(result)} characters")
                        return result
                        
                except ET.ParseError as e:
                    logger.warning(f"XML parsing error: {e}")
                    pass
            
            # Handle plain text or VTT format
            if content:
                lines = content.split('\n')
                transcript_parts = []
                
                for line in lines:
                    line = line.strip()
                    # Skip VTT headers, timing lines, and empty lines
                    if (line.startswith('WEBVTT') or
                        line.startswith('NOTE') or
                        '-->' in line or
                        line.startswith('STYLE') or
                        line.startswith('Kind:') or
                        line.isdigit() or
                        not line):
                        continue
                    
                    # Clean HTML tags and entities
                    clean_line = re.sub(r'<[^>]+>', '', line)
                    clean_line = re.sub(r'&nbsp;', ' ', clean_line)
                    clean_line = re.sub(r'&amp;', '&', clean_line)
                    clean_line = re.sub(r'&lt;', '<', clean_line)
                    clean_line = re.sub(r'&gt;', '>', clean_line)
                    clean_line = clean_line.strip()
                    
                    if clean_line:
                        transcript_parts.append(clean_line)
                
                if transcript_parts:
                    result = ' '.join(transcript_parts)
                    logger.info(f"Parsed as plain text, got {len(result)} characters")
                    return result
            
            logger.warning("Could not parse caption response")
            return ""
            
        except Exception as e:
            logger.error(f"Error parsing caption response: {e}")
            return ""
    
    def parse_vtt_file(self, vtt_path: Path) -> str:
        """Parse VTT subtitle file."""
        try:
            content = vtt_path.read_text(encoding='utf-8', errors='ignore')
            return self.parse_vtt_content(content)
        except Exception as e:
            logger.error(f"Error reading VTT file: {e}")
            return ""
    
    def parse_vtt_content(self, content: str) -> str:
        """Parse VTT content."""
        lines = content.split('\n')
        transcript_lines = []
        seen_lines = set()
        
        for line in lines:
            line = line.strip()
            
            # Skip VTT metadata and timing lines
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
            
            # Skip empty lines, pure digits, and duplicates
            if clean_line and not clean_line.isdigit() and clean_line not in seen_lines:
                transcript_lines.append(clean_line)
                seen_lines.add(clean_line)
        
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
            
            # Try methods in order of reliability
            methods = [
                ("yt-dlp", self.method_1_ytdlp),
                ("youtube-transcript-api", self.method_2_youtube_transcript_api),
                ("direct-api", self.method_3_direct_api),
                ("innertube-api", self.method_4_innertube_api),
            ]
            
            errors = []
            
            for method_name, method_func in methods:
                logger.info(f"Trying method: {method_name}")
                result = method_func(video_id, lang)
                
                if result.get("success") and result.get("transcript") and len(result.get("transcript", "")) > 50:
                    logger.info(f"Success with method: {method_name}, length: {result.get('length', 0)}")
                    # Cache the successful result
                    self.save_to_cache(video_id, lang, result)
                    return result
                else:
                    error_msg = f"{method_name}: {result.get('error', 'no transcript content')}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
                
                # Small delay between methods
                time.sleep(1)
            
            # All methods failed
            return {
                "success": False,
                "error": "All methods failed to extract transcript",
                "details": errors,
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
                        "description": "Get YouTube video transcript using multiple bulletproof methods (yt-dlp, youtube-transcript-api, direct API, InnerTube)",
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
        
        logger.info("MCP server ready - bulletproof transcript extraction active")
        
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
    server = BulletproofYouTubeTranscriptServer()
    server.run()

if __name__ == "__main__":
    main()