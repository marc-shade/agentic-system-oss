# YouTube Transcript MCP Tool Usage Guide

## Overview
The youtube-transcript-mcp tool is now configured and ready to use in Claude Desktop. It provides two main functions for extracting transcripts from YouTube videos.

## Available Tools

### 1. Get Transcript
**Tool**: `mcp__youtube-transcript-mcp__get_transcript`

**Parameters**:
- `url` (required): The YouTube video URL
- `lang` (optional): Language code for transcript (default: "en")

**Example Usage**:
```javascript
mcp__youtube-transcript-mcp__get_transcript({
  url: "https://youtu.be/fD8NLPU0WYU",
  lang: "en"
})
```

**Returns**:
- `success`: Whether the operation succeeded
- `video_id`: YouTube video ID
- `video_url`: Original URL
- `language`: Language of transcript
- `transcript`: Full transcript text
- `subtitle_format`: Format of extracted subtitles (vtt/srt)
- `character_count`: Total characters in transcript
- `word_count`: Total words in transcript
- `method`: Extraction method used (yt-dlp)

### 2. Get Available Languages
**Tool**: `mcp__youtube-transcript-mcp__get_transcript_languages`

**Parameters**:
- `url` (required): The YouTube video URL

**Example Usage**:
```javascript
mcp__youtube-transcript-mcp__get_transcript_languages({
  url: "https://youtu.be/fD8NLPU0WYU"
})
```

**Returns**:
- `success`: Whether the operation succeeded
- `video_id`: YouTube video ID
- `languages`: Array of available languages with:
  - `language_code`: ISO language code
  - `language`: Human-readable language name
  - `is_generated`: Whether it's auto-generated
  - `is_translatable`: Whether it can be translated

## Configuration Details

The tool is configured in Claude Desktop with:
- Python path: `/opt/homebrew/Caskroom/miniconda/base/bin/python3`
- Server path: `/Users/marc/Documents/Cline/MCP/youtube-transcript-mcp/server.py`
- Timeout: 120 seconds (for long videos)
- Uses yt-dlp for robust extraction

## Usage Notes

1. **Always use the MCP tool** when Marc shares YouTube links
2. **Automatic transcript extraction** - no manual steps needed
3. **Supports various URL formats**:
   - https://www.youtube.com/watch?v=VIDEO_ID
   - https://youtu.be/VIDEO_ID
   - https://youtube.com/embed/VIDEO_ID
   
4. **Error handling** - if a video doesn't have captions, the tool will report this gracefully

## Testing the Tool

After restarting Claude Desktop, test with:
```javascript
// Test with the BMAD workflow video
mcp__youtube-transcript-mcp__get_transcript({
  url: "https://youtu.be/fD8NLPU0WYU"
})
```

## Troubleshooting

If the tool isn't available after restart:
1. Check if youtube-transcript-mcp appears in available MCP servers
2. Verify the configuration in claude_desktop_config.json
3. Ensure yt-dlp is installed: `pip install yt-dlp`
4. Check server.py permissions and path

## Marc's Request
"omg, will you please always use the youtube scrapper? I need you to always use the transcript mcp to get the transript"

✅ This tool is now configured to automatically extract transcripts whenever YouTube links are shared!