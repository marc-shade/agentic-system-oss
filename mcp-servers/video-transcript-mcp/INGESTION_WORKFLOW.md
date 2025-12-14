# YouTube Video Ingestion Workflow

## Overview

The video-transcript-mcp now includes automatic chunking and memory ingestion support. When you provide a YouTube URL, the system can automatically:

1. **Fetch** the transcript via yt-dlp
2. **Chunk** it into context-safe segments (default 4000 tokens each)
3. **Extract** key concepts and methodologies
4. **Prepare** data for enhanced-memory storage

## Quick Start

### Using the New Tool (After Restart)

```python
# After restarting Claude Code to load updated MCP:
mcp__video-transcript-mcp__ingest_youtube_video({
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "max_chunk_tokens": 4000,  # Optional, default 4000
    "extract_metadata": True    # Optional, default True
})
```

This returns structured data with:
- `chunks`: List of text chunks with token counts
- `concepts`: Extracted key concepts
- `methodologies`: Extracted techniques
- `video_metadata`: Source information
- `ingestion_instructions`: How to process the data

### Complete Ingestion Example

```python
# 1. Ingest video and get chunked data
result = mcp__video-transcript-mcp__ingest_youtube_video({
    "url": "https://www.youtube.com/watch?v=ERJ2s73HwDs"
})

# 2. Spawn Memory Ingestion Agent to process chunks
Task({
    "subagent_type": "general-purpose",
    "prompt": f"""
    Process the following YouTube video chunks into enhanced-memory:
    
    {result}
    
    For each chunk, create an entity using create_entities.
    Link sequential chunks with create_association.
    Store concepts and methodologies as separate entities.
    Generate a summary entity linking to all chunks.
    """,
    "description": "Ingest YouTube transcript chunks"
})
```

## What Changed

### New Tool: `ingest_youtube_video`

Replaces the manual workflow of:
1. Fetch transcript
2. Manually chunk
3. Manually extract metadata
4. Manually store in memory

Now it's all automated in one tool call.

### Intelligent Chunking

- Splits on sentence boundaries (maintains coherence)
- Respects token limits (default 4000, configurable)
- Uses tiktoken for accurate Claude token counting
- Handles edge cases (very long sentences, unusual punctuation)

### Automatic Metadata Extraction

- Key concepts (technical terms, AI concepts, frameworks)
- Methodologies (techniques, approaches, best practices)
- Frequency-based filtering (only significant mentions)

## Requirements

**Before Using:**

1. **Restart Required**: You must restart Claude Code after MCP updates
   - The new `ingest_youtube_video` tool won't be available until restart
   - Existing tools (`fetch_youtube_transcript`, etc.) continue working

2. **Dependencies**: 
   ```bash
   pip3 install tiktoken
   ```
   Already installed if you ran `pip3 install -r requirements.txt`

## Testing

Test the workflow locally:

```bash
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/video-transcript-mcp
python3 test_chunking.py
```

## Memory Ingestion Agent

A specialized agent is available at `~/.claude/agents/memory-ingestion-agent.md` that:
- Processes chunks from ingestion data
- Stores each chunk as an entity
- Creates associations between chunks
- Stores concepts and methodologies
- Generates summary entities

## Example Output

For a 20-minute Stanford AI video:
- **Chunks**: 23 chunks (each ≤4000 tokens)
- **Concepts**: 10 key concepts (AI, data, training, model, etc.)
- **Methodologies**: 15 techniques
- **Total entities**: 49 (23 chunks + 10 concepts + 15 methods + 1 summary)

## Benefits

1. **No truncation**: Large transcripts handled automatically
2. **Context-aware**: Chunks maintain sentence boundaries
3. **Efficient retrieval**: Linked chunks enable contextual search
4. **Automatic extraction**: Key concepts identified automatically
5. **Scalable**: Works with any video length

## Migration from Old Workflow

**Before:**
```python
# Old manual workflow
transcript = mcp__video-transcript-mcp__fetch_youtube_transcript({"url": url})
# Manual chunking...
# Manual metadata extraction...
# Manual storage...
```

**After:**
```python
# New automated workflow
data = mcp__video-transcript-mcp__ingest_youtube_video({"url": url})
# Spawn Memory Ingestion Agent to process
Task(subagent_type="general-purpose", prompt=f"Process: {data}")
```

## Troubleshooting

**Tool not found:**
- Restart Claude Code to load updated MCP server

**Chunks too large:**
- Reduce `max_chunk_tokens` parameter (default 4000)

**Missing concepts:**
- Adjust `min_frequency` in extract_concepts (default 2)

**No transcript available:**
- Video may not have captions/subtitles
- Check video URL is valid YouTube URL
