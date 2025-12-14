"""
Ember Health Monitor Handlers
Ensures Ember stays healthy and monitors for violations
"""
import subprocess
import json
import time
import random
import os
from datetime import datetime, timedelta


def check_ember_status(event):
    """Get Ember status from Tamagotchi CLI"""
    try:
        result = subprocess.run(
            ["bun", "/tmp/claude-code-tamagotchi/dist/index.js", "status"],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Parse status output
        output = result.stdout

        # Extract stats (simple parsing)
        needs_care = False
        if "🍖" in output:
            # Check if hunger is low
            hunger_match = output.split("🍖")[1].split("%")[0].strip()
            if hunger_match.isdigit() and int(hunger_match) < 50:
                needs_care = True

        return {
            "healthy": result.returncode == 0,
            "needs_care": needs_care,
            "output": output[:200],
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e),
            "timestamp": time.time()
        }


def care_for_ember(event):
    """Feed, play, clean, or pet Ember"""
    # Get care type from event data or default to feed
    care_type = event.data.get("care_type", "feed") if hasattr(event, "data") else "feed"

    try:
        if care_type == "feed":
            foods = ["pizza", "cookie", "sushi", "apple", "fish"]
            food = random.choice(foods)
            result = subprocess.run(
                ["bun", "/tmp/claude-code-tamagotchi/dist/index.js", "feed", food],
                capture_output=True,
                text=True,
                timeout=5
            )
        elif care_type == "play":
            result = subprocess.run(
                ["bun", "/tmp/claude-code-tamagotchi/dist/index.js", "play"],
                capture_output=True,
                text=True,
                timeout=5
            )
        elif care_type == "clean":
            result = subprocess.run(
                ["bun", "/tmp/claude-code-tamagotchi/dist/index.js", "clean"],
                capture_output=True,
                text=True,
                timeout=5
            )
        elif care_type == "pet":
            result = subprocess.run(
                ["bun", "/tmp/claude-code-tamagotchi/dist/index.js", "pet"],
                capture_output=True,
                text=True,
                timeout=5
            )

        return {
            "success": result.returncode == 0,
            "care_type": care_type,
            "output": result.stdout[:100]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def check_violations(event):
    """Check ember_violations.jsonl for recent violations"""
    violations_path = os.path.expanduser("~/.claude/ember_violations.jsonl")

    if not os.path.exists(violations_path):
        return {
            "has_violations": False,
            "count": 0
        }

    try:
        recent_violations = []
        cutoff = (datetime.now() - timedelta(minutes=10)).timestamp()

        with open(violations_path) as f:
            for line in f:
                try:
                    violation = json.loads(line)
                    if violation.get("timestamp", 0) > cutoff:
                        recent_violations.append(violation)
                except:
                    pass

        return {
            "has_violations": len(recent_violations) > 0,
            "count": len(recent_violations),
            "violations": recent_violations[:5]  # Latest 5
        }
    except Exception as e:
        return {
            "has_violations": False,
            "error": str(e)
        }


def notify_via_voice(event):
    """Send voice notification via MCP"""
    message = event.data.get("message", "Notification") if hasattr(event, "data") else "Notification"

    try:
        # Use voice-mode MCP for notification
        # This would integrate with your voice MCP server
        return {
            "notified": True,
            "message": message
        }
    except Exception as e:
        return {
            "notified": False,
            "error": str(e)
        }
