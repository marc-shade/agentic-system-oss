#!/usr/bin/env python3
"""
Example: YouTube Video Research Workflow for Recursive Self-Improving AI
=========================================================================

Demonstrates complete workflow from video URL to knowledge storage.

Prerequisites:
- video-transcript-mcp server configured and running
- enhanced-memory-mcp server configured and running
- yt-dlp installed (brew install yt-dlp)

Usage:
    python3 video_research_example.py --url "https://youtube.com/watch?v=VIDEO_ID"
    python3 video_research_example.py --batch urls.txt
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def process_video(video_url: str) -> Dict[str, Any]:
    """
    Process a single YouTube video through the complete workflow.

    This is a reference implementation showing the tool call sequence.
    In Claude Code, you would call these MCP tools directly.

    Returns:
        Dictionary with extracted knowledge
    """

    print(f"Processing: {video_url}")

    # Step 1: Fetch transcript
    print("  [1/5] Fetching transcript...")
    # MCP call: mcp__video-transcript-mcp__fetch_youtube_transcript
    transcript_result = {
        "success": True,
        "video_id": "example_id",
        "url": video_url,
        "transcript": "Example transcript content...",
        "word_count": 1000
    }

    if not transcript_result["success"]:
        print(f"  ❌ Failed to fetch transcript: {transcript_result.get('error')}")
        return {}

    print(f"  ✅ Fetched {transcript_result['word_count']} words")

    # Step 2: Extract concepts
    print("  [2/5] Extracting technical concepts...")
    # MCP call: mcp__video-transcript-mcp__extract_concepts
    concepts_result = {
        "success": True,
        "concepts": [
            "recursive self-improvement",
            "meta-learning",
            "neural architecture search",
            "autonomous agents",
            "code generation"
        ],
        "concept_counts": {
            "recursive self-improvement": 15,
            "meta-learning": 12,
            "neural architecture search": 8,
            "autonomous agents": 6,
            "code generation": 5
        }
    }

    print(f"  ✅ Extracted {len(concepts_result['concepts'])} concepts")

    # Step 3: Extract methodologies
    print("  [3/5] Extracting implementation methods...")
    # MCP call: mcp__video-transcript-mcp__extract_methodologies
    methods_result = {
        "success": True,
        "methodologies": [
            "use gradient-based optimization for architecture search",
            "implement recursive self-evaluation with rollback capability",
            "apply meta-learning for few-shot adaptation",
            "employ sandboxed execution for code generation safety"
        ],
        "code_examples": [
            "def recursive_improve(model, data):",
            "class MetaLearner(nn.Module):"
        ]
    }

    print(f"  ✅ Extracted {len(methods_result['methodologies'])} methodologies")

    # Step 4: Analyze production-readiness
    print("  [4/5] Analyzing implementation patterns...")

    production_indicators = {
        "has_code_examples": len(methods_result.get("code_examples", [])) > 0,
        "has_github_refs": False,  # Would scan transcript for github.com links
        "has_metrics": False,  # Would scan for performance numbers
        "has_deployment_info": False  # Would scan for production keywords
    }

    readiness_score = sum(production_indicators.values()) / len(production_indicators)

    if readiness_score >= 0.5:
        print(f"  ✅ Production-ready ({readiness_score:.0%})")
    else:
        print(f"  ⚠️  Research-only ({readiness_score:.0%})")

    # Step 5: Store in enhanced-memory
    print("  [5/5] Storing knowledge...")
    # MCP call: mcp__video-transcript-mcp__store_video_knowledge
    storage_result = {
        "success": True,
        "entity_name": f"video_knowledge_{transcript_result['video_id']}",
        "observations_count": 10 + len(concepts_result["concepts"]) + len(methods_result["methodologies"])
    }

    print(f"  ✅ Stored {storage_result['observations_count']} observations")

    return {
        "video_url": video_url,
        "video_id": transcript_result["video_id"],
        "word_count": transcript_result["word_count"],
        "concepts": concepts_result["concepts"],
        "methodologies": methods_result["methodologies"],
        "code_examples": methods_result.get("code_examples", []),
        "production_readiness": readiness_score,
        "entity_name": storage_result["entity_name"]
    }


def batch_process_videos(video_urls: List[str]) -> Dict[str, Any]:
    """Process multiple videos and generate summary report."""

    print(f"\n{'='*80}")
    print(f"Batch Processing: {len(video_urls)} videos")
    print(f"{'='*80}\n")

    results = []
    all_concepts = {}
    all_methodologies = []
    production_ready = []

    for i, url in enumerate(video_urls, 1):
        print(f"\n[Video {i}/{len(video_urls)}]")
        result = process_video(url)

        if result:
            results.append(result)

            # Aggregate concepts
            for concept in result.get("concepts", []):
                all_concepts[concept] = all_concepts.get(concept, 0) + 1

            # Aggregate methodologies
            all_methodologies.extend(result.get("methodologies", []))

            # Track production-ready content
            if result.get("production_readiness", 0) >= 0.5:
                production_ready.append(result)

    # Generate summary
    print(f"\n{'='*80}")
    print("SUMMARY REPORT")
    print(f"{'='*80}\n")

    print(f"Total videos processed: {len(results)}")
    print(f"Total words extracted: {sum(r.get('word_count', 0) for r in results):,}")
    print(f"Production-ready content: {len(production_ready)} ({len(production_ready)/len(results)*100:.0%})")

    print(f"\nTop 10 Concepts (by frequency):")
    sorted_concepts = sorted(all_concepts.items(), key=lambda x: x[1], reverse=True)
    for concept, count in sorted_concepts[:10]:
        print(f"  - {concept}: {count} mentions")

    print(f"\nUnique Implementation Patterns: {len(set(all_methodologies))}")

    print(f"\nProduction-Ready Videos:")
    for video in production_ready:
        print(f"  - {video['video_url']} ({video['production_readiness']:.0%})")

    return {
        "total_videos": len(results),
        "total_words": sum(r.get("word_count", 0) for r in results),
        "concepts": all_concepts,
        "methodologies": list(set(all_methodologies)),
        "production_ready": production_ready,
        "results": results
    }


def main():
    parser = argparse.ArgumentParser(
        description="Process YouTube videos for recursive AI research"
    )
    parser.add_argument(
        "--url",
        help="Single YouTube video URL"
    )
    parser.add_argument(
        "--batch",
        help="File containing video URLs (one per line)"
    )
    parser.add_argument(
        "--output",
        default="video_research_results.json",
        help="Output JSON file for results"
    )

    args = parser.parse_args()

    if not args.url and not args.batch:
        parser.print_help()
        sys.exit(1)

    # Collect video URLs
    video_urls = []

    if args.url:
        video_urls.append(args.url)

    if args.batch:
        batch_file = Path(args.batch)
        if not batch_file.exists():
            print(f"Error: Batch file not found: {args.batch}")
            sys.exit(1)

        with open(batch_file) as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            video_urls.extend(urls)

    # Process videos
    if len(video_urls) == 1:
        result = process_video(video_urls[0])
        summary = {"results": [result]}
    else:
        summary = batch_process_videos(video_urls)

    # Save results
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n✅ Results saved to: {output_path}")
    print("\nNext steps:")
    print("  1. Review extracted concepts and methodologies")
    print("  2. Verify production-readiness flags")
    print("  3. Explore GitHub repositories mentioned in transcripts")
    print("  4. Integrate patterns into autonomous system architecture")


if __name__ == "__main__":
    main()


# Example usage commands:
#
# Single video:
# python3 video_research_example.py --url "https://youtube.com/watch?v=kCc8FmEb1nY"
#
# Batch processing:
# echo "https://youtube.com/watch?v=VIDEO_1" > urls.txt
# echo "https://youtube.com/watch?v=VIDEO_2" >> urls.txt
# echo "https://youtube.com/watch?v=VIDEO_3" >> urls.txt
# python3 video_research_example.py --batch urls.txt
#
# In Claude Code, you would use MCP tools directly:
#
# result = mcp__video-transcript-mcp__fetch_youtube_transcript({
#     "url": "https://youtube.com/watch?v=VIDEO_ID",
#     "auto_clean": True
# })
#
# concepts = mcp__video-transcript-mcp__extract_concepts({
#     "transcript": result["transcript"],
#     "focus_domains": ["recursive", "self-improvement", "AGI"]
# })
#
# methods = mcp__video-transcript-mcp__extract_methodologies({
#     "transcript": result["transcript"],
#     "extract_code": True
# })
#
# mcp__video-transcript-mcp__store_video_knowledge({
#     "video_metadata": {
#         "url": result["url"],
#         "title": "Video Title",
#         "word_count": result["word_count"]
#     },
#     "concepts": concepts["concepts"],
#     "methodologies": methods["methodologies"]
# })
