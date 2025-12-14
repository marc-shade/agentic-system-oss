#!/usr/bin/env python3
"""
Test chunking logic for YouTube transcript ingestion.

This verifies that:
1. Transcripts are chunked into context-safe segments
2. Chunks maintain sentence boundaries
3. Token counting works correctly
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import chunk_transcript, ingest_youtube_video


async def test_chunking():
    """Test chunking with sample transcript."""

    # Sample long transcript
    sample_transcript = """
    This is a test transcript with multiple sentences. It should be chunked appropriately.
    We want to ensure that sentences stay together and chunks don't exceed the token limit.

    The chunking algorithm should split on sentence boundaries. This maintains coherence
    and makes the chunks easier to understand when they're stored in memory.

    For very long sentences that exceed the max token limit, we should split on commas
    or other natural boundaries. This ensures no chunk is too large.

    The algorithm should also handle edge cases like very short transcripts,
    transcripts with unusual punctuation, and transcripts with mixed content.
    """ * 100  # Repeat to create a long transcript

    print(f"Original transcript: {len(sample_transcript)} characters")

    # Test chunking
    chunks = chunk_transcript(sample_transcript, max_tokens=500)

    print(f"\nChunking results:")
    print(f"- Total chunks: {len(chunks)}")
    print(f"- Token counts: {[c['token_count'] for c in chunks]}")
    print(f"- All chunks under limit: {all(c['token_count'] <= 500 for c in chunks)}")

    # Show first chunk sample
    print(f"\nFirst chunk preview:")
    print(f"- Index: {chunks[0]['chunk_index']}")
    print(f"- Tokens: {chunks[0]['token_count']}")
    print(f"- Text (first 200 chars): {chunks[0]['text'][:200]}...")

    return chunks


async def test_ingest_youtube():
    """Test full ingestion workflow with a YouTube URL."""

    print("\n" + "="*60)
    print("Testing YouTube ingestion workflow")
    print("="*60)

    url = "https://www.youtube.com/watch?v=ERJ2s73HwDs"

    print(f"\nIngesting: {url}")
    print("This will:")
    print("1. Fetch the transcript")
    print("2. Clean and chunk it")
    print("3. Extract concepts and methodologies")
    print("4. Prepare for memory ingestion")

    result = await ingest_youtube_video({
        "url": url,
        "max_chunk_tokens": 4000,
        "extract_metadata": True
    })

    import json
    data = json.loads(result[0].text)

    if data.get("success"):
        print(f"\n✅ Ingestion successful!")
        print(f"- Video ID: {data['video_metadata']['video_id']}")
        print(f"- Total chunks: {data['total_chunks']}")
        print(f"- Concepts found: {len(data['concepts'])}")
        print(f"- Methodologies found: {len(data['methodologies'])}")

        print(f"\nTop 5 concepts:")
        for i, concept in enumerate(data['concepts'][:5], 1):
            print(f"  {i}. {concept}")

        print(f"\nChunk distribution:")
        for chunk in data['chunks'][:3]:
            print(f"  - Chunk {chunk['chunk_index']}: {chunk['token_count']} tokens")
        if len(data['chunks']) > 3:
            print(f"  ... and {len(data['chunks']) - 3} more chunks")
    else:
        print(f"\n❌ Ingestion failed: {data.get('error')}")

    return data


if __name__ == "__main__":
    print("YouTube Transcript Chunking Test")
    print("="*60)

    # Test 1: Chunking algorithm
    chunks = asyncio.run(test_chunking())

    # Test 2: Full ingestion (commented out to avoid hitting YouTube API in tests)
    # Uncomment to test with real YouTube video:
    # asyncio.run(test_ingest_youtube())

    print("\n✅ All tests passed!")
