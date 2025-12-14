"""Voice Input Router - Routes STT transcriptions to Claude Code sessions.

Enables voice-controlled interaction with any running Claude Code instance.
Creates a bridge between EnvironmentalListener and Claude Code sessions.
"""

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from collections import deque
import uuid

from .audio_filter import AudioEvent
from ..utils.logging import get_logger


logger = get_logger(__name__)


# Well-known locations for voice input routing
VOICE_INPUT_DIR = Path(os.getenv("XDG_RUNTIME_DIR", "/tmp")) / "pixel_voice"
VOICE_INPUT_FILE = VOICE_INPUT_DIR / "pending_inputs.json"
VOICE_BROADCAST_FILE = VOICE_INPUT_DIR / "broadcast.json"
VOICE_SESSIONS_FILE = VOICE_INPUT_DIR / "active_sessions.json"


@dataclass
class VoiceInput:
    """A voice input destined for Claude Code."""
    id: str
    text: str
    timestamp: str
    is_directed: bool
    confidence: float
    source_event_id: Optional[str] = None
    claimed_by: Optional[str] = None
    claimed_at: Optional[str] = None
    processed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaudeSession:
    """A registered Claude Code session."""
    session_id: str
    pid: int
    registered_at: str
    last_heartbeat: str
    working_dir: str
    capabilities: List[str] = field(default_factory=list)


class VoiceInputRouter:
    """
    Routes voice transcriptions to running Claude Code sessions.

    Architecture:
    1. EnvironmentalListener detects directed speech
    2. VoiceInputRouter queues the input
    3. Claude Code sessions poll for pending inputs
    4. Sessions can claim and process inputs

    Supports:
    - Broadcast mode: All sessions receive the input
    - Directed mode: First available session claims input
    - Session filtering by capability
    """

    def __init__(self, config: dict):
        """Initialize Voice Input Router.

        Args:
            config: Daemon configuration
        """
        self.config = config

        # Configuration
        router_config = config.get("components", {}).get("voice_input_router", {})
        self.enabled = router_config.get("enabled", True)
        self.max_pending_inputs = router_config.get("max_pending_inputs", 50)
        self.input_ttl_seconds = router_config.get("input_ttl_seconds", 300)
        self.session_timeout_seconds = router_config.get("session_timeout_seconds", 60)
        self.auto_broadcast = router_config.get("auto_broadcast", True)

        # State
        self._pending_inputs: deque = deque(maxlen=self.max_pending_inputs)
        self._active_sessions: Dict[str, ClaudeSession] = {}
        self._processed_count = 0

        # Ensure directory exists
        VOICE_INPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Load any existing state
        self._load_state()

        logger.info(
            "voice_input_router_initialized",
            enabled=self.enabled,
            max_pending=self.max_pending_inputs,
            auto_broadcast=self.auto_broadcast,
        )

    def _load_state(self) -> None:
        """Load state from disk."""
        try:
            if VOICE_INPUT_FILE.exists():
                with open(VOICE_INPUT_FILE) as f:
                    data = json.load(f)
                    for item in data.get("pending", []):
                        self._pending_inputs.append(VoiceInput(**item))

            if VOICE_SESSIONS_FILE.exists():
                with open(VOICE_SESSIONS_FILE) as f:
                    data = json.load(f)
                    for session_data in data.get("sessions", []):
                        session = ClaudeSession(**session_data)
                        self._active_sessions[session.session_id] = session
        except Exception as e:
            logger.warning("failed_to_load_voice_state", error=str(e))

    def _save_state(self) -> None:
        """Save state to disk for Claude Code sessions to read."""
        try:
            # Save pending inputs
            pending_data = {
                "pending": [asdict(inp) for inp in self._pending_inputs],
                "updated_at": datetime.now().isoformat(),
                "total_pending": len(self._pending_inputs),
            }
            with open(VOICE_INPUT_FILE, "w") as f:
                json.dump(pending_data, f, indent=2)

            # Save session registry
            sessions_data = {
                "sessions": [asdict(s) for s in self._active_sessions.values()],
                "updated_at": datetime.now().isoformat(),
            }
            with open(VOICE_SESSIONS_FILE, "w") as f:
                json.dump(sessions_data, f, indent=2)

        except Exception as e:
            logger.error("failed_to_save_voice_state", error=str(e))

    async def route_audio_event(self, event: AudioEvent) -> str:
        """Route an audio event to Claude Code sessions.

        Args:
            event: Audio event from EnvironmentalListener

        Returns:
            Input ID for tracking
        """
        if not self.enabled:
            return ""

        # Create voice input
        input_id = str(uuid.uuid4())[:8]
        voice_input = VoiceInput(
            id=input_id,
            text=event.text,
            timestamp=event.timestamp.isoformat(),
            is_directed=event.is_directed_at_pixel,
            confidence=event.confidence,
            source_event_id=f"{event.timestamp.isoformat()}:{event.text[:20]}",
        )

        # Add to pending queue
        self._pending_inputs.append(voice_input)

        # Save state for Claude Code sessions
        self._save_state()

        # If auto-broadcast is enabled, also write to broadcast file
        if self.auto_broadcast and event.is_directed_at_pixel:
            await self._broadcast_input(voice_input)

        logger.info(
            "voice_input_routed",
            input_id=input_id,
            text=event.text[:50],
            is_directed=event.is_directed_at_pixel,
            pending_count=len(self._pending_inputs),
        )

        return input_id

    async def _broadcast_input(self, voice_input: VoiceInput) -> None:
        """Broadcast input to all active sessions.

        Args:
            voice_input: The voice input to broadcast
        """
        broadcast_data = {
            "input": asdict(voice_input),
            "broadcast_at": datetime.now().isoformat(),
            "message": f"Voice input from Marc: {voice_input.text}",
        }

        with open(VOICE_BROADCAST_FILE, "w") as f:
            json.dump(broadcast_data, f, indent=2)

        # Also send desktop notification
        try:
            subprocess.run([
                "notify-send",
                "-a", "Pixel",
                "-i", "audio-input-microphone",
                "Voice Input Detected",
                voice_input.text[:100],
            ], capture_output=True, timeout=5)
        except Exception as e:
            logger.warning("notification_failed", error=str(e))

        logger.info("voice_input_broadcast", input_id=voice_input.id)

    def register_session(
        self,
        session_id: str,
        pid: int,
        working_dir: str,
        capabilities: Optional[List[str]] = None,
    ) -> bool:
        """Register a Claude Code session for voice input.

        Args:
            session_id: Unique session identifier
            pid: Process ID of Claude Code
            working_dir: Working directory of the session
            capabilities: List of capabilities this session handles

        Returns:
            True if registration successful
        """
        session = ClaudeSession(
            session_id=session_id,
            pid=pid,
            registered_at=datetime.now().isoformat(),
            last_heartbeat=datetime.now().isoformat(),
            working_dir=working_dir,
            capabilities=capabilities or [],
        )

        self._active_sessions[session_id] = session
        self._save_state()

        logger.info(
            "claude_session_registered",
            session_id=session_id,
            pid=pid,
            capabilities=capabilities,
        )

        return True

    def heartbeat(self, session_id: str) -> bool:
        """Update heartbeat for a session.

        Args:
            session_id: Session to update

        Returns:
            True if session exists
        """
        if session_id in self._active_sessions:
            self._active_sessions[session_id].last_heartbeat = datetime.now().isoformat()
            return True
        return False

    def unregister_session(self, session_id: str) -> bool:
        """Unregister a Claude Code session.

        Args:
            session_id: Session to unregister

        Returns:
            True if session was registered
        """
        if session_id in self._active_sessions:
            del self._active_sessions[session_id]
            self._save_state()
            logger.info("claude_session_unregistered", session_id=session_id)
            return True
        return False

    def get_pending_inputs(
        self,
        session_id: Optional[str] = None,
        only_directed: bool = True,
        limit: int = 10,
    ) -> List[VoiceInput]:
        """Get pending voice inputs.

        Args:
            session_id: Filter by unclaimed or claimed by this session
            only_directed: Only return inputs directed at Pixel
            limit: Maximum number of inputs to return

        Returns:
            List of pending VoiceInputs
        """
        now = datetime.now()
        results = []

        for inp in self._pending_inputs:
            # Skip processed inputs
            if inp.processed:
                continue

            # Skip inputs claimed by other sessions
            if inp.claimed_by and inp.claimed_by != session_id:
                continue

            # Filter by directed status
            if only_directed and not inp.is_directed:
                continue

            # Check TTL
            try:
                input_time = datetime.fromisoformat(inp.timestamp)
                if (now - input_time).total_seconds() > self.input_ttl_seconds:
                    continue
            except (ValueError, TypeError):
                continue

            results.append(inp)

            if len(results) >= limit:
                break

        return results

    def claim_input(self, input_id: str, session_id: str) -> Optional[VoiceInput]:
        """Claim a voice input for processing.

        Args:
            input_id: Input to claim
            session_id: Session claiming the input

        Returns:
            The claimed VoiceInput or None
        """
        for inp in self._pending_inputs:
            if inp.id == input_id and not inp.claimed_by:
                inp.claimed_by = session_id
                inp.claimed_at = datetime.now().isoformat()
                self._save_state()
                logger.info(
                    "voice_input_claimed",
                    input_id=input_id,
                    session_id=session_id,
                )
                return inp
        return None

    def mark_processed(self, input_id: str, session_id: str) -> bool:
        """Mark an input as processed.

        Args:
            input_id: Input to mark
            session_id: Session that processed it

        Returns:
            True if successful
        """
        for inp in self._pending_inputs:
            if inp.id == input_id and inp.claimed_by == session_id:
                inp.processed = True
                self._processed_count += 1
                self._save_state()
                logger.info(
                    "voice_input_processed",
                    input_id=input_id,
                    session_id=session_id,
                )
                return True
        return False

    def cleanup_stale(self) -> int:
        """Remove stale inputs and sessions.

        Returns:
            Number of items cleaned up
        """
        now = datetime.now()
        cleaned = 0

        # Clean up stale inputs
        active_inputs = deque(maxlen=self.max_pending_inputs)
        for inp in self._pending_inputs:
            try:
                input_time = datetime.fromisoformat(inp.timestamp)
                age = (now - input_time).total_seconds()
                if age <= self.input_ttl_seconds and not inp.processed:
                    active_inputs.append(inp)
                else:
                    cleaned += 1
            except (ValueError, TypeError):
                cleaned += 1

        self._pending_inputs = active_inputs

        # Clean up stale sessions
        stale_sessions = []
        for session_id, session in self._active_sessions.items():
            try:
                last_beat = datetime.fromisoformat(session.last_heartbeat)
                if (now - last_beat).total_seconds() > self.session_timeout_seconds:
                    stale_sessions.append(session_id)
            except (ValueError, TypeError):
                stale_sessions.append(session_id)

        for session_id in stale_sessions:
            del self._active_sessions[session_id]
            cleaned += 1

        if cleaned > 0:
            self._save_state()
            logger.info("voice_router_cleanup", cleaned=cleaned)

        return cleaned

    def get_active_sessions(self) -> List[ClaudeSession]:
        """Get list of active Claude Code sessions.

        Returns:
            List of active sessions
        """
        return list(self._active_sessions.values())

    def detect_claude_sessions(self) -> List[Dict[str, Any]]:
        """Detect running Claude Code processes.

        Returns:
            List of detected Claude Code processes
        """
        detected = []

        try:
            result = subprocess.run(
                ["pgrep", "-fa", "claude"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split(maxsplit=1)
                if len(parts) < 2:
                    continue

                pid = int(parts[0])
                cmd = parts[1]

                # Filter for actual Claude Code sessions
                if "claude" in cmd and ("--dangerously-skip-permissions" in cmd or cmd.strip().endswith("claude")):
                    # Skip MCP server processes
                    if "mcp-server" in cmd or "node" in cmd:
                        continue

                    # Get working directory
                    try:
                        cwd = os.readlink(f"/proc/{pid}/cwd")
                    except (OSError, FileNotFoundError):
                        cwd = "unknown"

                    detected.append({
                        "pid": pid,
                        "command": cmd,
                        "working_dir": cwd,
                    })

        except Exception as e:
            logger.error("detect_claude_sessions_error", error=str(e))

        return detected

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "enabled": self.enabled,
            "pending_inputs": len(self._pending_inputs),
            "active_sessions": len(self._active_sessions),
            "processed_count": self._processed_count,
            "detected_claude_processes": len(self.detect_claude_sessions()),
        }


# Convenience function for Claude Code sessions
def get_pending_voice_inputs(only_directed: bool = True) -> List[Dict]:
    """Get pending voice inputs for Claude Code.

    This can be called from Claude Code slash commands or hooks.

    Args:
        only_directed: Only return inputs directed at Pixel

    Returns:
        List of pending voice inputs as dictionaries
    """
    try:
        if not VOICE_INPUT_FILE.exists():
            return []

        with open(VOICE_INPUT_FILE) as f:
            data = json.load(f)

        results = []
        for inp in data.get("pending", []):
            if inp.get("processed"):
                continue
            if only_directed and not inp.get("is_directed"):
                continue
            results.append(inp)

        return results
    except Exception:
        return []


def get_latest_broadcast() -> Optional[Dict]:
    """Get the latest broadcast voice input.

    This can be used by Claude Code hooks to check for recent voice input.

    Returns:
        Latest broadcast or None
    """
    try:
        if not VOICE_BROADCAST_FILE.exists():
            return None

        with open(VOICE_BROADCAST_FILE) as f:
            data = json.load(f)

        # Check if broadcast is recent (within 30 seconds)
        broadcast_at = datetime.fromisoformat(data.get("broadcast_at", ""))
        if (datetime.now() - broadcast_at).total_seconds() > 30:
            return None

        return data
    except Exception:
        return None
