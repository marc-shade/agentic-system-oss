#!/usr/bin/env python3
"""
Simple YouTube Transcript MCP Server - FastMCP Free
"""
import asyncio
import json
import sys
import subprocess
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from typing import Any, Dict, List

app = Server("youtube-transcript")

@app.list_tools()
async def list_tools() -> List[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="get_transcript",
            description="Get transcript from YouTube video",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "YouTube video URL"},
                    "lang": {"type": "string", "description": "Language code", "default": "en"}
                },
                "required": ["url"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls"""
    if name == "get_transcript":
        # Simple implementation using yt-dlp
        try:
            url = arguments["url"]
            result = subprocess.run([
                'yt-dlp', '--write-subs', '--write-auto-subs', '--sub-lang', 'en',
                '--skip-download', '--print', 'title', url
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return [types.TextContent(
                    type="text", 
                    text=f"Transcript extraction attempted for: {result.stdout.strip()}"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text="Transcript extraction failed - yt-dlp error"
                )]
        except Exception as e:
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
