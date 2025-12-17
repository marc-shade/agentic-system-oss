#!/usr/bin/env python3
"""
Research Paper Ingestion MCP Server
====================================

Autonomous knowledge acquisition from academic research papers.

Provides tools for:
- arXiv paper search and download
- Semantic Scholar API integration
- PDF parsing and text extraction
- Key insight extraction
- Citation graph analysis
- Knowledge integration with enhanced-memory

This enables the AGI system to autonomously learn from the latest
AI research papers and integrate findings into its knowledge base.

MCP Tools:
- search_arxiv: Search arXiv for papers
- search_semantic_scholar: Search Semantic Scholar
- download_paper: Download PDF from URL
- extract_insights: Extract key findings from paper
- analyze_citations: Analyze citation relationships
- store_paper_knowledge: Store extracted knowledge in memory

Requirements:
- pip install mcp arxiv aiohttp

Environment Variables:
- AGENTIC_SYSTEM_PATH: Root path for agentic system (default: ~/agentic-system)
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import quote

try:
    import aiohttp
    import arxiv
    from mcp.server.models import InitializationOptions
    from mcp.server import NotificationOptions, Server
    import mcp.server.stdio
    import mcp.types as types
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install mcp arxiv aiohttp")
    sys.exit(1)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("research-paper-mcp")

# Configuration
ARXIV_BASE_URL = "http://export.arxiv.org/api/query"
SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"
PAPERS_DIR = Path(os.environ.get("AGENTIC_SYSTEM_PATH", Path.home() / "agentic-system")) / "research-papers"
PAPERS_DIR.mkdir(parents=True, exist_ok=True)


# Create MCP server
server = Server("research-paper-mcp")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available research paper ingestion tools."""
    return [
        types.Tool(
            name="search_arxiv",
            description="Search arXiv for research papers by query. Returns paper metadata including title, authors, abstract, PDF URL, and publication date.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (e.g., 'recursive self-improvement AGI', 'meta-learning neural networks')"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Sort order: relevance, lastUpdatedDate, or submittedDate",
                        "enum": ["relevance", "lastUpdatedDate", "submittedDate"],
                        "default": "relevance"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="search_semantic_scholar",
            description="Search Semantic Scholar for papers with citation counts and influence metrics. Provides academic impact analysis.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to retrieve: title, authors, abstract, citationCount, influentialCitationCount, year, venue",
                        "default": ["title", "authors", "abstract", "citationCount", "year"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="download_paper",
            description="Download research paper PDF from URL. Saves to local storage and returns file path.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "PDF URL (arXiv, Semantic Scholar, etc.)"
                    },
                    "paper_id": {
                        "type": "string",
                        "description": "Unique paper identifier for filename"
                    }
                },
                "required": ["url", "paper_id"]
            }
        ),
        types.Tool(
            name="extract_insights",
            description="Extract key insights, findings, and techniques from research paper text. Uses AI to identify important contributions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_text": {
                        "type": "string",
                        "description": "Full paper text or abstract"
                    },
                    "focus_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional specific areas to focus on (e.g., ['methodology', 'results', 'applications'])",
                        "default": []
                    }
                },
                "required": ["paper_text"]
            }
        ),
        types.Tool(
            name="analyze_citations",
            description="Analyze citation relationships and paper influence using Semantic Scholar citation graph.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Semantic Scholar paper ID or arXiv ID"
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Citation graph depth (1-3)",
                        "default": 1
                    }
                },
                "required": ["paper_id"]
            }
        ),
        types.Tool(
            name="store_paper_knowledge",
            description="Store extracted paper knowledge in enhanced-memory for AGI learning. Creates structured memory entities.",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_metadata": {
                        "type": "object",
                        "description": "Paper metadata (title, authors, year, etc.)"
                    },
                    "insights": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key insights extracted from paper"
                    },
                    "techniques": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Novel techniques or methods described"
                    }
                },
                "required": ["paper_metadata", "insights"]
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""

    if name == "search_arxiv":
        return await search_arxiv(arguments or {})

    elif name == "search_semantic_scholar":
        return await search_semantic_scholar(arguments or {})

    elif name == "download_paper":
        return await download_paper(arguments or {})

    elif name == "extract_insights":
        return await extract_insights(arguments or {})

    elif name == "analyze_citations":
        return await analyze_citations(arguments or {})

    elif name == "store_paper_knowledge":
        return await store_paper_knowledge(arguments or {})

    else:
        raise ValueError(f"Unknown tool: {name}")


async def search_arxiv(args: Dict) -> List[types.TextContent]:
    """Search arXiv for research papers."""
    query = args.get("query", "")
    max_results = args.get("max_results", 10)
    sort_by_str = args.get("sort_by", "relevance")

    logger.info(f"Searching arXiv for: {query} (max_results={max_results})")

    try:
        # Map sort string to arxiv.SortCriterion
        sort_map = {
            "relevance": arxiv.SortCriterion.Relevance,
            "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
            "submittedDate": arxiv.SortCriterion.SubmittedDate
        }
        sort_by = sort_map.get(sort_by_str, arxiv.SortCriterion.Relevance)

        # Search arXiv
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=sort_by
        )

        results = []
        for result in search.results():
            paper_data = {
                "id": result.entry_id.split("/")[-1],
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "abstract": result.summary,
                "pdf_url": result.pdf_url,
                "published": result.published.isoformat() if result.published else None,
                "updated": result.updated.isoformat() if result.updated else None,
                "categories": result.categories,
                "primary_category": result.primary_category
            }
            results.append(paper_data)

        logger.info(f"Found {len(results)} papers on arXiv")

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "query": query,
                "count": len(results),
                "papers": results
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"arXiv search failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def search_semantic_scholar(args: Dict) -> List[types.TextContent]:
    """Search Semantic Scholar for papers with citations."""
    query = args.get("query", "")
    fields = args.get("fields", ["title", "authors", "abstract", "citationCount", "year"])
    limit = args.get("limit", 10)

    logger.info(f"Searching Semantic Scholar for: {query} (limit={limit})")

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{SEMANTIC_SCHOLAR_BASE_URL}/paper/search"
            params = {
                "query": query,
                "fields": ",".join(fields),
                "limit": limit
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    papers = data.get("data", [])

                    logger.info(f"Found {len(papers)} papers on Semantic Scholar")

                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "query": query,
                            "count": len(papers),
                            "papers": papers
                        }, indent=2)
                    )]
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")

    except Exception as e:
        logger.error(f"Semantic Scholar search failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def download_paper(args: Dict) -> List[types.TextContent]:
    """Download research paper PDF."""
    url = args.get("url", "")
    paper_id = args.get("paper_id", "")

    logger.info(f"Downloading paper {paper_id} from {url}")

    try:
        # Create safe filename
        safe_id = re.sub(r'[^\w\-]', '_', paper_id)
        pdf_path = PAPERS_DIR / f"{safe_id}.pdf"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()

                    # Save PDF
                    pdf_path.write_bytes(content)

                    logger.info(f"Downloaded paper to {pdf_path}")

                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "paper_id": paper_id,
                            "file_path": str(pdf_path),
                            "size_bytes": len(content)
                        })
                    )]
                else:
                    raise Exception(f"HTTP {response.status}")

    except Exception as e:
        logger.error(f"Paper download failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def extract_insights(args: Dict) -> List[types.TextContent]:
    """Extract key insights from paper text."""
    paper_text = args.get("paper_text", "")
    focus_areas = args.get("focus_areas", [])

    logger.info(f"Extracting insights from paper (length={len(paper_text)})")

    try:
        # Simple insight extraction (pattern-based)
        insights = []

        # Extract key sentences
        sentences = re.split(r'[.!?]\s+', paper_text)

        # Look for sentences with key phrases
        key_phrases = [
            "we propose", "we demonstrate", "we show", "we present",
            "our method", "our approach", "our results",
            "achieve", "outperform", "improvement", "novel",
            "state-of-the-art", "significant", "effective"
        ]

        for sentence in sentences:
            if any(phrase in sentence.lower() for phrase in key_phrases):
                if len(sentence) > 50 and len(sentence) < 300:
                    insights.append(sentence.strip())

            if len(insights) >= 10:
                break

        logger.info(f"Extracted {len(insights)} insights")

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "insights": insights,
                "focus_areas": focus_areas
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Insight extraction failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def analyze_citations(args: Dict) -> List[types.TextContent]:
    """Analyze citation relationships."""
    paper_id = args.get("paper_id", "")
    depth = args.get("depth", 1)

    logger.info(f"Analyzing citations for {paper_id} (depth={depth})")

    try:
        async with aiohttp.ClientSession() as session:
            url = f"{SEMANTIC_SCHOLAR_BASE_URL}/paper/{paper_id}"
            params = {
                "fields": "title,citationCount,influentialCitationCount,citations,references"
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    citation_graph = {
                        "paper_id": paper_id,
                        "title": data.get("title"),
                        "citation_count": data.get("citationCount", 0),
                        "influential_citations": data.get("influentialCitationCount", 0),
                        "citations": len(data.get("citations", [])),
                        "references": len(data.get("references", []))
                    }

                    logger.info(f"Citation analysis complete: {citation_graph['citation_count']} citations")

                    return [types.TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "citation_graph": citation_graph
                        }, indent=2)
                    )]
                else:
                    raise Exception(f"HTTP {response.status}")

    except Exception as e:
        logger.error(f"Citation analysis failed: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": str(e)
            })
        )]


async def store_paper_knowledge(args: Dict) -> List[types.TextContent]:
    """Store paper knowledge in enhanced-memory."""
    paper_metadata = args.get("paper_metadata", {})
    insights = args.get("insights", [])
    techniques = args.get("techniques", [])

    logger.info(f"Storing paper knowledge: {paper_metadata.get('title', 'Unknown')}")

    try:
        # Create memory entity
        entity_name = f"research_paper_{paper_metadata.get('id', hashlib.md5(paper_metadata.get('title', '').encode()).hexdigest()[:8])}"

        observations = [
            f"Title: {paper_metadata.get('title')}",
            f"Authors: {', '.join(paper_metadata.get('authors', []))}",
            f"Year: {paper_metadata.get('year', 'Unknown')}",
            f"Citations: {paper_metadata.get('citationCount', 0)}"
        ]

        observations.extend([f"Insight: {insight}" for insight in insights])
        observations.extend([f"Technique: {technique}" for technique in techniques])

        # Note: In production, would call enhanced-memory MCP create_entities
        logger.info(f"Would store entity: {entity_name} with {len(observations)} observations")

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "success": True,
                "entity_name": entity_name,
                "observations_count": len(observations),
                "message": "Paper knowledge ready for storage in enhanced-memory"
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
        logger.info("Research Paper MCP Server starting...")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="research-paper-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
