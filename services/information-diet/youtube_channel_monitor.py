#!/usr/bin/env python3
"""
YouTube Channel Monitor - Information Diet System
Watches specified channels, auto-fetches transcripts, extracts key concepts.
Leverages existing video-transcript-mcp server.

Usage:
    python3 youtube_channel_monitor.py                    # Check all channels
    python3 youtube_channel_monitor.py --daemon           # Run continuously
    python3 youtube_channel_monitor.py --channel ID       # Check specific channel
"""
import platform

import asyncio
import hashlib
import json
import os
import re
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
logger = logging.getLogger("youtube_monitor")

# Configuration
AGENTIC_PATH = Path(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
CONFIG_FILE = AGENTIC_PATH / "config" / "youtube-channels.json"
STATE_FILE = AGENTIC_PATH / "databases" / "youtube-monitor-state.json"

# Default channels to monitor
DEFAULT_CHANNELS = [
    {
        "name": "Anthropic",
        "channel_id": "UCnnXe2Sb6Gn_zNUUXEFXxpA",
        "category": "ai-research",
        "priority": "high"
    },
    {
        "name": "Yannic Kilcher",
        "channel_id": "UCZHmQk67mSJgfCCTn7xBfew",
        "category": "ml-papers",
        "priority": "high"
    },
    {
        "name": "Two Minute Papers",
        "channel_id": "UCbfYPyITQ-7l4upoX8nvctg",
        "category": "ai-news",
        "priority": "medium"
    },
    {
        "name": "Lex Fridman",
        "channel_id": "UCSHZKyawb77ixDdsGog4iWA",
        "category": "interviews",
        "priority": "medium"
    }
]


def load_config() -> Dict:
    """Load channel configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"channels": DEFAULT_CHANNELS, "max_videos_per_channel": 3}


def save_default_config():
    """Save default configuration."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        with open(CONFIG_FILE, "w") as f:
            json.dump({
                "channels": DEFAULT_CHANNELS,
                "max_videos_per_channel": 3,
                "check_interval_hours": 12,
                "transcript_max_tokens": 15000
            }, f, indent=2)
        logger.info(f"Created config at {CONFIG_FILE}")


def load_state() -> Dict:
    """Load processing state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"seen_videos": {}, "last_run": None}


def save_state(state: Dict):
    """Save processing state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


async def get_channel_videos(channel_id: str, max_videos: int = 3) -> List[Dict]:
    """Get recent videos from a YouTube channel via RSS."""
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(rss_url)
            if response.status_code != 200:
                return []

            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.text)
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'yt': 'http://www.youtube.com/xml/schemas/2015',
                'media': 'http://search.yahoo.com/mrss/'
            }

            videos = []
            for entry in root.findall('atom:entry', ns)[:max_videos]:
                video_id = entry.find('yt:videoId', ns)
                title = entry.find('atom:title', ns)
                published = entry.find('atom:published', ns)
                media_group = entry.find('media:group', ns)
                description = media_group.find('media:description', ns) if media_group is not None else None

                videos.append({
                    "video_id": video_id.text if video_id is not None else "",
                    "title": title.text if title is not None else "",
                    "published": published.text if published is not None else "",
                    "description": description.text[:500] if description is not None and description.text else "",
                    "url": f"https://www.youtube.com/watch?v={video_id.text}" if video_id is not None else ""
                })

            return videos
    except Exception as e:
        logger.error(f"Failed to fetch channel {channel_id}: {e}")
        return []


async def fetch_transcript(video_url: str) -> Optional[str]:
    """Fetch video transcript via MCP or yt-dlp."""
    # Try video-transcript-mcp
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8106/fetch_youtube_transcript",
                json={"url": video_url, "auto_clean": True}
            )
            if response.status_code == 200:
                return response.json().get("transcript", "")
    except Exception as e:
        logger.debug(f"MCP transcript failed: {e}")

    # Fallback: try youtube_transcript_api
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        video_id_match = re.search(r'v=([^&]+)', video_url)
        if video_id_match:
            video_id = video_id_match.group(1)
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join([t['text'] for t in transcript_list])
    except Exception as e:
        logger.debug(f"Fallback transcript failed: {e}")

    return None


async def store_video_in_memory(video: Dict, channel: Dict, transcript: Optional[str]):
    """Store video and transcript in enhanced memory."""
    transcript_snippet = transcript[:2000] if transcript else "Transcript not available"

    content = f"""YouTube Video from {channel['name']}:
Title: {video.get('title', 'Unknown')}
Channel: {channel['name']} ({channel.get('category', 'general')})
Published: {video.get('published', 'Unknown')[:10]}
URL: {video.get('url', '')}
Priority: {channel.get('priority', 'medium')}

Description:
{video.get('description', '')[:500]}

Transcript Preview:
{transcript_snippet}"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8101/nmf/remember",
                json={
                    "content": content,
                    "agent_id": "youtube-monitor",
                    "tags": ["youtube", channel.get('category', 'general'), channel['name'].lower().replace(" ", "-")],
                    "metadata": {
                        "source": "youtube",
                        "video_id": video.get('video_id', ''),
                        "channel": channel['name'],
                        "url": video.get('url', '')
                    }
                }
            )
            if response.status_code == 200:
                logger.info(f"Stored video: {video.get('title', '')[:50]}...")
                return True
    except Exception as e:
        logger.debug(f"MCP storage failed: {e}")

    # Fallback
    fallback_file = STATE_FILE.parent / "pending_videos.jsonl"
    with open(fallback_file, "a") as f:
        f.write(json.dumps({
            "content": content,
            "tags": ["youtube", channel.get('category', 'general')],
            "timestamp": datetime.now().isoformat()
        }) + "\n")
    logger.info(f"Queued video: {video.get('title', '')[:50]}...")
    return True


async def process_channel(channel: Dict, state: Dict, max_videos: int) -> int:
    """Process a single YouTube channel."""
    name = channel["name"]
    channel_id = channel["channel_id"]
    logger.info(f"Checking channel: {name}")

    videos = await get_channel_videos(channel_id, max_videos)
    if not videos:
        logger.warning(f"No videos found for {name}")
        return 0

    new_count = 0
    seen = state.get("seen_videos", {})

    for video in videos:
        video_id = video.get("video_id", "")
        if not video_id or video_id in seen:
            continue

        # Fetch transcript
        transcript = await fetch_transcript(video.get("url", ""))

        # Store in memory
        await store_video_in_memory(video, channel, transcript)

        seen[video_id] = {
            "title": video.get("title", ""),
            "timestamp": datetime.now().isoformat()
        }
        new_count += 1

    state["seen_videos"] = seen
    return new_count


async def check_all_channels():
    """Check all configured channels."""
    save_default_config()
    config = load_config()
    state = load_state()

    channels = config.get("channels", DEFAULT_CHANNELS)
    max_videos = config.get("max_videos_per_channel", 3)

    total_new = 0
    for channel in channels:
        try:
            count = await process_channel(channel, state, max_videos)
            total_new += count
            await asyncio.sleep(2)  # Rate limiting
        except Exception as e:
            logger.error(f"Error processing {channel['name']}: {e}")

    save_state(state)
    logger.info(f"Checked {len(channels)} channels, found {total_new} new videos")
    return total_new


async def daemon_loop(interval_hours: int = 12):
    """Run continuously."""
    logger.info(f"Starting daemon, checking every {interval_hours} hours")

    while True:
        try:
            await check_all_channels()
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

    parser = argparse.ArgumentParser(description="YouTube Channel Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run continuously")
    parser.add_argument("--channel", help="Specific channel ID to check")
    parser.add_argument("--interval", type=int, default=12, help="Daemon interval (hours)")
    args = parser.parse_args()

    if args.channel:
        channel = {"name": "Custom", "channel_id": args.channel, "category": "custom", "priority": "high"}
        state = load_state()
        count = asyncio.run(process_channel(channel, state, 5))
        save_state(state)
        print(f"Found {count} new videos")
        return

    if args.daemon:
        asyncio.run(daemon_loop(args.interval))
    else:
        asyncio.run(check_all_channels())


if __name__ == "__main__":
    main()
