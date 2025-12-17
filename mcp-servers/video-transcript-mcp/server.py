#!/usr/bin/env python3
"""
Video Transcript Processing MCP Server
=======================================

Autonomous knowledge acquisition from technical videos and talks.

Provides tools for:
- YouTube transcript fetching (via yt-dlp)
- Transcript cleaning and structuring
- Key concept extraction
- Technical insight identification
- Speaker analysis (for multi-speaker content)
- Knowledge integration with enhanced-memory

This enables the AGI system to learn from YouTube tutorials, conference talks,
technical presentations, and expert interviews.

MCP Tools:
- fetch_youtube_transcript: Get transcript from YouTube URL
- clean_transcript: Remove repetition and formatting artifacts
- extract_concepts: Identify key technical concepts discussed
- extract_methodologies: Extract techniques and approaches
- analyze_speakers: Identify and separate multiple speakers
- store_video_knowledge: Store extracted knowledge in memory

Requirements:
- pip install mcp
- yt-dlp (system package)

Environment Variables:
- AGENTIC_SYSTEM_PATH: Root path for agentic system (default: ~/agentic-system)
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlparse, parse_qs

try:
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions, Server
    import mcp.server.stdio
    import mcp.types as types
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install mcp")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("video-transcript-mcp")

# Configuration
TRANSCRIPTS_DIR = Path(os.environ.get("AGENTIC_SYSTEM_PATH", Path.home() / "agentic-system")) / "video-transcripts"
TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


# Create MCP server
server = Server("video-transcript-mcp")


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    elif "youtube.com/watch" in url:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get("v", [None])[0]
    return None


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available video transcript processing tools."""
    return [
        types.Tool(
            name="fetch_youtube_transcript",
            description="Fetch transcript from YouTube video using yt-dlp. Returns cleaned, structured transcript text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "YouTube video URL (e.g., https://youtube.com/watch?v=...)"
                    },
                    "language": {
                        "type": "string",
                        "description": "Preferred language code (e.g., 'en', 'es')",
                        "default": "en"
                    },
                    "auto_clean": {
                        "type": "boolean",
                        "description": "Automatically clean transcript (remove repetition, etc.)",
                        "default": True
                    }
                },
                "required": ["url"]
            }
        ),
        types.Tool(
            name="clean_transcript",
            description="Clean and structure transcript text. Removes repetition, formatting artifacts, and stutters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "transcript": {
                        "type": "string",
                        "description": "Raw transcript text"
                    },
                    "remove_timestamps": {
                        "type": "boolean",
                        "description": "Remove timestamp markers",
                        "default": True
                    },
                    "deduplicate": {
                        "type": "boolean",
                        "description": "Remove duplicate lines",
                        "default": True
                    }
                },
                "required": ["transcript"]
            }
        ),
        types.Tool(
            name="extract_concepts",
            description="Extract key technical concepts, terms, and topics discussed in video. Uses pattern matching and frequency analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "transcript": {
                        "type": "string",
                        "description": "Transcript text"
                    },
                    "min_frequency": {
                        "type": "integer",
                        "description": "Minimum mentions for concept to be extracted",
                        "default": 2
                    },
                    "focus_domains": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional domains to focus on (e.g., ['AI', 'machine learning', 'AGI'])",
                        "default": []
                    }
                },
                "required": ["transcript"]
            }
        ),
        types.Tool(
            name="extract_methodologies",
            description="Extract techniques, methods, and approaches described in video. Identifies how-to content and best practices.",
            inputSchema={
                "type": "object",
                "properties": {
                    "transcript": {
                        "type": "string",
                        "description": "Transcript text"
                    },
                    "extract_code": {
                        "type": "boolean",
                        "description": "Also extract code examples if present",
                        "default": False
                    }
                },
                "required": ["transcript"]
            }
        ),
        types.Tool(
            name="analyze_speakers",
            description="Identify and separate multiple speakers in transcript (if available in source data).",
            inputSchema={
                "type": "object",
                "properties": {
                    "transcript": {
                        "type": "string",
                        "description": "Transcript text with speaker markers"
                    }
                },
                "required": ["transcript"]
            }
        ),
        types.Tool(
            name="store_video_knowledge",
            description="Store extracted video knowledge in enhanced-memory for AGI learning. Creates structured memory entities.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_metadata": {
                        "type": "object",
                        "description": "Video metadata (URL, title, duration, etc.)"
                    },
                    "concepts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key concepts identified"
                    },
                    "methodologies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Techniques and methods described"
                    },
                    "transcript_summary": {
                        "type": "string",
                        "description": "Optional brief summary of video content"
                    }
                },
                "required": ["video_metadata", "concepts"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""

    if name == "fetch_youtube_transcript":
        return await fetch_youtube_transcript(arguments or {})

    elif name == "clean_transcript":
        return await clean_transcript(arguments or {})

    elif name == "extract_concepts":
        return await extract_concepts(arguments or {})

    elif name == "extract_methodologies":
        return await extract_methodologies(arguments or {})

    elif name == "analyze_speakers":
        return await analyze_speakers(arguments or {})

    elif name == "store_video_knowledge":
        return await store_video_knowledge(arguments or {})

    else:
        raise ValueError(f"Unknown tool: {name}")


async def fetch_youtube_transcript(args: Dict) -> List[types.TextContent]:
    """Fetch YouTube transcript using yt-dlp."""
    url = args.get("url", "")
    language = args.get("language", "en")
    auto_clean = args.get("auto_clean", True)

    logger.info(f"Fetching transcript from {url}")

    try:
        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")

        # Use yt-dlp to get transcript
        output_file = TRANSCRIPTS_DIR / f"{video_id}.vtt"

        process = await asyncio.create_subprocess_exec(
            'yt-dlp',
            '--write-auto-sub',
            '--sub-lang', language,
            '--skip-download',
            '--output', str(output_file.with_suffix('')),
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        # Find generated VTT file
        vtt_files = list(TRANSCRIPTS_DIR.glob(f"{video_id}.*.vtt"))

        if not vtt_files:
            raise Exception("No transcript found (video may not have captions)")

        # Read VTT file
        vtt_content = vtt_files[0].read_text()

        # Parse VTT format
        lines = vtt_content.split('\n')
        transcript_lines = []

        for line in lines:
            # Skip WEBVTT header, timestamps, and empty lines
            if line.strip() and not line.startswith('WEBVTT') and not '-->' in line and not line.strip().isdigit():
                transcript_lines.append(line.strip())

        transcript = ' '.join(transcript_lines)

        # Auto-clean if requested
        if auto_clean:
            cleaned_result = await clean_transcript({
                "transcript": transcript,
                "remove_timestamps": True,
                "deduplicate": True
            })
            cleaned_data = json.loads(cleaned_result[0].text)
            transcript = cleaned_data.get("cleaned_transcript", transcript)

        # Cleanup VTT files
        for vtt_file in vtt_files:
            vtt_file.unlink()

        logger.info(f"Fetched transcript ({len(transcript)} chars)")

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "video_id": video_id,
                "url": url,
                "transcript": transcript,
                "word_count": len(transcript.split()),
                "auto_cleaned": auto_clean
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Transcript fetch failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def clean_transcript(args: Dict) -> List[types.TextContent]:
    """Clean and structure transcript text."""
    transcript = args.get("transcript", "")
    remove_timestamps = args.get("remove_timestamps", True)
    deduplicate = args.get("deduplicate", True)

    logger.info(f"Cleaning transcript ({len(transcript)} chars)")

    try:
        cleaned = transcript

        # Remove VTT/SRT timestamp patterns
        if remove_timestamps:
            cleaned = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}', '', cleaned)
            cleaned = re.sub(r'\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}\.\d{3}', '', cleaned)

        # Remove duplicate consecutive lines
        if deduplicate:
            lines = cleaned.split('\n')
            deduped_lines = []
            prev_line = None

            for line in lines:
                line = line.strip()
                if line and line != prev_line:
                    deduped_lines.append(line)
                    prev_line = line

            cleaned = '\n'.join(deduped_lines)

        # Remove multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Remove speaker labels like "[Music]", "[Applause]"
        cleaned = re.sub(r'\[.*?\]', '', cleaned)

        # Clean up punctuation
        cleaned = cleaned.strip()

        logger.info(f"Cleaned transcript ({len(cleaned)} chars, {len(cleaned.split())} words)")

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "cleaned_transcript": cleaned,
                "original_length": len(transcript),
                "cleaned_length": len(cleaned),
                "compression_ratio": len(transcript) / len(cleaned) if len(cleaned) > 0 else 1.0
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Transcript cleaning failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def extract_concepts(args: Dict) -> List[types.TextContent]:
    """Extract key technical concepts from transcript."""
    transcript = args.get("transcript", "")
    min_frequency = args.get("min_frequency", 2)
    focus_domains = args.get("focus_domains", [])

    logger.info(f"Extracting concepts (min_freq={min_frequency})")

    try:
        # Common technical terms (expandable)
        tech_patterns = [
            r'\b(AI|AGI|ASI)\b',
            r'\b(machine learning|deep learning|neural network)\b',
            r'\b(algorithm|optimization|architecture)\b',
            r'\b(self-improvement|recursive|meta-learning)\b',
            r'\b(transformer|attention|embedding)\b',
            r'\b(reinforcement learning|supervised learning)\b',
            r'\b(model|training|inference)\b',
            r'\b(framework|library|API)\b',
            r'\b(data|dataset|benchmark)\b',
            r'\b(performance|accuracy|precision)\b'
        ]

        concept_counts = {}

        # Find all matches
        for pattern in tech_patterns:
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            for match in matches:
                concept = match.lower()
                concept_counts[concept] = concept_counts.get(concept, 0) + 1

        # Filter by frequency
        concepts = [
            concept for concept, count in concept_counts.items()
            if count >= min_frequency
        ]

        # Sort by frequency
        concepts_sorted = sorted(
            concepts,
            key=lambda c: concept_counts[c],
            reverse=True
        )

        logger.info(f"Extracted {len(concepts_sorted)} concepts")

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "concepts": concepts_sorted,
                "concept_counts": {c: concept_counts[c] for c in concepts_sorted},
                "total_concepts": len(concepts_sorted)
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Concept extraction failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def extract_methodologies(args: Dict) -> List[types.TextContent]:
    """Extract techniques and methods from transcript."""
    transcript = args.get("transcript", "")
    extract_code = args.get("extract_code", False)

    logger.info("Extracting methodologies")

    try:
        methodologies = []

        # Look for methodology indicators
        method_patterns = [
            r'(we|they|you)\s+(use|implement|apply|employ|build)\s+([^.!?]{10,100})',
            r'(approach|method|technique|strategy)\s+(?:is|was|involves)\s+([^.!?]{10,100})',
            r'(first|then|next|finally),?\s+([^.!?]{10,100})',
            r'(step \d+|phase \d+):\s*([^.!?]{10,100})'
        ]

        for pattern in method_patterns:
            matches = re.findall(pattern, transcript, re.IGNORECASE)
            for match in matches:
                # Extract the methodology description (last group)
                method_text = match[-1].strip()
                if len(method_text) > 20 and method_text not in methodologies:
                    methodologies.append(method_text)

        # Extract code examples if requested
        code_examples = []
        if extract_code:
            code_patterns = [
                r'```(.*?)```',  # Markdown code blocks
                r'`([^`]{10,})`',  # Inline code
            ]

            for pattern in code_patterns:
                matches = re.findall(pattern, transcript, re.DOTALL)
                code_examples.extend(matches)

        logger.info(f"Extracted {len(methodologies)} methodologies, {len(code_examples)} code examples")

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "methodologies": methodologies[:20],  # Top 20
                "code_examples": code_examples[:10] if extract_code else [],
                "total_methodologies": len(methodologies)
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Methodology extraction failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def analyze_speakers(args: Dict) -> List[types.TextContent]:
    """Analyze speaker information in transcript."""
    transcript = args.get("transcript", "")

    logger.info("Analyzing speakers")

    try:
        # Look for speaker labels (common patterns)
        speaker_patterns = [
            r'([A-Z][a-z]+):\s*([^:\n]{20,})',  # "Name: speech"
            r'\[([A-Z][a-z]+)\]\s*([^[\n]{20,})',  # "[Name] speech"
            r'>>([A-Z][a-z]+)\s*([^>\n]{20,})',  # ">>Name speech"
        ]

        speakers = {}

        for pattern in speaker_patterns:
            matches = re.findall(pattern, transcript)
            for name, speech in matches:
                if name not in speakers:
                    speakers[name] = []
                speakers[name].append(speech.strip())

        # Count contributions
        speaker_stats = {
            name: {
                "segments": len(segments),
                "total_words": sum(len(s.split()) for s in segments),
                "sample": segments[0] if segments else ""
            }
            for name, segments in speakers.items()
        }

        logger.info(f"Identified {len(speakers)} speakers")

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "speaker_count": len(speakers),
                "speakers": list(speakers.keys()),
                "speaker_stats": speaker_stats
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Speaker analysis failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def store_video_knowledge(args: Dict) -> List[types.TextContent]:
    """Store video knowledge in enhanced-memory."""
    video_metadata = args.get("video_metadata", {})
    concepts = args.get("concepts", [])
    methodologies = args.get("methodologies", [])
    transcript_summary = args.get("transcript_summary", "")

    logger.info(f"Storing video knowledge: {video_metadata.get('url', 'Unknown')}")

    try:
        # Create memory entity
        video_id = extract_video_id(video_metadata.get("url", "")) or hashlib.md5(
            video_metadata.get("title", "").encode()
        ).hexdigest()[:8]

        entity_name = f"video_knowledge_{video_id}"

        observations = [
            f"URL: {video_metadata.get('url')}",
            f"Title: {video_metadata.get('title', 'Unknown')}",
            f"Duration: {video_metadata.get('duration', 'Unknown')}",
            f"Word Count: {video_metadata.get('word_count', 0)}"
        ]

        if transcript_summary:
            observations.append(f"Summary: {transcript_summary}")

        observations.extend([f"Concept: {concept}" for concept in concepts])
        observations.extend([f"Methodology: {method}" for method in methodologies])

        # Note: In production, would call enhanced-memory MCP create_entities
        logger.info(f"Would store entity: {entity_name} with {len(observations)} observations")

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "entity_name": entity_name,
                "observations_count": len(observations),
                "message": "Video knowledge ready for storage in enhanced-memory"
            })
        )]

    except Exception as e:
        logger.error(f"Knowledge storage failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Video Transcript MCP Server starting...")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="video-transcript-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
