#!/usr/bin/env python3
"""
YouTube Transcript MCP Server - Bulletproof Implementation
Based on analysis of working MCP servers and best practices
"""

import sys
import json
import logging
import subprocess
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

# Set up logging first - before importing MCP logging
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
        self.version = "2.0.0"
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
    
    def get_transcript_via_api(self, video_id: str, lang: str = "en") -> Dict[str, Any]:
        """Get transcript using youtube-transcript-api library."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            
            # Try to get transcript using the static method - this is the correct API usage
            try:
                # Try multiple language formats
                languages_to_try = [lang, f'{lang}-US', f'{lang}-GB', 'en', 'en-US', 'en-GB']
                transcript_list = None
                
                for lang_code in languages_to_try:
                    try:
                        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang_code])
                        logger.info(f"Successfully got transcript with language: {lang_code}")
                        break
                    except Exception as lang_error:
                        logger.debug(f"Language {lang_code} failed: {lang_error}")
                        continue
                
                if transcript_list is None:
                    # Try without specifying language (get any available)
                    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
                    
            except Exception as e:
                logger.warning(f"youtube-transcript-api static method failed: {e}")
                # Don't return here, let it fall through to the general exception handler
                # which will try the yt-dlp fallback
                raise e
            
            # Extract text from transcript segments
            # The API returns a list of dictionaries with 'text', 'start', 'duration' keys
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
            else:
                logger.warning("Unexpected transcript format from API")
                return {
                    "success": False,
                    "error": "Unexpected transcript format from API",
                    "method": "youtube-transcript-api"
                }
            
        except ImportError:
            logger.warning("youtube-transcript-api not available, trying yt-dlp fallback")
            return self.get_transcript_via_ytdlp(video_id, lang)
        except Exception as e:
            logger.warning(f"youtube-transcript-api failed: {e}, trying yt-dlp fallback")
            fallback_result = self.get_transcript_via_ytdlp(video_id, lang)
            if fallback_result.get("success"):
                return fallback_result
            else:
                return {
                    "success": False,
                    "error": f"youtube-transcript-api failed: {str(e)}, yt-dlp also failed: {fallback_result.get('error', 'unknown error')}",
                    "method": "youtube-transcript-api"
                }
    
    def get_transcript_via_ytdlp(self, video_id: str, lang: str = "en") -> Dict[str, Any]:
        """Get transcript using yt-dlp as fallback."""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            
            # Use yt-dlp to get subtitle info
            cmd = [
                "yt-dlp",
                "--write-auto-sub",
                "--sub-lang", lang,
                "--skip-download",
                "--print", "%(title)s",
                url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Look for generated subtitle files
                subtitle_files = list(Path(".").glob(f"*{video_id}*.vtt"))
                
                if subtitle_files:
                    subtitle_file = subtitle_files[0]
                    transcript = self.parse_vtt_file(subtitle_file)
                    
                    # Clean up the file
                    subtitle_file.unlink(missing_ok=True)
                    
                    return {
                        "success": True,
                        "video_id": video_id,
                        "language": lang,
                        "transcript": transcript,
                        "method": "yt-dlp"
                    }
            
            # If yt-dlp fails, try the working script
            return self.get_transcript_via_script(video_id, lang)
            
        except Exception as e:
            logger.warning(f"yt-dlp failed: {e}, falling back to script")
            return self.get_transcript_via_script(video_id, lang)
    
    def get_transcript_via_script(self, video_id: str, lang: str = "en") -> Dict[str, Any]:
        """Get transcript using the working extract_transcript.py script."""
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            script_path = Path(__file__).parent / "extract_transcript.py"
            
            if not script_path.exists():
                return {
                    "success": False,
                    "error": "extract_transcript.py script not found"
                }
            
            cmd = ["python3", str(script_path), url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                output = result.stdout
                
                if "Successfully extracted transcript!" in output:
                    # Check if a transcript file was created
                    transcript_file = Path(__file__).parent / f"full_transcript_{video_id}.txt"
                    
                    if transcript_file.exists():
                        # Read the full transcript from file
                        transcript = transcript_file.read_text(encoding='utf-8')
                        
                        # Clean up the file
                        transcript_file.unlink(missing_ok=True)
                        
                        return {
                            "success": True,
                            "video_id": video_id,
                            "language": lang,
                            "transcript": transcript,
                            "method": "extract_script",
                            "length": len(transcript)
                        }
                    else:
                        # Fallback to parsing stdout (but this will be limited)
                        lines = output.split('\n')
                        transcript = ""
                        
                        # Parse the output to extract transcript
                        in_transcript = False
                        transcript_lines = []
                        
                        for line in lines:
                            if "=" * 50 in line:
                                if in_transcript:
                                    break  # End of transcript
                                else:
                                    in_transcript = True  # Start of transcript
                                    continue
                            
                            if in_transcript:
                                transcript_lines.append(line)
                        
                        transcript = '\n'.join(transcript_lines).strip()
                        
                        return {
                            "success": True,
                            "video_id": video_id,
                            "language": lang,
                            "transcript": transcript,
                            "method": "extract_script_fallback",
                            "length": len(transcript)
                        }
            
            return {
                "success": False,
                "error": f"Script failed: {result.stderr}",
                "output": result.stdout
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Script execution failed: {str(e)}"
            }
    
    def parse_vtt_file(self, vtt_path: Path) -> str:
        """Parse VTT subtitle file and extract clean text with deduplication."""
        content = vtt_path.read_text(encoding='utf-8')
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
    
    def get_transcript(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Main transcript retrieval method with multiple fallbacks."""
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
            
            # Try multiple methods in order of preference
            result = self.get_transcript_via_api(video_id, lang)
            
            if result.get("success"):
                logger.info(f"Successfully retrieved transcript using {result.get('method')}")
                return result
            else:
                logger.warning(f"API method failed, trying fallback methods for video {video_id}")
                # The get_transcript_via_api method already tries fallbacks internally,
                # but let's ensure we get the result from the fallback
                return result
                
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
                        "description": "Get the transcript/captions of a YouTube video using multiple fallback methods",
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