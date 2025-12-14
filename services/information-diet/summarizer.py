#!/usr/bin/env python3
"""
Summarizer Module - Ollama + Claude Code Headless
Shared by all Information Diet services for content summarization.

Primary: Ollama on local cluster (llama3.2)
Fallback: Claude Code headless (if Max authenticated)
"""

import os
import subprocess
import json
import logging
from typing import Optional

try:
    import httpx
except ImportError:
    os.system("pip3 install httpx")
    import httpx

logger = logging.getLogger("summarizer")


def summarize_with_claude_headless(text: str, title: str, timeout_seconds: int = 60) -> Optional[str]:
    """
    Summarize using Claude Code in headless mode.

    Uses best practices from Claude Code documentation:
    - JSON output format for structured parsing
    - Restricted tools (none needed for summarization)
    - System prompt for consistent behavior
    - Proper error handling via JSON response
    """
    # Content to summarize (limit to avoid token issues)
    content = f'Title: "{title}"\n\nContent: {text[:2000]}'

    try:
        result = subprocess.run(
            [
                "claude", "-p", content,
                "--output-format", "json",
                "--allowedTools", "",  # No tools needed for summarization
                "--append-system-prompt",
                "You are a summarizer. Respond with ONLY a 2-3 sentence summary of the content. No preamble, no explanation, just the summary."
            ],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "cli"}
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                # Parse JSON response for structured data
                response = json.loads(result.stdout)

                # Check for errors in response
                if response.get("is_error"):
                    logger.debug(f"Claude headless error: {response.get('result', 'Unknown error')}")
                    return None

                # Extract result text
                summary = response.get("result", "").strip()
                if summary:
                    # Log cost for monitoring
                    cost = response.get("total_cost_usd", 0)
                    if cost > 0:
                        logger.debug(f"Claude headless cost: ${cost:.4f}")
                    return summary[:500]

            except json.JSONDecodeError:
                # Fallback: treat as plain text if JSON parsing fails
                logger.debug("JSON parse failed, using raw output")
                return result.stdout.strip()[:500]

        # Check stderr for errors
        if result.stderr:
            logger.debug(f"Claude headless stderr: {result.stderr[:200]}")

    except subprocess.TimeoutExpired:
        logger.debug(f"Claude headless timed out after {timeout_seconds}s")
    except FileNotFoundError:
        logger.debug("Claude CLI not found in PATH")
    except Exception as e:
        logger.debug(f"Claude headless failed: {e}")

    return None


async def summarize_with_ollama(text: str, title: str, endpoints: list = None) -> Optional[str]:
    """Fallback: Summarize using Ollama on cluster nodes."""
    if endpoints is None:
        endpoints = [
            "http://localhost:11434",  # Local first (current node)
            "http://macpro51.local:11434",
            "http://mac-studio.local:11434",
        ]

    prompt = f"""Summarize this article in 2-3 sentences:

Title: {title}
Content: {text[:2000]}

Summary:"""

    async with httpx.AsyncClient(timeout=60.0) as client:
        for endpoint in endpoints:
            try:
                response = await client.post(
                    f"{endpoint}/api/generate",
                    json={
                        "model": "llama3.2:latest",  # Use :latest instead of :3b
                        "prompt": prompt,
                        "stream": False,
                        "options": {"num_predict": 150}
                    }
                )
                if response.status_code == 200:
                    result = response.json().get("response", "").strip()
                    if result:
                        logger.debug(f"Summarized via Ollama at {endpoint}")
                        return result
            except Exception as e:
                logger.debug(f"Ollama at {endpoint} failed: {e}")
                continue

    return None


async def summarize(text: str, title: str, max_tokens: int = 150) -> Optional[str]:
    """
    Summarize content using best available method.

    Priority:
    1. Ollama on cluster (primary - runs locally on macpro51)
    2. Claude Code headless (fallback - if Max authenticated)
    """
    # Primary: Ollama on local cluster
    summary = await summarize_with_ollama(text, title)
    if summary:
        logger.info("Summarized via Ollama")
        return summary

    # Fallback: Claude headless (if Max is authenticated on this node)
    logger.debug("Ollama unavailable, trying Claude headless")
    summary = summarize_with_claude_headless(text, title)
    if summary:
        logger.info("Summarized via Claude Code headless")
        return summary

    logger.warning("No summarization method available")
    return None
