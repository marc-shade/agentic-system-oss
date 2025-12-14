#!/usr/bin/env python3
"""
Webhook Receiver - Information Diet System
HTTP endpoint to receive data from n8n workflows and store in memory.

Endpoints:
    POST /webhook/memory      - Store arbitrary content in memory
    POST /webhook/rss         - Store RSS-style item
    POST /webhook/email       - Store email summary
    POST /webhook/calendar    - Store calendar event
    GET  /webhook/health      - Health check
    GET  /webhook/stats       - Statistics

Usage:
    python3 webhook_receiver.py                # Start on default port 8110
    python3 webhook_receiver.py --port 8110    # Custom port
"""
import platform

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging

try:
    from flask import Flask, request, jsonify
    import httpx
except ImportError:
    os.system("pip3 install flask httpx")
    from flask import Flask, request, jsonify
    import httpx

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("webhook_receiver")

app = Flask(__name__)

# Configuration
AGENTIC_PATH = Path(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)))
STATE_FILE = AGENTIC_PATH / "databases" / "webhook-stats.json"

# Stats tracking
stats = {
    "total_received": 0,
    "successful_stores": 0,
    "failed_stores": 0,
    "by_type": {},
    "started_at": datetime.now().isoformat()
}


def load_stats():
    """Load stats from file."""
    global stats
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            saved = json.load(f)
            stats.update(saved)


def save_stats():
    """Save stats to file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(stats, f, indent=2)


async def store_in_memory(content: str, tags: list, metadata: dict) -> bool:
    """Store content in enhanced memory via MCP."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8101/nmf/remember",
                json={
                    "content": content,
                    "agent_id": "webhook-receiver",
                    "tags": tags,
                    "metadata": metadata
                }
            )
            if response.status_code == 200:
                return True
    except Exception as e:
        logger.debug(f"MCP storage failed: {e}")

    # Fallback to local file
    fallback_file = STATE_FILE.parent / "pending_webhook_memories.jsonl"
    with open(fallback_file, "a") as f:
        f.write(json.dumps({
            "content": content,
            "tags": tags,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat()
        }) + "\n")
    return True


def run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@app.route("/webhook/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "information-diet-webhook",
        "timestamp": datetime.now().isoformat()
    })


@app.route("/webhook/stats", methods=["GET"])
def get_stats():
    """Get webhook statistics."""
    return jsonify(stats)


@app.route("/webhook/memory", methods=["POST"])
def receive_memory():
    """
    Store arbitrary content in memory.

    Body:
        {
            "content": "Text content to store",
            "tags": ["optional", "tags"],
            "category": "optional-category",
            "source": "source-name",
            "metadata": {}
        }
    """
    stats["total_received"] += 1
    stats["by_type"]["memory"] = stats["by_type"].get("memory", 0) + 1

    data = request.get_json() or {}
    content = data.get("content", "")

    if not content:
        stats["failed_stores"] += 1
        return jsonify({"error": "content is required"}), 400

    tags = data.get("tags", [])
    if data.get("category"):
        tags.append(data["category"])
    tags.append("webhook")

    metadata = data.get("metadata", {})
    metadata["source"] = data.get("source", "n8n-webhook")
    metadata["received_at"] = datetime.now().isoformat()

    success = run_async(store_in_memory(content, tags, metadata))

    if success:
        stats["successful_stores"] += 1
        save_stats()
        logger.info(f"Stored memory: {content[:50]}...")
        return jsonify({"status": "stored", "tags": tags})
    else:
        stats["failed_stores"] += 1
        save_stats()
        return jsonify({"error": "storage failed"}), 500


@app.route("/webhook/rss", methods=["POST"])
def receive_rss():
    """
    Store RSS-style item.

    Body:
        {
            "title": "Article Title",
            "link": "https://...",
            "summary": "Article content...",
            "feed_name": "Source Feed",
            "category": "tech"
        }
    """
    stats["total_received"] += 1
    stats["by_type"]["rss"] = stats["by_type"].get("rss", 0) + 1

    data = request.get_json() or {}

    content = f"""RSS Item from {data.get('feed_name', 'Unknown')}:
Title: {data.get('title', 'No title')}
Link: {data.get('link', '')}
Category: {data.get('category', 'general')}

{data.get('summary', '')}"""

    tags = ["rss", "webhook", data.get("category", "general")]
    metadata = {
        "source": "rss-webhook",
        "feed": data.get("feed_name", ""),
        "url": data.get("link", ""),
        "title": data.get("title", "")
    }

    success = run_async(store_in_memory(content, tags, metadata))

    if success:
        stats["successful_stores"] += 1
        save_stats()
        return jsonify({"status": "stored", "type": "rss"})
    else:
        stats["failed_stores"] += 1
        return jsonify({"error": "storage failed"}), 500


@app.route("/webhook/email", methods=["POST"])
def receive_email():
    """
    Store email summary.

    Body:
        {
            "from": "sender@example.com",
            "subject": "Email Subject",
            "summary": "Email summary...",
            "received": "2024-01-01T10:00:00",
            "importance": "high"
        }
    """
    stats["total_received"] += 1
    stats["by_type"]["email"] = stats["by_type"].get("email", 0) + 1

    data = request.get_json() or {}

    content = f"""Email Summary:
From: {data.get('from', 'Unknown')}
Subject: {data.get('subject', 'No subject')}
Received: {data.get('received', 'Unknown')}
Importance: {data.get('importance', 'normal')}

Summary:
{data.get('summary', '')}"""

    tags = ["email", "webhook", f"importance-{data.get('importance', 'normal')}"]
    metadata = {
        "source": "email-webhook",
        "from": data.get("from", ""),
        "subject": data.get("subject", ""),
        "importance": data.get("importance", "normal")
    }

    success = run_async(store_in_memory(content, tags, metadata))

    if success:
        stats["successful_stores"] += 1
        save_stats()
        return jsonify({"status": "stored", "type": "email"})
    else:
        stats["failed_stores"] += 1
        return jsonify({"error": "storage failed"}), 500


@app.route("/webhook/calendar", methods=["POST"])
def receive_calendar():
    """
    Store calendar event.

    Body:
        {
            "title": "Meeting Title",
            "start": "2024-01-01T10:00:00",
            "end": "2024-01-01T11:00:00",
            "description": "Meeting details...",
            "attendees": ["person1", "person2"],
            "location": "Room A"
        }
    """
    stats["total_received"] += 1
    stats["by_type"]["calendar"] = stats["by_type"].get("calendar", 0) + 1

    data = request.get_json() or {}

    attendees = data.get("attendees", [])
    attendees_str = ", ".join(attendees) if attendees else "None"

    content = f"""Calendar Event:
Title: {data.get('title', 'Untitled Event')}
Start: {data.get('start', 'Unknown')}
End: {data.get('end', 'Unknown')}
Location: {data.get('location', 'Not specified')}
Attendees: {attendees_str}

Description:
{data.get('description', '')}"""

    tags = ["calendar", "webhook", "event"]
    metadata = {
        "source": "calendar-webhook",
        "title": data.get("title", ""),
        "start": data.get("start", ""),
        "location": data.get("location", "")
    }

    success = run_async(store_in_memory(content, tags, metadata))

    if success:
        stats["successful_stores"] += 1
        save_stats()
        return jsonify({"status": "stored", "type": "calendar"})
    else:
        stats["failed_stores"] += 1
        return jsonify({"error": "storage failed"}), 500


@app.route("/webhook/notification", methods=["POST"])
def receive_notification():
    """
    Store notification with optional voice output.

    Body:
        {
            "title": "Notification Title",
            "message": "Notification content...",
            "priority": "high",
            "speak": true
        }
    """
    stats["total_received"] += 1
    stats["by_type"]["notification"] = stats["by_type"].get("notification", 0) + 1

    data = request.get_json() or {}

    content = f"""Notification:
Title: {data.get('title', 'Alert')}
Priority: {data.get('priority', 'normal')}
Time: {datetime.now().isoformat()}

{data.get('message', '')}"""

    tags = ["notification", "webhook", f"priority-{data.get('priority', 'normal')}"]
    metadata = {
        "source": "notification-webhook",
        "title": data.get("title", ""),
        "priority": data.get("priority", "normal")
    }

    success = run_async(store_in_memory(content, tags, metadata))

    # Optional: trigger voice notification
    if data.get("speak") and success:
        try:
            run_async(trigger_voice(data.get("message", data.get("title", "Notification"))))
        except Exception as e:
            logger.debug(f"Voice notification failed: {e}")

    if success:
        stats["successful_stores"] += 1
        save_stats()
        return jsonify({"status": "stored", "type": "notification"})
    else:
        stats["failed_stores"] += 1
        return jsonify({"error": "storage failed"}), 500


async def trigger_voice(text: str):
    """Trigger voice notification via voice-mode MCP."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        await client.post(
            "http://localhost:8103/speak",
            json={"text": text}
        )


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

    parser = argparse.ArgumentParser(description="Webhook Receiver")
    parser.add_argument("--port", type=int, default=8110, help="Port to listen on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    load_stats()
    logger.info(f"Starting webhook receiver on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
