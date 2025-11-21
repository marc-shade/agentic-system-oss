# YouTube Transcript MCP - Updated Usage Guide

## New Features Added ✨

The YouTube transcript MCP now supports:
- **Pagination** - Get transcripts in manageable chunks
- **Length limiting** - Specify maximum characters to return
- **Smart summaries** - Get strategic samples from very long videos

## Updated Tool Functions

### 1. `get_transcript` (Enhanced)

Now supports pagination and length limiting:

```python
get_transcript(
    url: str,                    # YouTube video URL
    lang: str = "en",           # Language (default: "en")
    max_length: int = None,     # Max characters to return
    offset: int = 0,            # Starting position
    page_size: int = None       # Characters per page
)
```

**Examples:**

```python
# Get first 5000 characters
result = get_transcript("https://youtu.be/VIDEO_ID", max_length=5000)

# Get second page (5000-10000 characters)
result = get_transcript("https://youtu.be/VIDEO_ID", max_length=5000, offset=5000)

# Use pagination (1000 chars per page)
result = get_transcript("https://youtu.be/VIDEO_ID", page_size=1000)

# Get page 3
result = get_transcript("https://youtu.be/VIDEO_ID", page_size=1000, offset=2000)
```

**New Response Fields:**
- `total_length` - Total transcript length
- `offset` - Current starting position
- `has_more` - Whether more content is available
- `next_offset` - Offset for next page (if has_more is true)
- `page_size` - Page size used (if pagination)
- `current_page` - Current page number (if pagination)
- `total_pages` - Total number of pages (if pagination)

### 2. `get_transcript_summary` (New)

For very long videos, get strategic samples:

```python
get_transcript_summary(
    url: str,                    # YouTube video URL
    lang: str = "en",           # Language (default: "en")
    summary_length: int = 5000  # Target summary length
)
```

**How it works:**
- If transcript ≤ summary_length: returns full transcript
- If transcript > summary_length: returns beginning + middle + end sections
- Provides substantial coverage while staying within token limits

**Additional Response Fields:**
- `is_summary` - True if this is a summary
- `summary_type` - "strategic_sampling" or "full"
- `compression_ratio` - Summary length / original length

### 3. `get_transcript_languages` (Unchanged)

```python
get_transcript_languages(url: str)
```

## Usage Examples for Claude Code

### Handle Large Videos with Pagination

```python
# Step 1: Get first chunk and check total length
first_chunk = mcp__youtube-transcript-mcp__get_transcript(
    url="https://youtu.be/Auuk1y4DRgk",
    max_length=5000
)

print(f"Total length: {first_chunk['total_length']} characters")
print(f"This chunk: {first_chunk['character_count']} characters")
print(f"Has more: {first_chunk['has_more']}")

# Step 2: Get next chunk if needed
if first_chunk['has_more']:
    next_chunk = mcp__youtube-transcript-mcp__get_transcript(
        url="https://youtu.be/Auuk1y4DRgk",
        max_length=5000,
        offset=first_chunk['next_offset']
    )
```

### Get Smart Summary for Analysis

```python
# Get strategic summary (beginning + middle + end)
summary = mcp__youtube-transcript-mcp__get_transcript_summary(
    url="https://youtu.be/Auuk1y4DRgk",
    summary_length=8000
)

print(f"Original: {summary['total_length']} chars")
print(f"Summary: {summary['character_count']} chars")
print(f"Compression: {summary['compression_ratio']}x")
```

### Paginated Reading Pattern

```python
url = "https://youtu.be/Auuk1y4DRgk"
page_size = 3000
offset = 0
all_content = []

while True:
    chunk = mcp__youtube-transcript-mcp__get_transcript(
        url=url,
        page_size=page_size,
        offset=offset
    )
    
    if not chunk['success']:
        break
        
    all_content.append(chunk['transcript'])
    
    if not chunk['has_more']:
        break
        
    offset = chunk['next_offset']

full_transcript = '\n'.join(all_content)
```

## Token Management

The enhanced MCP helps manage Claude Code's token limits:

- **max_length=5000**: Good for initial analysis (~5K tokens)
- **page_size=3000**: Manageable chunks for processing
- **get_transcript_summary**: Intelligent sampling for overview

## Migration from Old Version

If you have existing code using the old version:

```python
# Old way (might hit token limits)
result = mcp__youtube-transcript-mcp__get_transcript(url)

# New way (safe)
result = mcp__youtube-transcript-mcp__get_transcript(url, max_length=5000)
# or
summary = mcp__youtube-transcript-mcp__get_transcript_summary(url)
```

## Error Handling

All functions return the same error structure:
```python
{
    "success": false,
    "error": "description of error",
    "video_url": "original_url",
    "transcript": ""
}
```

## Restart Required

After updating the server code, restart Claude Code or the MCP server to use the new features.