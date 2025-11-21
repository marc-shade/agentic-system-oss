#!/usr/bin/env python3
"""
CLI wrapper for video-transcript-mcp server
Allows direct command-line searches for use by AGI loop
"""

import argparse
import json
import sys
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent))

# For now, return empty results since YouTube search requires API key
# In production, would use youtube-transcript-api + Google API


def search_youtube(query: str, max_results: int = 3):
    """Search YouTube for videos (placeholder)"""
    # YouTube search requires API key which may not be configured
    # Return empty results for now - AGI loop will fall back to papers
    return []


def main():
    parser = argparse.ArgumentParser(description="Search YouTube for videos")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--max-results", type=int, default=3, help="Maximum number of results")

    args = parser.parse_args()

    # Run search
    results = search_youtube(args.query, args.max_results)

    # Output JSON to stdout
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
