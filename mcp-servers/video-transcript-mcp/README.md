# Video Transcript MCP Server

Autonomous knowledge acquisition from technical videos and talks via YouTube transcript processing.

## Features

- **YouTube Transcript Fetching**: Get transcripts from any YouTube video using yt-dlp
- **Transcript Cleaning**: Remove repetition, formatting artifacts, and stutters
- **Concept Extraction**: Identify key technical concepts discussed
- **Methodology Extraction**: Extract techniques and approaches described
- **Speaker Analysis**: Identify and separate multiple speakers
- **Memory Integration**: Store extracted knowledge in enhanced-memory system

## MCP Tools

| Tool | Description |
|------|-------------|
| `fetch_youtube_transcript` | Fetch transcript from YouTube URL |
| `clean_transcript` | Clean and structure raw transcript text |
| `extract_concepts` | Identify key technical concepts and terms |
| `extract_methodologies` | Extract techniques and best practices |
| `analyze_speakers` | Separate multiple speakers in transcript |
| `store_video_knowledge` | Store extracted knowledge in memory |

## Requirements

- Python 3.10+
- yt-dlp (for YouTube transcript fetching)
- mcp SDK

## Installation

```bash
pip install -r requirements.txt

# Install yt-dlp if not present
pip install yt-dlp
```

## Usage

```bash
# Run as MCP server
python server.py
```

## Configuration

Set `AGENTIC_SYSTEM_PATH` environment variable to configure the transcripts storage directory (defaults to `/mnt/agentic-system`).

## Integration

This MCP integrates with:
- **enhanced-memory-mcp**: For storing extracted knowledge
- **research-paper-mcp**: Complements academic paper research with video learning

## License

MIT
