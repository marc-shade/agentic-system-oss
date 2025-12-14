#!/usr/bin/env python3
"""
RSS Feed Ingestion Service - Information Diet System
Fetches RSS feeds, summarizes with LLM, stores in enhanced memory.

Usage:
    python3 rss_ingestion.py                    # Process all configured feeds
    python3 rss_ingestion.py --feed URL         # Process single feed
    python3 rss_ingestion.py --daemon           # Run continuously
    python3 rss_ingestion.py --list             # List configured feeds
"""
import platform

import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

# Third-party imports
try:
    import feedparser
    import httpx
except ImportError:
    print("Installing required packages...")
    os.system("pip3 install feedparser httpx")
    import feedparser
    import httpx

# Import shared summarizer
from summarizer import summarize

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("rss_ingestion")

# Configuration
CONFIG_DIR = Path(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))) / "config"
FEEDS_CONFIG = CONFIG_DIR / "information-diet-feeds.json"
STATE_FILE = Path(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))) / "databases" / "information-diet-state.json"

# NOTE: Summarization handled by shared summarizer module
# Priority: 1) Anthropic API, 2) Claude Code headless, 3) Ollama cluster

# Default feeds if config doesn't exist
DEFAULT_FEEDS = [
    {
        "name": "Hacker News",
        "url": "https://hnrss.org/frontpage",
        "category": "tech",
        "summarize": True,
        "max_items": 10
    },
    {
        "name": "arXiv AI",
        "url": "http://export.arxiv.org/rss/cs.AI",
        "category": "research",
        "summarize": True,
        "max_items": 5
    },
    {
        "name": "Anthropic Blog",
        "url": "https://www.anthropic.com/rss.xml",
        "category": "ai",
        "summarize": True,
        "max_items": 5
    }
]


def load_config() -> List[Dict]:
    """Load RSS feed configuration."""
    if FEEDS_CONFIG.exists():
        with open(FEEDS_CONFIG) as f:
            return json.load(f).get("feeds", DEFAULT_FEEDS)
    return DEFAULT_FEEDS


def save_default_config():
    """Save default configuration if none exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not FEEDS_CONFIG.exists():
        with open(FEEDS_CONFIG, "w") as f:
            json.dump({
                "feeds": DEFAULT_FEEDS,
                "settings": {
                    "check_interval_minutes": 60,
                    "max_age_hours": 24,
                    "ollama_model": "llama3.2:3b"
                }
            }, f, indent=2)
        logger.info(f"Created default config at {FEEDS_CONFIG}")


def load_state() -> Dict:
    """Load processing state (seen items)."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"seen_items": {}, "last_run": None}


def save_state(state: Dict):
    """Save processing state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def get_item_id(item: Dict) -> str:
    """Generate unique ID for feed item."""
    content = f"{item.get('title', '')}{item.get('link', '')}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# Summarization is now handled by the shared summarizer module
# See summarizer.py for implementation (Claude API -> Claude headless -> Ollama)


async def store_in_memory(item: Dict, summary: Optional[str], feed_name: str, category: str):
    """Store item in enhanced memory via MCP."""
    content = f"""RSS Item from {feed_name}:
Title: {item.get('title', 'No title')}
Link: {item.get('link', '')}
Published: {item.get('published', 'Unknown')}
Category: {category}

{f'Summary: {summary}' if summary else ''}

Original snippet: {item.get('summary', '')[:500]}"""

    # Use memory MCP client
    try:
        # Try via HTTP API if MCP not directly available
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8101/nmf/remember",
                json={
                    "content": content,
                    "agent_id": "information-diet",
                    "tags": ["rss", category, feed_name.lower().replace(" ", "-")],
                    "metadata": {
                        "source": "rss",
                        "feed": feed_name,
                        "url": item.get('link', ''),
                        "title": item.get('title', '')
                    }
                }
            )
            if response.status_code == 200:
                logger.info(f"Stored: {item.get('title', 'Unknown')[:50]}...")
                return True
    except Exception as e:
        logger.debug(f"HTTP storage failed: {e}")

    # Fallback: Store to local JSON for later sync
    fallback_file = STATE_FILE.parent / "pending_memories.jsonl"
    with open(fallback_file, "a") as f:
        f.write(json.dumps({
            "content": content,
            "tags": ["rss", category],
            "timestamp": datetime.now().isoformat()
        }) + "\n")
    logger.info(f"Queued for later: {item.get('title', 'Unknown')[:50]}...")
    return True


async def process_feed(feed_config: Dict, state: Dict) -> int:
    """Process a single RSS feed, return count of new items."""
    name = feed_config["name"]
    url = feed_config["url"]
    category = feed_config.get("category", "general")
    max_items = feed_config.get("max_items", 10)
    should_summarize = feed_config.get("summarize", True)

    logger.info(f"Processing feed: {name}")

    try:
        feed = feedparser.parse(url)
    except Exception as e:
        logger.error(f"Failed to parse {name}: {e}")
        return 0

    if not feed.entries:
        logger.warning(f"No entries in {name}")
        return 0

    new_count = 0
    seen = state.get("seen_items", {})

    for entry in feed.entries[:max_items]:
        item_id = get_item_id(entry)

        if item_id in seen:
            continue

        # Get summary using shared summarizer (Claude API -> headless -> Ollama)
        summary = None
        if should_summarize:
            text = entry.get("summary", "") or entry.get("description", "")
            if text:
                summary = await summarize(text, entry.get("title", ""))

        # Store in memory
        await store_in_memory(entry, summary, name, category)

        # Mark as seen
        seen[item_id] = {
            "title": entry.get("title", ""),
            "timestamp": datetime.now().isoformat()
        }
        new_count += 1

    state["seen_items"] = seen
    return new_count


async def process_all_feeds():
    """Process all configured feeds."""
    save_default_config()
    feeds = load_config()
    state = load_state()

    total_new = 0
    for feed in feeds:
        try:
            count = await process_feed(feed, state)
            total_new += count
        except Exception as e:
            logger.error(f"Error processing {feed['name']}: {e}")

    save_state(state)
    logger.info(f"Processed {len(feeds)} feeds, {total_new} new items")
    return total_new


async def daemon_loop(interval_minutes: int = 60):
    """Run continuously, checking feeds at interval."""
    logger.info(f"Starting daemon, checking every {interval_minutes} minutes")

    while True:
        try:
            await process_all_feeds()
        except Exception as e:
            logger.error(f"Daemon error: {e}")

        await asyncio.sleep(interval_minutes * 60)


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

    parser = argparse.ArgumentParser(description="RSS Feed Ingestion Service")
    parser.add_argument("--feed", help="Process single feed URL")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--list", action="store_true", help="List configured feeds")
    parser.add_argument("--interval", type=int, default=60, help="Daemon interval (minutes)")
    args = parser.parse_args()

    if args.list:
        save_default_config()
        feeds = load_config()
        print("\nConfigured Feeds:")
        for f in feeds:
            print(f"  - {f['name']}: {f['url']} [{f.get('category', 'general')}]")
        print(f"\nConfig file: {FEEDS_CONFIG}")
        return

    if args.feed:
        feed_config = {
            "name": "Custom",
            "url": args.feed,
            "category": "custom",
            "summarize": True,
            "max_items": 10
        }
        state = load_state()
        count = asyncio.run(process_feed(feed_config, state))
        save_state(state)
        print(f"Processed {count} new items")
        return

    if args.daemon:
        asyncio.run(daemon_loop(args.interval))
    else:
        asyncio.run(process_all_feeds())


if __name__ == "__main__":
    main()
