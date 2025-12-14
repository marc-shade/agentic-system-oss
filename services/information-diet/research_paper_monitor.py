#!/usr/bin/env python3
"""
Research Paper Monitor - Information Diet System
Watches arXiv and Semantic Scholar for AGI-relevant papers.
Leverages existing research-paper-mcp server.

Usage:
    python3 research_paper_monitor.py                    # Check once
    python3 research_paper_monitor.py --daemon           # Run continuously
    python3 research_paper_monitor.py --query "topic"    # Custom search
"""
import platform

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

try:
    import httpx
except ImportError:
    os.system("pip3 install httpx")
    import httpx

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("research_paper_monitor")

# Configuration
AGENTIC_PATH = Path(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
CONFIG_FILE = AGENTIC_PATH / "config" / "research-paper-topics.json"
STATE_FILE = AGENTIC_PATH / "databases" / "research-paper-state.json"

# Default topics to monitor
DEFAULT_TOPICS = [
    {
        "query": "artificial general intelligence self-improvement",
        "category": "agi",
        "priority": "high"
    },
    {
        "query": "large language model reasoning",
        "category": "llm",
        "priority": "high"
    },
    {
        "query": "neural memory systems retrieval augmented generation",
        "category": "memory",
        "priority": "high"
    },
    {
        "query": "multi-agent systems coordination",
        "category": "agents",
        "priority": "medium"
    },
    {
        "query": "meta-learning self-supervised",
        "category": "meta-learning",
        "priority": "medium"
    }
]


def load_config() -> Dict:
    """Load research topics configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"topics": DEFAULT_TOPICS, "max_papers_per_topic": 5}


def save_default_config():
    """Save default configuration."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "topics": DEFAULT_TOPICS,
                "max_papers_per_topic": 5,
                "check_interval_hours": 6
            }, f, indent=2)
        logger.info(f"Created config at {CONFIG_FILE}")


def load_state() -> Dict:
    """Load processing state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"seen_papers": {}, "last_run": None}


def save_state(state: Dict):
    """Save processing state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


async def search_arxiv(query: str, max_results: int = 5) -> List[Dict]:
    """Search arXiv for papers."""
    try:
        # Use research-paper-mcp if available
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8105/search_arxiv",
                json={"query": query, "max_results": max_results}
            )
            if response.status_code == 200:
                return response.json().get("papers", [])
    except Exception as e:
        logger.debug(f"MCP unavailable: {e}")

    # Direct arXiv API fallback
    try:
        import urllib.parse
        encoded_query = urllib.parse.quote(query)
        url = f"https://export.arxiv.org/api/query?search_query=all:{encoded_query}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 200:
                # Parse Atom feed
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.text)
                ns = {'atom': 'http://www.w3.org/2005/Atom'}

                papers = []
                for entry in root.findall('atom:entry', ns):
                    paper = {
                        "id": entry.find('atom:id', ns).text if entry.find('atom:id', ns) is not None else "",
                        "title": entry.find('atom:title', ns).text.strip() if entry.find('atom:title', ns) is not None else "",
                        "abstract": entry.find('atom:summary', ns).text.strip() if entry.find('atom:summary', ns) is not None else "",
                        "authors": [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns) if a.find('atom:name', ns) is not None],
                        "published": entry.find('atom:published', ns).text if entry.find('atom:published', ns) is not None else "",
                        "pdf_url": next((l.get('href') for l in entry.findall('atom:link', ns) if l.get('title') == 'pdf'), "")
                    }
                    papers.append(paper)
                return papers
    except Exception as e:
        logger.error(f"arXiv search failed: {e}")

    return []


async def store_paper_in_memory(paper: Dict, topic: Dict):
    """Store paper in enhanced memory."""
    content = f"""Research Paper Discovery:
Title: {paper.get('title', 'Unknown')}
Authors: {', '.join(paper.get('authors', [])[:3])}
Published: {paper.get('published', 'Unknown')[:10]}
Topic Category: {topic.get('category', 'general')}
Priority: {topic.get('priority', 'medium')}

Abstract:
{paper.get('abstract', '')[:1000]}

PDF: {paper.get('pdf_url', 'N/A')}
arXiv ID: {paper.get('id', 'N/A')}"""

    # Try MCP storage
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8101/nmf/remember",
                json={
                    "content": content,
                    "agent_id": "research-monitor",
                    "tags": ["research-paper", topic.get('category', 'general'), "arxiv"],
                    "metadata": {
                        "source": "arxiv",
                        "paper_id": paper.get('id', ''),
                        "title": paper.get('title', ''),
                        "priority": topic.get('priority', 'medium')
                    }
                }
            )
            if response.status_code == 200:
                logger.info(f"Stored paper: {paper.get('title', '')[:50]}...")
                return True
    except Exception as e:
        logger.debug(f"MCP storage failed: {e}")

    # Fallback to local file
    fallback_file = STATE_FILE.parent / "pending_papers.jsonl"
    with open(fallback_file, "a") as f:
        f.write(json.dumps({
            "content": content,
            "tags": ["research-paper", topic.get('category', 'general')],
            "timestamp": datetime.now().isoformat()
        }) + "\n")
    logger.info(f"Queued paper: {paper.get('title', '')[:50]}...")
    return True


async def process_topic(topic: Dict, state: Dict, max_papers: int) -> int:
    """Process a single research topic."""
    query = topic["query"]
    logger.info(f"Searching for: {query}")

    papers = await search_arxiv(query, max_papers)
    if not papers:
        return 0

    new_count = 0
    seen = state.get("seen_papers", {})

    for paper in papers:
        paper_id = hashlib.sha256(paper.get("id", "").encode()).hexdigest()[:16]

        if paper_id in seen:
            continue

        await store_paper_in_memory(paper, topic)

        seen[paper_id] = {
            "title": paper.get("title", ""),
            "timestamp": datetime.now().isoformat()
        }
        new_count += 1

    state["seen_papers"] = seen
    return new_count


async def check_all_topics():
    """Check all configured topics."""
    save_default_config()
    config = load_config()
    state = load_state()

    topics = config.get("topics", DEFAULT_TOPICS)
    max_papers = config.get("max_papers_per_topic", 5)

    total_new = 0
    for topic in topics:
        try:
            count = await process_topic(topic, state, max_papers)
            total_new += count
            await asyncio.sleep(1)  # Rate limiting
        except Exception as e:
            logger.error(f"Error processing {topic['query']}: {e}")

    save_state(state)
    logger.info(f"Checked {len(topics)} topics, found {total_new} new papers")
    return total_new


async def daemon_loop(interval_hours: int = 6):
    """Run continuously."""
    logger.info(f"Starting daemon, checking every {interval_hours} hours")

    while True:
        try:
            await check_all_topics()
        except Exception as e:
            logger.error(f"Daemon error: {e}")

        await asyncio.sleep(interval_hours * 3600)


def main():
    import argparse

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

    parser = argparse.ArgumentParser(description="Research Paper Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--query", help="Custom search query")
    parser.add_argument("--interval", type=int, default=6, help="Daemon interval (hours)")
    args = parser.parse_args()

    if args.query:
        topic = {"query": args.query, "category": "custom", "priority": "high"}
        state = load_state()
        count = asyncio.run(process_topic(topic, state, 10))
        save_state(state)
        print(f"Found {count} new papers")
        return

    if args.daemon:
        asyncio.run(daemon_loop(args.interval))
    else:
        asyncio.run(check_all_topics())


if __name__ == "__main__":
    main()
