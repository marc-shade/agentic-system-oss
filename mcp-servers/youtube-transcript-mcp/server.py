#!/usr/bin/env python3
"""
FastMCP Wrapper: youtube-transcript-mcp
Bulletproof YouTube Transcript Extraction
"""

import sys
import json
from pathlib import Path
from fastmcp import FastMCP
from typing import Dict, Any

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Initialize FastMCP server
mcp = FastMCP("youtube-transcript-mcp")

# Import original server logic
try:
    from server_original import BulletproofYouTubeTranscriptServer
    transcript_server = BulletproofYouTubeTranscriptServer()
    HAS_ORIGINAL = True
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    HAS_ORIGINAL = False

@mcp.tool()
def get_transcript(url: str, lang: str = "en") -> Dict[str, Any]:
    """Get YouTube video transcript using bulletproof extraction methods
    
    Args:
        url: YouTube video URL or video ID
        lang: Language code (default: en)
    
    Returns:
        Dictionary containing transcript data and metadata
    """
    if not HAS_ORIGINAL:
        return {
            "success": False,
            "error": "Original transcript server not available"
        }
    
    try:
        arguments = {"url": url, "lang": lang}
        result = transcript_server.get_transcript(arguments)
        return result
    except Exception as e:
        return {
            "success": False,
            "error": f"Transcript extraction failed: {str(e)}"
        }

@mcp.tool() 
def status() -> Dict[str, Any]:
    """Get server status"""
    return {
        "server": "youtube-transcript-mcp",
        "framework": "FastMCP",
        "status": "operational",
        "original_available": HAS_ORIGINAL,
        "methods": ["yt-dlp", "youtube-transcript-api", "direct-api", "innertube-api"] if HAS_ORIGINAL else [],
        "version": "5.0.0"
    }

if __name__ == "__main__":
    mcp.run()
