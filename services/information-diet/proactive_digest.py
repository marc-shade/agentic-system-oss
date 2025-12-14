#!/usr/bin/env python3
"""
Proactive Digest - Information Diet System
Generate daily/weekly digests of gathered information, notify via voice/Arduino.

Usage:
    python3 proactive_digest.py                  # Generate today's digest
    python3 proactive_digest.py --weekly         # Weekly digest
    python3 proactive_digest.py --daemon         # Run on schedule
    python3 proactive_digest.py --speak          # Also speak the digest
"""
import platform

import asyncio
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
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
logger = logging.getLogger("digest")

AGENTIC_PATH = Path(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
DIGEST_DIR = AGENTIC_PATH / "logs" / "digests"

# Ollama endpoints for summarization fallback
OLLAMA_ENDPOINTS = [
    "http://localhost:11434",  # Local first (current node)
    "http://macpro51.local:11434",
    "http://mac-studio.local:11434",
]

# Ollama model to use (llama3.2:latest is available on this node)
OLLAMA_MODEL = "llama3.2:latest"


async def get_recent_memories(hours: int = 24, limit: int = 50) -> List[Dict]:
    """Get recent memories from enhanced memory."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Search for recent items by various tags
            response = await client.post(
                "http://localhost:8101/nmf/recall",
                json={
                    "query": "recent information news research update",
                    "mode": "temporal",
                    "limit": limit
                }
            )
            if response.status_code == 200:
                return response.json().get("memories", [])
    except Exception as e:
        logger.debug(f"Memory recall failed: {e}")

    # Fallback: check pending files
    memories = []
    pending_files = [
        AGENTIC_PATH / "databases" / "pending_memories.jsonl",
        AGENTIC_PATH / "databases" / "pending_papers.jsonl",
        AGENTIC_PATH / "databases" / "pending_videos.jsonl"
    ]

    for pf in pending_files:
        if pf.exists():
            with open(pf) as f:
                for line in f:
                    try:
                        item = json.loads(line.strip())
                        # Check timestamp
                        ts = datetime.fromisoformat(item.get("timestamp", ""))
                        if datetime.now() - ts < timedelta(hours=hours):
                            memories.append(item)
                    except:
                        pass

    return memories[:limit]


def summarize_with_claude_headless(content: str, timeout_seconds: int = 120) -> Optional[str]:
    """
    Summarize using Claude Code in headless mode.

    Uses best practices from Claude Code documentation:
    - JSON output format for structured parsing
    - Restricted tools (none needed for summarization)
    - System prompt for consistent digest behavior
    """
    import subprocess

    system_prompt = """You are a digest creator. Create a structured summary with:
1. Key highlights (2-3 most important items)
2. Research updates (if any)
3. News and trends
4. Action items or things to follow up
Keep the summary concise (under 500 words). No preamble."""

    try:
        result = subprocess.run(
            [
                "claude", "-p", content,
                "--output-format", "json",
                "--allowedTools", "",  # No tools needed
                "--append-system-prompt", system_prompt
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "cli"}
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                response = json.loads(result.stdout)
                if response.get("is_error"):
                    logger.debug(f"Claude error: {response.get('result', 'Unknown')}")
                    return None

                summary = response.get("result", "").strip()
                if summary:
                    cost = response.get("total_cost_usd", 0)
                    if cost > 0:
                        logger.debug(f"Digest cost: ${cost:.4f}")
                    return summary[:2000]

            except json.JSONDecodeError:
                logger.debug("JSON parse failed, using raw output")
                return result.stdout.strip()[:2000]

        if result.stderr:
            logger.debug(f"Claude stderr: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        logger.debug(f"Claude timed out after {timeout_seconds}s")
    except FileNotFoundError:
        logger.debug("Claude CLI not found")
    except Exception as e:
        logger.debug(f"Claude headless failed: {e}")

    return None


async def summarize_digest(items: List[Dict]) -> Optional[str]:
    """
    Summarize items into a digest.
    Priority: 1) Claude Code headless, 2) Ollama on cluster.
    """
    if not items:
        return "No new information gathered in this period."

    # Prepare content for summarization
    content_parts = []
    for item in items[:20]:  # Limit to 20 items
        content = item.get("content", "")[:500]
        tags = item.get("tags", [])
        content_parts.append(f"[{', '.join(tags[:2])}] {content}")

    combined = "\n\n---\n\n".join(content_parts)

    prompt = f"""Create a brief digest summary of these information items. Group by category and highlight the most important items:

{combined[:6000]}

Provide a structured digest with:
1. Key highlights (2-3 most important items)
2. Research updates (if any)
3. News and trends
4. Action items or things to follow up

Keep the summary concise (under 500 words)."""

    # Try Claude Code headless first
    summary = summarize_with_claude_headless(prompt)
    if summary:
        logger.debug("Digest generated via Claude headless")
        return summary

    # Fallback to Ollama on cluster
    async with httpx.AsyncClient(timeout=120.0) as client:
        for endpoint in OLLAMA_ENDPOINTS:
            try:
                response = await client.post(
                    f"{endpoint}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": 600}
                    }
                )
                if response.status_code == 200:
                    logger.debug(f"Digest generated via Ollama at {endpoint}")
                    return response.json().get("response", "").strip()
            except Exception as e:
                logger.debug(f"Ollama at {endpoint} unavailable: {e}")
                continue

    # Fallback: simple summary
    logger.warning("No summarization method available for digest")
    return f"Gathered {len(items)} new items. Categories: {', '.join(set(t for i in items for t in i.get('tags', [])[:2]))}"


async def speak_digest(text: str):
    """Speak the digest via voice-mode MCP."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                "http://localhost:8103/speak",
                json={"text": text[:1000]}  # Limit length for voice
            )
    except Exception as e:
        logger.debug(f"Voice notification failed: {e}")


def save_digest(digest: str, period: str):
    """Save digest to file."""
    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = DIGEST_DIR / f"digest_{period}_{timestamp}.md"

    content = f"""# Information Digest - {period.title()}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

{digest}

---
*Generated by Information Diet System*
"""

    with open(filename, "w") as f:
        f.write(content)

    logger.info(f"Saved digest to {filename}")
    return filename


async def generate_digest(period: str = "daily", speak: bool = False) -> str:
    """Generate a digest for the specified period."""
    hours = 24 if period == "daily" else 168  # 7 days for weekly

    logger.info(f"Generating {period} digest...")

    # Get recent memories
    memories = await get_recent_memories(hours=hours, limit=100)
    logger.info(f"Found {len(memories)} items")

    # Generate summary (Claude headless -> Ollama fallback)
    summary = await summarize_digest(memories)

    # Add stats header
    digest = f"""## Summary
- Period: Last {hours} hours
- Items processed: {len(memories)}
- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Digest

{summary}
"""

    # Save digest
    save_digest(digest, period)

    # Optionally speak
    if speak:
        # Create voice-friendly version
        voice_summary = f"Here's your {period} information digest. {summary[:500]}"
        await speak_digest(voice_summary)

    return digest


async def daemon_loop(daily_hour: int = 8, weekly_day: int = 0):
    """
    Run on schedule.
    daily_hour: Hour to generate daily digest (0-23)
    weekly_day: Day for weekly digest (0=Monday)
    """
    logger.info(f"Starting digest daemon (daily at {daily_hour}:00, weekly on day {weekly_day})")

    while True:
        now = datetime.now()

        # Check if time for daily digest
        if now.hour == daily_hour and now.minute < 5:
            await generate_digest("daily", speak=True)

            # Check if also time for weekly
            if now.weekday() == weekly_day:
                await generate_digest("weekly", speak=False)

        # Sleep until next check
        await asyncio.sleep(300)  # Check every 5 minutes


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

    parser = argparse.ArgumentParser(description="Proactive Digest")
    parser.add_argument("--weekly", action="store_true", help="Generate weekly digest")
    parser.add_argument("--daemon", action="store_true", help="Run on schedule")
    parser.add_argument("--speak", action="store_true", help="Speak the digest")
    parser.add_argument("--hour", type=int, default=8, help="Hour for daily digest")
    args = parser.parse_args()

    if args.daemon:
        asyncio.run(daemon_loop(daily_hour=args.hour))
    else:
        period = "weekly" if args.weekly else "daily"
        digest = asyncio.run(generate_digest(period, speak=args.speak))
        print(digest)


if __name__ == "__main__":
    main()
