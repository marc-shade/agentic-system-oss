# YouTube Video Analysis

Analyze the provided YouTube video URL using the youtube-analyst agent.

## Process

1. Extract the transcript using `/Users/marc/Documents/Cline/MCP/youtube-transcript-mcp/extract_transcript.py`
2. If transcript already exists (check for `full_transcript_<video_id>.txt` in the youtube-transcript-mcp directory), read it directly
3. Analyze the content comprehensively
4. Provide:
   - Video summary
   - Key technical points
   - Tools/technologies mentioned
   - Relevance to current work
   - Actionable recommendations

## Usage

```
/youtube <youtube_url>
```

Or just paste a YouTube URL and the system will detect it automatically.