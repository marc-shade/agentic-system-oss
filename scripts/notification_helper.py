#!/usr/bin/env python3
"""
Notification Helper for AGI Daemons

Provides unified notification support for all autonomous daemons:
- Voice announcements via voice-mode MCP
- Log to notifications.log
- Store in voice_notifications.db

Used by: goal-decomposer-daemon, task-processor-daemon, etc.
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import platform

logger = logging.getLogger(__name__)


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

# Configuration
NOTIFICATION_CONFIG = {
    "voice_mode_url": "http://localhost:8765/speak",  # voice-mode MCP endpoint
    "notification_log": str(_STORAGE_BASE / "logs" / "notifications.log"),
    "voice_db_path": str(_STORAGE_BASE / "databases" / "voice_notifications.db"),
    "default_voice": "en-IE-EmilyNeural",  # Irish female voice
    "enable_voice": True,
    "enable_log": True,
    "enable_db": True,
}


def init_notifications_db():
    """Initialize voice notifications database if needed."""
    db_path = Path(NOTIFICATION_CONFIG["voice_db_path"])
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            source TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            metadata TEXT,
            spoken INTEGER DEFAULT 0,
            acknowledged INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()


def log_notification(source: str, level: str, message: str, metadata: Optional[dict] = None):
    """Log notification to file."""
    if not NOTIFICATION_CONFIG["enable_log"]:
        return

    log_path = Path(NOTIFICATION_CONFIG["notification_log"])
    log_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{source}] [{level}] {message}"
    if metadata:
        log_entry += f" | {json.dumps(metadata)}"

    with open(log_path, "a") as f:
        f.write(log_entry + "\n")


def store_notification(source: str, level: str, message: str, metadata: Optional[dict] = None, spoken: bool = False):
    """Store notification in database."""
    if not NOTIFICATION_CONFIG["enable_db"]:
        return

    try:
        init_notifications_db()
        conn = sqlite3.connect(NOTIFICATION_CONFIG["voice_db_path"])
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO notifications (timestamp, source, level, message, metadata, spoken)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            source,
            level,
            message,
            json.dumps(metadata) if metadata else None,
            1 if spoken else 0
        ))

        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"Failed to store notification in DB: {e}")


async def speak_notification(message: str, voice: Optional[str] = None) -> bool:
    """Send voice notification via edge-tts."""
    if not NOTIFICATION_CONFIG["enable_voice"]:
        return False

    try:
        import subprocess
        import tempfile

        voice_name = voice or NOTIFICATION_CONFIG["default_voice"]

        # Generate speech using edge-tts
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_file = f.name

        cmd = [
            "edge-tts",
            "--voice", voice_name,
            "--text", message,
            "--write-media", temp_file
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=30)

        if result.returncode == 0:
            # Play audio using mpv or ffplay
            play_cmd = None
            for player in ["mpv", "ffplay", "aplay"]:
                try:
                    subprocess.run(["which", player], capture_output=True, check=True)
                    if player == "mpv":
                        play_cmd = ["mpv", "--no-terminal", "--really-quiet", temp_file]
                    elif player == "ffplay":
                        play_cmd = ["ffplay", "-nodisp", "-autoexit", temp_file]
                    else:
                        # aplay needs wav, skip for mp3
                        continue
                    break
                except subprocess.CalledProcessError:
                    continue

            if play_cmd:
                subprocess.run(play_cmd, capture_output=True, timeout=60)
                return True
            else:
                logger.warning("No audio player found (mpv or ffplay)")
                return False
        else:
            logger.warning(f"edge-tts failed: {result.stderr.decode()}")
            return False

    except FileNotFoundError:
        logger.warning("edge-tts not found in PATH")
        return False
    except Exception as e:
        logger.warning(f"Voice notification failed: {e}")
        return False
    finally:
        # Clean up temp file
        try:
            import os
            if 'temp_file' in locals():
                os.unlink(temp_file)
        except:
            pass


async def notify(
    source: str,
    message: str,
    level: str = "info",
    speak: bool = True,
    metadata: Optional[dict] = None,
    voice: Optional[str] = None
):
    """
    Send unified notification.

    Args:
        source: Source daemon (e.g., "goal-decomposer", "task-processor")
        message: Human-readable message
        level: info, success, warning, error
        speak: Whether to announce via voice
        metadata: Additional data to store
        voice: Override default voice
    """
    # Always log
    log_notification(source, level, message, metadata)

    # Speak if requested
    spoken = False
    if speak:
        spoken = await speak_notification(message, voice)

    # Store in DB
    store_notification(source, level, message, metadata, spoken)

    logger.info(f"[{source}] {level.upper()}: {message}")


async def notify_task_complete(task_title: str, task_id: int, result: str = "success"):
    """Notify when a task completes."""
    level = "success" if result == "success" else "warning"
    message = f"Task completed: {task_title}"

    await notify(
        source="task-processor",
        message=message,
        level=level,
        speak=True,
        metadata={"task_id": task_id, "result": result}
    )


async def notify_task_failed(task_title: str, task_id: int, error: str):
    """Notify when a task fails."""
    message = f"Task failed: {task_title}"

    await notify(
        source="task-processor",
        message=message,
        level="error",
        speak=True,
        metadata={"task_id": task_id, "error": error[:200]}
    )


async def notify_goal_decomposed(goal_name: str, goal_id: int, task_count: int):
    """Notify when a goal is decomposed."""
    message = f"Goal decomposed into {task_count} tasks: {goal_name}"

    await notify(
        source="goal-decomposer",
        message=message,
        level="info",
        speak=True,
        metadata={"goal_id": goal_id, "task_count": task_count}
    )


async def notify_daemon_status(daemon: str, status: str, details: Optional[str] = None):
    """Notify daemon status changes."""
    message = f"{daemon} is {status}"
    if details:
        message += f": {details}"

    level = "info" if status in ("starting", "running") else "warning"

    await notify(
        source=daemon,
        message=message,
        level=level,
        speak=False,  # Don't speak routine status updates
        metadata={"status": status}
    )


# Synchronous wrappers for non-async contexts
def notify_sync(source: str, message: str, level: str = "info", speak: bool = True, metadata: Optional[dict] = None):
    """Synchronous wrapper for notify."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(notify(source, message, level, speak, metadata))
        else:
            loop.run_until_complete(notify(source, message, level, speak, metadata))
    except RuntimeError:
        # No event loop, create one
        asyncio.run(notify(source, message, level, speak, metadata))


if __name__ == "__main__":
    # Test notifications
    async def test():
        print("Testing notification system...")
        await notify("test", "This is a test notification", level="info", speak=True)
        await notify_task_complete("Test task", 123, "success")
        await notify_goal_decomposed("Test goal", 1, 5)
        print("Test complete!")

    asyncio.run(test())
