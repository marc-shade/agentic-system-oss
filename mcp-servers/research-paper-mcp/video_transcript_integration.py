#!/usr/bin/env python3
"""
Video Transcript Integration Module
===================================

Integrates video-transcript-mcp tools into research-paper-mcp for knowledge consolidation.
This module provides YouTube transcript extraction and analysis capabilities.

Tools:
- fetch_youtube_transcript: Extract transcript from YouTube video
- clean_transcript: Clean and structure transcript text
- extract_concepts: Extract key technical concepts
- extract_methodologies: Extract techniques and methods
- analyze_speakers: Identify multiple speakers
- store_video_knowledge: Store in enhanced-memory

Dependencies:
- yt-dlp for transcript fetching
- enhanced-memory-mcp for knowledge storage
"""

import re
import json
import logging
import asyncio
import shutil
from typing import Dict, List, Any, Optional
from collections import Counter

from mcp.types import Tool, TextContent

logger = logging.getLogger("video-transcript-integration")

# Check for yt-dlp availability
YT_DLP_AVAILABLE = shutil.which("yt-dlp") is not None

# Tool definitions
VIDEO_TRANSCRIPT_TOOLS = [
    Tool(
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
    Tool(
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
    Tool(
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
    Tool(
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
    Tool(
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
    Tool(
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
                    "description": "Techniques and methods described",
                    "default": []
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


def get_video_transcript_tools() -> List[Tool]:
    """Return list of video transcript tools."""
    return VIDEO_TRANSCRIPT_TOOLS


async def fetch_youtube_transcript(
    url: str,
    language: str = "en",
    auto_clean: bool = True
) -> Dict[str, Any]:
    """
    Fetch transcript from YouTube video using yt-dlp.

    Args:
        url: YouTube video URL
        language: Preferred language code
        auto_clean: Whether to automatically clean the transcript

    Returns:
        Dict with transcript, metadata, and status
    """
    if not YT_DLP_AVAILABLE:
        return {
            "success": False,
            "error": "yt-dlp not installed. Install with: pip install yt-dlp"
        }

    try:
        # Fetch video info and subtitles using yt-dlp
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-sub",
            "--sub-lang", language,
            "--sub-format", "vtt",
            "--print", "%(title)s",
            "--print", "%(duration)s",
            "--print", "%(channel)s",
            url
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            # Try fetching just metadata
            logger.warning(f"Subtitle fetch failed: {stderr.decode()}")

        output_lines = stdout.decode().strip().split('\n')
        title = output_lines[0] if len(output_lines) > 0 else "Unknown"
        duration = output_lines[1] if len(output_lines) > 1 else "0"
        channel = output_lines[2] if len(output_lines) > 2 else "Unknown"

        # Now fetch the actual transcript
        transcript_cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-sub",
            "--sub-lang", language,
            "--sub-format", "vtt",
            "-o", "-",
            "--print-to-file", "%(subtitles)s", "-",
            url
        ]

        # Alternative: use youtube-transcript-api if available
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            # Extract video ID from URL
            video_id = None
            if "v=" in url:
                video_id = url.split("v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                video_id = url.split("youtu.be/")[1].split("?")[0]

            if video_id:
                transcript_list = YouTubeTranscriptApi.get_transcript(
                    video_id,
                    languages=[language, 'en']
                )

                # Combine transcript segments
                full_transcript = " ".join([
                    segment['text'] for segment in transcript_list
                ])

                if auto_clean:
                    full_transcript = clean_transcript_text(full_transcript)

                return {
                    "success": True,
                    "transcript": full_transcript,
                    "metadata": {
                        "title": title,
                        "duration_seconds": int(duration) if duration.isdigit() else 0,
                        "channel": channel,
                        "url": url,
                        "language": language,
                        "video_id": video_id
                    },
                    "segment_count": len(transcript_list)
                }
        except ImportError:
            logger.info("youtube-transcript-api not available, using yt-dlp only")
        except Exception as e:
            logger.warning(f"youtube-transcript-api failed: {e}")

        return {
            "success": False,
            "error": "Could not fetch transcript. Video may not have captions.",
            "metadata": {
                "title": title,
                "channel": channel,
                "url": url
            }
        }

    except Exception as e:
        logger.error(f"Error fetching transcript: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def clean_transcript_text(
    transcript: str,
    remove_timestamps: bool = True,
    deduplicate: bool = True
) -> str:
    """
    Clean and structure transcript text.

    Args:
        transcript: Raw transcript text
        remove_timestamps: Whether to remove timestamp markers
        deduplicate: Whether to remove duplicate lines

    Returns:
        Cleaned transcript string
    """
    text = transcript

    # Remove timestamp patterns like [00:00:00] or (00:00)
    if remove_timestamps:
        text = re.sub(r'\[?\d{1,2}:\d{2}(:\d{2})?\]?', '', text)
        text = re.sub(r'\(\d{1,2}:\d{2}(:\d{2})?\)', '', text)

    # Remove VTT formatting artifacts
    text = re.sub(r'WEBVTT\n', '', text)
    text = re.sub(r'Kind:.*\n', '', text)
    text = re.sub(r'Language:.*\n', '', text)
    text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*\n', '', text)

    # Remove HTML-like tags
    text = re.sub(r'<[^>]+>', '', text)

    # Remove music/sound effect markers
    text = re.sub(r'\[.*?(music|applause|laughter|sound).*?\]', '', text, flags=re.IGNORECASE)

    # Clean up stutters and repetitions
    text = re.sub(r'\b(\w+)( \1)+\b', r'\1', text)

    # Remove filler words patterns
    text = re.sub(r'\b(um|uh|er|ah|like,|you know,)\b', '', text, flags=re.IGNORECASE)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()

    # Deduplicate consecutive identical lines
    if deduplicate:
        lines = text.split('. ')
        seen = set()
        unique_lines = []
        for line in lines:
            line_clean = line.strip().lower()
            if line_clean and line_clean not in seen:
                seen.add(line_clean)
                unique_lines.append(line.strip())
        text = '. '.join(unique_lines)

    return text


async def clean_transcript(
    transcript: str,
    remove_timestamps: bool = True,
    deduplicate: bool = True
) -> Dict[str, Any]:
    """
    Clean and structure transcript text (async wrapper).

    Args:
        transcript: Raw transcript text
        remove_timestamps: Whether to remove timestamps
        deduplicate: Whether to remove duplicates

    Returns:
        Dict with cleaned transcript and stats
    """
    original_length = len(transcript)
    cleaned = clean_transcript_text(transcript, remove_timestamps, deduplicate)
    cleaned_length = len(cleaned)

    return {
        "success": True,
        "cleaned_transcript": cleaned,
        "original_length": original_length,
        "cleaned_length": cleaned_length,
        "reduction_percent": round((1 - cleaned_length / original_length) * 100, 1) if original_length > 0 else 0
    }


async def extract_concepts(
    transcript: str,
    min_frequency: int = 2,
    focus_domains: List[str] = None
) -> Dict[str, Any]:
    """
    Extract key technical concepts from transcript.

    Args:
        transcript: Transcript text
        min_frequency: Minimum mentions for inclusion
        focus_domains: Optional domains to prioritize

    Returns:
        Dict with extracted concepts and frequencies
    """
    focus_domains = focus_domains or []

    # Technical term patterns
    tech_patterns = [
        r'\b(?:AI|ML|AGI|LLM|GPT|CNN|RNN|LSTM|GAN|VAE)\b',
        r'\b(?:neural network|machine learning|deep learning|reinforcement learning)\b',
        r'\b(?:transformer|attention mechanism|embedding|tokenizer)\b',
        r'\b(?:API|SDK|CLI|REST|GraphQL|JSON|XML)\b',
        r'\b(?:Python|JavaScript|TypeScript|Rust|Go|Java)\b',
        r'\b(?:database|SQL|NoSQL|PostgreSQL|MongoDB|Redis)\b',
        r'\b(?:Docker|Kubernetes|container|microservice)\b',
        r'\b(?:algorithm|optimization|inference|training)\b',
    ]

    # Find all technical terms
    concepts = []
    for pattern in tech_patterns:
        matches = re.findall(pattern, transcript, re.IGNORECASE)
        concepts.extend([m.lower() for m in matches])

    # Extract capitalized terms (likely proper nouns/concepts)
    cap_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', transcript)
    concepts.extend([t.lower() for t in cap_terms])

    # Count frequencies
    concept_counts = Counter(concepts)

    # Filter by minimum frequency
    frequent_concepts = {
        concept: count
        for concept, count in concept_counts.items()
        if count >= min_frequency
    }

    # Boost concepts in focus domains
    if focus_domains:
        for concept in list(frequent_concepts.keys()):
            for domain in focus_domains:
                if domain.lower() in concept.lower():
                    frequent_concepts[concept] *= 2

    # Sort by frequency
    sorted_concepts = sorted(
        frequent_concepts.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return {
        "success": True,
        "concepts": [c[0] for c in sorted_concepts[:50]],
        "concept_frequencies": dict(sorted_concepts[:50]),
        "total_unique_concepts": len(frequent_concepts),
        "focus_domains": focus_domains
    }


async def extract_methodologies(
    transcript: str,
    extract_code: bool = False
) -> Dict[str, Any]:
    """
    Extract methodologies and techniques from transcript.

    Args:
        transcript: Transcript text
        extract_code: Whether to extract code examples

    Returns:
        Dict with methodologies and best practices
    """
    methodologies = []
    best_practices = []
    steps = []
    code_examples = []

    # Methodology indicators
    method_patterns = [
        r'(?:the )?(?:way|method|approach|technique|strategy) (?:to|for) ([^.]+)',
        r'(?:you can|we can|one can) ([^.]+)',
        r'(?:first|then|next|finally)[,]? ([^.]+)',
        r'(?:step \d+)[:\s]+([^.]+)',
        r'(?:the key is to|the trick is to|the secret is to) ([^.]+)',
    ]

    for pattern in method_patterns:
        matches = re.findall(pattern, transcript, re.IGNORECASE)
        methodologies.extend(matches[:10])

    # Best practice indicators
    practice_patterns = [
        r'(?:best practice|recommended|always|never|should|must)[:\s]+([^.]+)',
        r'(?:pro tip|tip)[:\s]+([^.]+)',
        r'(?:important(?:ly)?|note that|remember)[:\s]+([^.]+)',
    ]

    for pattern in practice_patterns:
        matches = re.findall(pattern, transcript, re.IGNORECASE)
        best_practices.extend(matches[:10])

    # Extract numbered steps
    step_pattern = r'(?:step )?(\d+)[:\.\)]\s*([^.]+)'
    step_matches = re.findall(step_pattern, transcript, re.IGNORECASE)
    steps = [f"Step {num}: {step.strip()}" for num, step in step_matches[:20]]

    # Extract code if requested
    if extract_code:
        code_patterns = [
            r'```[\w]*\n(.*?)```',
            r'`([^`]+)`',
        ]
        for pattern in code_patterns:
            matches = re.findall(pattern, transcript, re.DOTALL)
            code_examples.extend(matches[:10])

    return {
        "success": True,
        "methodologies": list(set(methodologies))[:20],
        "best_practices": list(set(best_practices))[:15],
        "steps": steps,
        "code_examples": code_examples if extract_code else [],
        "methodology_count": len(set(methodologies))
    }


async def analyze_speakers(transcript: str) -> Dict[str, Any]:
    """
    Analyze speakers in transcript.

    Args:
        transcript: Transcript with potential speaker markers

    Returns:
        Dict with speaker analysis
    """
    speakers = {}

    # Common speaker marker patterns
    speaker_patterns = [
        r'^([A-Z][A-Za-z\s]+):\s*(.+)$',  # "Speaker Name: text"
        r'^\[([^\]]+)\]\s*(.+)$',          # "[Speaker]: text"
        r'^>>>\s*([A-Z][A-Za-z\s]+)\s*(.+)$',  # ">>> Speaker text"
    ]

    lines = transcript.split('\n')
    current_speaker = "Unknown"

    for line in lines:
        for pattern in speaker_patterns:
            match = re.match(pattern, line.strip())
            if match:
                current_speaker = match.group(1).strip()
                text = match.group(2).strip()
                if current_speaker not in speakers:
                    speakers[current_speaker] = {
                        "line_count": 0,
                        "word_count": 0,
                        "sample_lines": []
                    }
                speakers[current_speaker]["line_count"] += 1
                speakers[current_speaker]["word_count"] += len(text.split())
                if len(speakers[current_speaker]["sample_lines"]) < 3:
                    speakers[current_speaker]["sample_lines"].append(text[:100])
                break

    # Calculate percentages
    total_words = sum(s["word_count"] for s in speakers.values())
    for speaker in speakers:
        if total_words > 0:
            speakers[speaker]["percentage"] = round(
                speakers[speaker]["word_count"] / total_words * 100, 1
            )
        else:
            speakers[speaker]["percentage"] = 0

    return {
        "success": True,
        "speakers": speakers,
        "speaker_count": len(speakers),
        "total_words": total_words,
        "has_multiple_speakers": len(speakers) > 1
    }


async def store_video_knowledge(
    video_metadata: Dict[str, Any],
    concepts: List[str],
    methodologies: List[str] = None,
    transcript_summary: str = None
) -> Dict[str, Any]:
    """
    Store video knowledge in enhanced-memory.

    Args:
        video_metadata: Video metadata (URL, title, etc.)
        concepts: Key concepts from video
        methodologies: Extracted methodologies
        transcript_summary: Summary of video content

    Returns:
        Dict with storage confirmation
    """
    methodologies = methodologies or []

    # Prepare entity for enhanced-memory
    entity = {
        "name": f"video_{video_metadata.get('video_id', 'unknown')}_{video_metadata.get('title', 'untitled')[:50]}",
        "entityType": "video_knowledge",
        "observations": [
            f"source_url: {video_metadata.get('url', 'unknown')}",
            f"title: {video_metadata.get('title', 'unknown')}",
            f"channel: {video_metadata.get('channel', 'unknown')}",
            f"duration: {video_metadata.get('duration_seconds', 0)} seconds",
            f"concepts: {', '.join(concepts[:20])}",
        ]
    }

    if methodologies:
        entity["observations"].append(f"methodologies: {', '.join(methodologies[:10])}")

    if transcript_summary:
        entity["observations"].append(f"summary: {transcript_summary[:500]}")

    # Try to store via enhanced-memory HTTP API
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:8101/api/entities",
                json={"entities": [entity]},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "success": True,
                        "stored": True,
                        "entity_name": entity["name"],
                        "concept_count": len(concepts),
                        "methodology_count": len(methodologies),
                        "storage_result": result
                    }
    except Exception as e:
        logger.warning(f"Could not store to enhanced-memory API: {e}")

    # Return success with entity details even if API unavailable
    return {
        "success": True,
        "stored": False,
        "entity": entity,
        "message": "Entity prepared but enhanced-memory API not available",
        "concept_count": len(concepts),
        "methodology_count": len(methodologies)
    }


async def handle_video_transcript_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """
    Handle video transcript tool calls.

    Args:
        name: Tool name
        arguments: Tool arguments

    Returns:
        List of TextContent with results
    """
    try:
        if name == "fetch_youtube_transcript":
            result = await fetch_youtube_transcript(
                url=arguments["url"],
                language=arguments.get("language", "en"),
                auto_clean=arguments.get("auto_clean", True)
            )
        elif name == "clean_transcript":
            result = await clean_transcript(
                transcript=arguments["transcript"],
                remove_timestamps=arguments.get("remove_timestamps", True),
                deduplicate=arguments.get("deduplicate", True)
            )
        elif name == "extract_concepts":
            result = await extract_concepts(
                transcript=arguments["transcript"],
                min_frequency=arguments.get("min_frequency", 2),
                focus_domains=arguments.get("focus_domains", [])
            )
        elif name == "extract_methodologies":
            result = await extract_methodologies(
                transcript=arguments["transcript"],
                extract_code=arguments.get("extract_code", False)
            )
        elif name == "analyze_speakers":
            result = await analyze_speakers(
                transcript=arguments["transcript"]
            )
        elif name == "store_video_knowledge":
            result = await store_video_knowledge(
                video_metadata=arguments["video_metadata"],
                concepts=arguments["concepts"],
                methodologies=arguments.get("methodologies", []),
                transcript_summary=arguments.get("transcript_summary")
            )
        else:
            result = {"error": f"Unknown video transcript tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        logger.error(f"Error in video transcript tool {name}: {e}")
        return [TextContent(type="text", text=json.dumps({
            "error": str(e),
            "tool": name
        }))]


# Module info
VIDEO_TRANSCRIPT_AVAILABLE = True
logger.info("✅ Video transcript integration loaded (6 tools: fetch, clean, extract_concepts, extract_methodologies, analyze_speakers, store)")
