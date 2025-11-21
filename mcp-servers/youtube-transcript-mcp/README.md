# YouTube Transcript MCP Server

A reliable MCP server for extracting YouTube video transcripts with enhanced error handling and multiple language support.

## Features

- Extract transcripts from YouTube videos using URLs
- Support for multiple languages
- Automatic fallback to available languages
- Raw transcript data with timestamps
- Comprehensive error handling
- Video metadata extraction

## Tools

### `get_transcript(url, lang="en")`
Retrieves the transcript of a YouTube video.

**Parameters:**
- `url` (string): The YouTube video URL
- `lang` (string, optional): Preferred language code (default: "en")

**Returns:**
- `success` (boolean): Whether the operation succeeded
- `video_id` (string): Extracted YouTube video ID
- `transcript` (string): Formatted transcript text
- `raw_transcript` (array): Raw transcript data with timestamps
- `language` (string): Language used for transcript
- `total_segments` (number): Number of transcript segments
- `duration_seconds` (number): Video duration in seconds

### `get_transcript_languages(url)`
Get available transcript languages for a YouTube video.

**Parameters:**
- `url` (string): The YouTube video URL

**Returns:**
- `success` (boolean): Whether the operation succeeded
- `video_id` (string): Extracted YouTube video ID
- `languages` (array): Available languages with metadata

## Installation

```bash
cd /Users/marc/Documents/Cline/MCP/youtube-transcript-mcp
pip install -r requirements.txt
```

## Usage

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "/Users/marc/Documents/Cline/MCP/.venv_mcp/bin/python",
      "args": [
        "/Users/marc/Documents/Cline/MCP/youtube-transcript-mcp/server.py"
      ],
      "timeout": 30000
    }
  }
}
```

## Supported URL Formats

- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://youtube.com/embed/VIDEO_ID`
- URLs with additional parameters and timestamps