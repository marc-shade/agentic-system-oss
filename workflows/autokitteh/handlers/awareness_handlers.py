"""
Awareness System AutoKitteh Handlers
====================================
Ensures the AGI Environmental Awareness System runs persistently.
"""

import subprocess
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3

# Configuration
STORAGE_BASE = Path("/Volumes/SSDRAID0/agentic-system")
AWARENESS_SCRIPT = STORAGE_BASE / "scripts" / "start-awareness.sh"
SENSORY_DIR = STORAGE_BASE / "databases" / "sensory"
LOG_DIR = STORAGE_BASE / "logs"
PID_FILE = LOG_DIR / "awareness.pid"

# State tracking
RESTART_COOLDOWN = timedelta(seconds=60)
MAX_RESTARTS_PER_HOUR = 3
restart_history = []


def is_awareness_running():
    """Check if awareness system is running."""
    if not PID_FILE.exists():
        return False

    try:
        pid = int(PID_FILE.read_text().strip())
        # Check if process exists
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        return False


def start_awareness():
    """Start the awareness system."""
    global restart_history

    # Check restart cooldown
    now = datetime.now()
    restart_history = [t for t in restart_history if now - t < timedelta(hours=1)]

    if len(restart_history) >= MAX_RESTARTS_PER_HOUR:
        return {
            "status": "blocked",
            "reason": f"Too many restarts ({len(restart_history)}) in the last hour",
            "next_restart_allowed": restart_history[0] + timedelta(hours=1)
        }

    try:
        result = subprocess.run(
            [str(AWARENESS_SCRIPT), "start"],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            restart_history.append(now)
            return {
                "status": "started",
                "output": result.stdout,
                "timestamp": now.isoformat()
            }
        else:
            return {
                "status": "failed",
                "error": result.stderr,
                "returncode": result.returncode
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def get_awareness_status():
    """Get comprehensive awareness system status."""
    try:
        result = subprocess.run(
            [str(AWARENESS_SCRIPT), "status"],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Parse JSON from output
        lines = result.stdout.strip().split('\n')
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                json_str = '\n'.join(lines[i:])
                return json.loads(json_str)

        return {"raw_output": result.stdout}
    except Exception as e:
        return {"error": str(e)}


def get_capture_stats():
    """Get statistics on captured sensory data."""
    stats = {
        "screenshots": 0,
        "webcam": 0,
        "audio_transcripts": 0,
        "total_size_mb": 0
    }

    # Count captures from database
    db_path = None
    for db in SENSORY_DIR.glob("sensory_memory_*.db"):
        if db.stat().st_size > 0:
            db_path = db
            break

    if db_path and db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                stats["screenshots"] = conn.execute(
                    "SELECT COUNT(*) FROM captures WHERE capture_type='screenshot' AND deleted=FALSE"
                ).fetchone()[0]
                stats["webcam"] = conn.execute(
                    "SELECT COUNT(*) FROM captures WHERE capture_type='webcam' AND deleted=FALSE"
                ).fetchone()[0]
        except:
            pass

    # Check audio transcripts
    for db in SENSORY_DIR.glob("sensory_memory_*.db"):
        if db.stat().st_size > 0:
            try:
                with sqlite3.connect(db) as conn:
                    stats["audio_transcripts"] = conn.execute(
                        "SELECT COUNT(*) FROM audio_transcripts"
                    ).fetchone()[0]
            except:
                pass

    # Calculate total size
    for f in SENSORY_DIR.rglob("*"):
        if f.is_file():
            stats["total_size_mb"] += f.stat().st_size / (1024 * 1024)

    stats["total_size_mb"] = round(stats["total_size_mb"], 2)
    return stats


# === AutoKitteh Handlers ===

def ensure_awareness_running(ctx):
    """
    Handler: Ensure awareness system is running.
    Called on startup and health checks.
    """
    if is_awareness_running():
        status = get_awareness_status()
        return {
            "action": "verified",
            "running": True,
            "status": status
        }
    else:
        # System not running, attempt restart
        result = start_awareness()
        return {
            "action": "restarted",
            "running": result.get("status") == "started",
            "result": result
        }


def generate_daily_report(ctx):
    """
    Handler: Generate daily awareness report.
    Called at 9 AM daily.
    """
    running = is_awareness_running()
    status = get_awareness_status() if running else {"error": "not running"}
    capture_stats = get_capture_stats()

    report = {
        "report_type": "daily_awareness",
        "timestamp": datetime.now().isoformat(),
        "system_running": running,
        "health": status.get("health", "unknown"),
        "drives": status.get("drives", {}),
        "capture_stats": capture_stats,
        "sensory_data_mb": status.get("sensory_mb", capture_stats.get("total_size_mb", 0)),
        "recommendations": []
    }

    # Add recommendations based on status
    if not running:
        report["recommendations"].append("Awareness system not running - investigate")

    if status.get("health") == "warning":
        report["recommendations"].append("Drive space warning - consider cleanup")

    if capture_stats["total_size_mb"] > 1500:  # > 1.5GB
        report["recommendations"].append("Sensory data exceeding recommended size")

    return report


def manual_restart(ctx):
    """
    Handler: Manually restart awareness system.
    Can be triggered via AutoKitteh API.
    """
    # Stop first if running
    if is_awareness_running():
        subprocess.run([str(AWARENESS_SCRIPT), "stop"], timeout=10)

    # Start fresh
    return start_awareness()


def get_status(ctx):
    """
    Handler: Get current status without taking action.
    """
    return {
        "running": is_awareness_running(),
        "status": get_awareness_status(),
        "capture_stats": get_capture_stats(),
        "restart_history": [t.isoformat() for t in restart_history]
    }
