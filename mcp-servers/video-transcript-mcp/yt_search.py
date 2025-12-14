#!/usr/bin/env python3
"""
YouTube Search Integration via yt-dlp
======================================

Provides YouTube search and browsing capabilities using yt-dlp,
inspired by the yt-x terminal browser approach.

Supports:
- Keyword search with filters
- Channel browsing
- Trending/popular videos
- Playlist exploration
- Browser cookie authentication for paid accounts

Uses --cookies-from-browser for premium content access.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger("yt-search")

# Configuration - detect browser for cookies
# Priority: Firefox > Chrome > Chromium > Edge (firefox works best on Linux)
PREFERRED_BROWSER = os.environ.get("YT_COOKIE_BROWSER", "firefox")


@dataclass
class VideoResult:
    """Structured video search result."""
    id: str
    title: str
    channel: str
    channel_id: Optional[str]
    duration: Optional[int]  # seconds
    duration_string: Optional[str]
    view_count: Optional[int]
    upload_date: Optional[str]
    description: Optional[str]
    thumbnail: Optional[str]
    url: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "channel": self.channel,
            "channel_id": self.channel_id,
            "duration": self.duration,
            "duration_string": self.duration_string,
            "view_count": self.view_count,
            "upload_date": self.upload_date,
            "description": self.description,
            "thumbnail": self.thumbnail,
            "url": self.url
        }


def _format_duration(seconds: Optional[int]) -> Optional[str]:
    """Format duration in seconds to HH:MM:SS or MM:SS."""
    if seconds is None:
        return None
    # Convert to int in case yt-dlp returns float
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _parse_entry(entry: Dict) -> VideoResult:
    """Parse yt-dlp JSON entry to VideoResult."""
    video_id = entry.get("id", "")
    duration = entry.get("duration")

    return VideoResult(
        id=video_id,
        title=entry.get("title", "Unknown"),
        channel=entry.get("channel") or entry.get("uploader", "Unknown"),
        channel_id=entry.get("channel_id") or entry.get("uploader_id"),
        duration=duration,
        duration_string=_format_duration(duration) or entry.get("duration_string"),
        view_count=entry.get("view_count"),
        upload_date=entry.get("upload_date"),
        description=entry.get("description"),
        thumbnail=entry.get("thumbnail") or (entry.get("thumbnails", [{}])[-1].get("url") if entry.get("thumbnails") else None),
        url=f"https://youtube.com/watch?v={video_id}"
    )


async def run_ytdlp(url: str, max_results: int = 10, use_cookies: bool = True) -> Dict:
    """
    Run yt-dlp and return JSON result.

    Uses the same approach as yt-x: -J for JSON, --flat-playlist for metadata only.
    """
    cmd = [
        "yt-dlp",
        url,
        "-J",  # JSON output
        "--flat-playlist",  # Don't download, just list
        "--extractor-args", "youtubetab:approximate_date",  # Get approximate dates
        "--playlist-start", "1",
        "--playlist-end", str(max_results),
        "--no-warnings",
        "--ignore-errors",
    ]

    # Add browser cookies for paid account access
    if use_cookies and PREFERRED_BROWSER:
        cmd.extend(["--cookies-from-browser", PREFERRED_BROWSER])

    logger.info(f"Running yt-dlp: {' '.join(cmd[:6])}...")

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=60.0  # 60 second timeout
        )

        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.warning(f"yt-dlp returned {process.returncode}: {error_msg[:200]}")
            # Try to parse partial results anyway

        if stdout:
            return json.loads(stdout.decode())
        return {}

    except asyncio.TimeoutError:
        logger.error("yt-dlp timed out after 60 seconds")
        raise Exception("YouTube search timed out")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse yt-dlp JSON output: {e}")
        raise Exception(f"Invalid response from YouTube: {e}")


async def search_youtube(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    upload_date: Optional[str] = None,
    duration: Optional[str] = None,
    use_cookies: bool = True
) -> List[VideoResult]:
    """
    Search YouTube for videos.

    Args:
        query: Search query string
        max_results: Maximum results to return (default 10)
        sort_by: Sort order - relevance, date, view_count, rating
        upload_date: Filter - hour, today, week, month, year
        duration: Filter - short (<4min), medium (4-20min), long (>20min)
        use_cookies: Use browser cookies for paid account

    Returns:
        List of VideoResult objects
    """
    # Build search URL with filters
    # YouTube search format: ytsearchN:query
    search_url = f"ytsearch{max_results}:{query}"

    # Note: yt-dlp search doesn't support all filters directly,
    # but we can use YouTube's search URL with filters
    if sort_by != "relevance" or upload_date or duration:
        # Use YouTube's search URL with filter params
        params = []

        # Sort parameters (sp=CAI for date, CAM for view count, CAE for rating)
        if sort_by == "date":
            params.append("CAI")
        elif sort_by == "view_count":
            params.append("CAM")
        elif sort_by == "rating":
            params.append("CAE")

        # For complex filters, fall back to basic search
        # (full filter support would require YouTube Data API)

    result = await run_ytdlp(search_url, max_results, use_cookies)

    videos = []
    entries = result.get("entries", [])

    for entry in entries:
        if entry and entry.get("id"):
            try:
                video = _parse_entry(entry)
                videos.append(video)
            except Exception as e:
                logger.warning(f"Failed to parse entry: {e}")

    logger.info(f"Search '{query}' returned {len(videos)} results")
    return videos


async def get_channel_videos(
    channel_url: str,
    max_results: int = 10,
    use_cookies: bool = True
) -> List[VideoResult]:
    """
    Get recent videos from a YouTube channel.

    Args:
        channel_url: Channel URL or @handle (e.g., @3blue1brown, channel/UC...)
        max_results: Maximum videos to return
        use_cookies: Use browser cookies

    Returns:
        List of VideoResult objects
    """
    # Normalize channel URL
    if not channel_url.startswith("http"):
        if channel_url.startswith("@"):
            channel_url = f"https://youtube.com/{channel_url}/videos"
        else:
            channel_url = f"https://youtube.com/channel/{channel_url}/videos"
    elif "/videos" not in channel_url:
        channel_url = channel_url.rstrip("/") + "/videos"

    result = await run_ytdlp(channel_url, max_results, use_cookies)

    videos = []
    entries = result.get("entries", [])

    for entry in entries:
        if entry and entry.get("id"):
            try:
                video = _parse_entry(entry)
                videos.append(video)
            except Exception as e:
                logger.warning(f"Failed to parse entry: {e}")

    logger.info(f"Channel {channel_url} returned {len(videos)} videos")
    return videos


async def get_playlist_videos(
    playlist_url: str,
    max_results: int = 50,
    use_cookies: bool = True
) -> List[VideoResult]:
    """
    Get videos from a YouTube playlist.

    Args:
        playlist_url: Playlist URL or ID
        max_results: Maximum videos to return
        use_cookies: Use browser cookies

    Returns:
        List of VideoResult objects
    """
    # Normalize playlist URL
    if not playlist_url.startswith("http"):
        playlist_url = f"https://youtube.com/playlist?list={playlist_url}"

    result = await run_ytdlp(playlist_url, max_results, use_cookies)

    videos = []
    entries = result.get("entries", [])

    for entry in entries:
        if entry and entry.get("id"):
            try:
                video = _parse_entry(entry)
                videos.append(video)
            except Exception as e:
                logger.warning(f"Failed to parse entry: {e}")

    logger.info(f"Playlist returned {len(videos)} videos")
    return videos


async def get_trending(
    category: str = "now",
    region: str = "US",
    max_results: int = 20,
    use_cookies: bool = True
) -> List[VideoResult]:
    """
    Get trending YouTube videos.

    Args:
        category: Trending category - now, music, gaming, movies
        region: Region code (US, GB, etc.)
        max_results: Maximum videos
        use_cookies: Use browser cookies

    Returns:
        List of VideoResult objects
    """
    # Trending URL format
    category_paths = {
        "now": "trending",
        "music": "feed/trending?bp=4gINGgt5dG1hX2NoYXJ0cw%3D%3D",
        "gaming": "gaming",
        "movies": "feed/trending?bp=4gIcGhpnYW1pbmdfY29ycHVzX21vc3RfcG9wdWxhcg%3D%3D"
    }

    path = category_paths.get(category, "trending")
    url = f"https://youtube.com/{path}"

    result = await run_ytdlp(url, max_results, use_cookies)

    videos = []
    entries = result.get("entries", [])

    for entry in entries:
        if entry and entry.get("id"):
            try:
                video = _parse_entry(entry)
                videos.append(video)
            except Exception as e:
                logger.warning(f"Failed to parse entry: {e}")

    logger.info(f"Trending '{category}' returned {len(videos)} videos")
    return videos


async def get_video_metadata(
    video_url: str,
    use_cookies: bool = True
) -> Optional[VideoResult]:
    """
    Get detailed metadata for a single video.

    Args:
        video_url: YouTube video URL or ID
        use_cookies: Use browser cookies

    Returns:
        VideoResult with full metadata
    """
    # Normalize URL
    if not video_url.startswith("http"):
        video_url = f"https://youtube.com/watch?v={video_url}"

    result = await run_ytdlp(video_url, 1, use_cookies)

    if result and result.get("id"):
        return _parse_entry(result)

    return None


# Quick test
if __name__ == "__main__":
    async def test():
        print("Testing YouTube search...")
        results = await search_youtube("AGI self-improvement", max_results=5)
        for v in results:
            print(f"  - {v.title} ({v.duration_string}) by {v.channel}")

    asyncio.run(test())
