#!/usr/bin/env python3
"""
CLI wrapper for research-paper-mcp server
Allows direct command-line searches for use by AGI loop
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import MCP server functions
try:
    import arxiv
except ImportError:
    print(json.dumps({"error": "arxiv library not installed"}), file=sys.stderr)
    sys.exit(1)


async def search_arxiv(query: str, max_results: int = 5):
    """Search arXiv for papers"""
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        papers = []
        for result in search.results():
            paper = {
                "id": result.entry_id,
                "title": result.title,
                "abstract": result.summary,
                "authors": [author.name for author in result.authors],
                "published": result.published.isoformat() if result.published else None,
                "pdf_url": result.pdf_url,
                "categories": result.categories,
                "citations": 0,  # arXiv API doesn't provide citation count
                "concepts": [],  # Would need NLP to extract
                "techniques": [],  # Would need NLP to extract
                "insights": [result.summary[:200]]  # First 200 chars as preview
            }
            papers.append(paper)

        return papers
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return []


def main():
    parser = argparse.ArgumentParser(description="Search arXiv for research papers")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--max-results", type=int, default=5, help="Maximum number of results")

    args = parser.parse_args()

    # Run async search
    results = asyncio.run(search_arxiv(args.query, args.max_results))

    # Output JSON to stdout
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
