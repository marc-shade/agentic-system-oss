#!/usr/bin/env python3
"""
YouTube Research Pipeline
=========================

Voice-driven autonomous knowledge acquisition from YouTube videos.
Integrates with video-transcript-mcp and enhanced-memory-mcp.

Usage:
    # Standalone
    python youtube_research_pipeline.py "transformer architecture"

    # As module
    from youtube_research_pipeline import research_topic
    result = await research_topic("AGI self-improvement")
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add MCP server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp-servers" / "video-transcript-mcp"))

try:
    from yt_search import search_youtube, get_video_metadata, VideoResult
except ImportError:
    # Fallback if import fails
    search_youtube = None
    VideoResult = None

logger = logging.getLogger("youtube-research-pipeline")


@dataclass
class ResearchResult:
    """Result from YouTube research pipeline."""
    topic: str
    video_url: str
    video_title: str
    channel: str
    concepts: List[str]
    methodologies: List[str]
    memory_entity_id: Optional[int]
    success: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "video_url": self.video_url,
            "video_title": self.video_title,
            "channel": self.channel,
            "concepts": self.concepts,
            "methodologies": self.methodologies,
            "memory_entity_id": self.memory_entity_id,
            "success": self.success,
            "error": self.error
        }


async def search_videos(topic: str, max_results: int = 5) -> List[Dict]:
    """Search YouTube for educational videos on topic."""
    if search_youtube is None:
        logger.error("yt_search module not available")
        return []

    try:
        results = await search_youtube(topic, max_results=max_results)
        videos = []
        for v in results:
            videos.append({
                "id": v.id,
                "title": v.title,
                "channel": v.channel,
                "url": v.url,
                "duration": v.duration,
                "duration_string": v.duration_string,
                "view_count": v.view_count
            })
        return videos
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


def select_best_video(videos: List[Dict]) -> Optional[Dict]:
    """Select best video based on quality heuristics."""
    if not videos:
        return None

    # Prioritize:
    # 1. High view count (>100K)
    # 2. Reasonable duration (5-20 min = 300-1200 sec)
    # 3. Known educational channels
    educational_channels = [
        "IBM Technology", "3Blue1Brown", "Two Minute Papers",
        "Yannic Kilcher", "AI Explained", "Lex Fridman",
        "Computerphile", "StatQuest", "sentdex"
    ]

    scored = []
    for v in videos:
        score = 0

        # View count bonus
        views = v.get("view_count") or 0
        if views > 1000000:
            score += 30
        elif views > 100000:
            score += 20
        elif views > 10000:
            score += 10

        # Duration preference (5-20 min ideal)
        duration = v.get("duration") or 0
        if 300 <= duration <= 1200:
            score += 20
        elif 180 <= duration <= 1800:
            score += 10

        # Educational channel bonus
        if any(ec.lower() in v.get("channel", "").lower() for ec in educational_channels):
            score += 25

        scored.append((score, v))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored else videos[0]


async def fetch_transcript(video_url: str) -> Optional[str]:
    """Fetch and clean transcript from video."""
    try:
        # Import youtube_transcript_api
        from youtube_transcript_api import YouTubeTranscriptApi

        # Extract video ID from URL
        video_id = video_url.split("v=")[-1].split("&")[0]

        # Get transcript
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

        # Combine into text
        text = " ".join([entry["text"] for entry in transcript_list])
        return text

    except Exception as e:
        logger.error(f"Transcript fetch failed: {e}")
        return None


def extract_concepts(transcript: str, focus_domains: List[str] = None) -> List[str]:
    """Extract key concepts from transcript."""
    if not transcript:
        return []

    # Simple keyword extraction
    focus_domains = focus_domains or ["AI", "machine learning", "neural networks"]

    # Technical terms to look for
    tech_terms = [
        "attention", "transformer", "encoder", "decoder", "embedding",
        "gradient", "backpropagation", "optimization", "loss function",
        "neural network", "deep learning", "reinforcement learning",
        "supervised", "unsupervised", "pre-training", "fine-tuning",
        "architecture", "model", "training", "inference", "parameters",
        "GPT", "BERT", "CNN", "RNN", "LSTM", "GAN", "diffusion",
        "self-attention", "cross-attention", "positional encoding"
    ]

    found = []
    transcript_lower = transcript.lower()

    for term in tech_terms:
        if term.lower() in transcript_lower:
            count = transcript_lower.count(term.lower())
            if count >= 2:  # Mentioned at least twice
                found.append(term)

    return found[:15]  # Top 15 concepts


def extract_methodologies(transcript: str) -> List[str]:
    """Extract methodologies and techniques from transcript."""
    if not transcript:
        return []

    methodologies = []
    sentences = transcript.replace(".", ".\n").split("\n")

    method_keywords = [
        "we use", "the approach", "the method", "technique",
        "algorithm", "process", "step", "procedure", "how to",
        "first", "then", "finally", "this allows", "this enables"
    ]

    for sentence in sentences:
        if any(kw in sentence.lower() for kw in method_keywords):
            if 20 < len(sentence) < 200:
                methodologies.append(sentence.strip())

    return methodologies[:10]


async def store_in_memory(
    topic: str,
    video: Dict,
    concepts: List[str],
    methodologies: List[str]
) -> Optional[int]:
    """Store research results in enhanced memory."""
    try:
        # Build observations
        observations = [
            f"Research topic: {topic}",
            f"Source: YouTube video - {video.get('title')}",
            f"Channel: {video.get('channel')}",
            f"Views: {video.get('view_count', 'unknown')}",
            f"URL: {video.get('url')}"
        ]

        observations.extend([f"Concept: {c}" for c in concepts])
        observations.extend([f"Methodology: {m[:100]}" for m in methodologies])

        # Create entity name from topic
        entity_name = f"youtube_research_{topic.lower().replace(' ', '_')[:30]}"

        # Try to store via MCP client (if available)
        # For now, return None - actual storage happens via MCP tools
        logger.info(f"Would store entity: {entity_name} with {len(observations)} observations")

        return None  # Placeholder - actual ID comes from MCP

    except Exception as e:
        logger.error(f"Memory storage failed: {e}")
        return None


async def research_topic(
    topic: str,
    max_videos: int = 5,
    focus_domains: List[str] = None,
    verbose: bool = True
) -> ResearchResult:
    """
    Complete YouTube research pipeline.

    Args:
        topic: Research topic to search for
        max_videos: Maximum videos to consider
        focus_domains: AI/ML domains to focus on
        verbose: Print progress updates

    Returns:
        ResearchResult with extracted knowledge
    """
    if verbose:
        print(f"Searching YouTube for: {topic}")

    # Step 1: Search
    videos = await search_videos(topic, max_videos)
    if not videos:
        return ResearchResult(
            topic=topic,
            video_url="",
            video_title="",
            channel="",
            concepts=[],
            methodologies=[],
            memory_entity_id=None,
            success=False,
            error="No videos found"
        )

    if verbose:
        print(f"Found {len(videos)} videos")

    # Step 2: Select best video
    video = select_best_video(videos)
    if verbose:
        print(f"Selected: {video['title']} by {video['channel']}")

    # Step 3: Fetch transcript
    transcript = await fetch_transcript(video["url"])
    if not transcript:
        return ResearchResult(
            topic=topic,
            video_url=video["url"],
            video_title=video["title"],
            channel=video["channel"],
            concepts=[],
            methodologies=[],
            memory_entity_id=None,
            success=False,
            error="Could not fetch transcript"
        )

    if verbose:
        print(f"Got transcript ({len(transcript)} chars)")

    # Step 4: Extract concepts
    concepts = extract_concepts(transcript, focus_domains)
    methodologies = extract_methodologies(transcript)

    if verbose:
        print(f"Extracted {len(concepts)} concepts, {len(methodologies)} methodologies")

    # Step 5: Store in memory
    entity_id = await store_in_memory(topic, video, concepts, methodologies)

    return ResearchResult(
        topic=topic,
        video_url=video["url"],
        video_title=video["title"],
        channel=video["channel"],
        concepts=concepts,
        methodologies=methodologies,
        memory_entity_id=entity_id,
        success=True
    )


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="YouTube Research Pipeline")
    parser.add_argument("topic", help="Research topic")
    parser.add_argument("--max-videos", type=int, default=5, help="Max videos to search")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    result = await research_topic(args.topic, max_videos=args.max_videos)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        if result.success:
            print(f"\n=== Research Complete ===")
            print(f"Video: {result.video_title}")
            print(f"Channel: {result.channel}")
            print(f"URL: {result.video_url}")
            print(f"\nKey Concepts: {', '.join(result.concepts[:5])}")
            if result.methodologies:
                print(f"\nMethodologies found: {len(result.methodologies)}")
        else:
            print(f"Research failed: {result.error}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
