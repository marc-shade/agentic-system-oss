"""Proactive Notifier - Sends notifications to Marc via desktop and voice."""

import asyncio
import json
import platform
import subprocess
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from ..utils.config import get_path, get_config_value
from ..utils.logging import get_logger


logger = get_logger(__name__)


def detect_os() -> str:
    """Detect the current operating system.

    Returns:
        One of: 'linux', 'darwin' (macOS), 'windows'
    """
    system = platform.system().lower()
    if system == "darwin":
        return "darwin"
    elif system == "windows":
        return "windows"
    else:
        return "linux"  # Default to Linux for BSD, etc.


class NotificationPriority(Enum):
    """Notification priority levels."""
    INFO = 1       # Low importance, desktop only
    NORMAL = 2     # Standard notifications
    HIGH = 3       # Important - desktop + optional voice
    URGENT = 4     # Critical - desktop + voice immediately
    CRITICAL = 5   # Emergency - all channels, repeat if needed


@dataclass
class Notification:
    """A notification to send."""
    title: str
    message: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    source: str = "ACD"
    timestamp: datetime = field(default_factory=datetime.now)
    category: str = "general"
    data: Optional[Dict[str, Any]] = None
    sent_desktop: bool = False
    sent_voice: bool = False


class ProactiveNotifier:
    """
    Sends proactive notifications via multiple channels.

    Channels:
    - Desktop: notify-send (libnotify) for visual notifications
    - Voice: voice-mode MCP for spoken alerts
    - File: JSON log for history and review

    Features:
    - Rate limiting to prevent notification spam
    - Priority-based channel selection
    - Notification batching for low-priority items
    - History tracking for deduplication
    """

    def __init__(self, config: dict):
        """Initialize Proactive Notifier.

        Args:
            config: Daemon configuration
        """
        self.config = config

        # Configuration
        notifier_config = config.get("components", {}).get("proactive_notifier", {})

        self.enabled = notifier_config.get("enabled", True)
        self.voice_enabled = notifier_config.get("voice_enabled", True)
        self.desktop_enabled = notifier_config.get("desktop_enabled", True)

        # Rate limiting
        self.min_interval_seconds = notifier_config.get("min_interval_seconds", 30)
        self.max_per_hour = notifier_config.get("max_per_hour", 20)

        # Voice settings
        self.voice_host = notifier_config.get("voice_host", "localhost")
        self.voice_port = notifier_config.get("voice_port", 8765)

        # Storage
        self.notification_log_path = Path(
            notifier_config.get(
                "log_path",
                "/mnt/agentic-system/autonomous-cognitive-daemon/notifications.json"
            )
        )

        # State
        self._notification_history: List[Notification] = []
        self._last_notification_time: Optional[datetime] = None
        self._pending_batch: List[Notification] = []

        # Environment for Wayland desktop notifications
        self._display_env = self._get_display_env()

        logger.info(
            "proactive_notifier_initialized",
            desktop_enabled=self.desktop_enabled,
            voice_enabled=self.voice_enabled,
            rate_limit=f"{self.max_per_hour}/hour",
        )

    def _get_display_env(self) -> Dict[str, str]:
        """Get environment variables for desktop notifications on Wayland."""
        import os
        env = os.environ.copy()

        # Required for Wayland notifications
        if "WAYLAND_DISPLAY" not in env:
            env["WAYLAND_DISPLAY"] = "wayland-0"
        if "XDG_RUNTIME_DIR" not in env:
            env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        if "DBUS_SESSION_BUS_ADDRESS" not in env:
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path=/run/user/{os.getuid()}/bus"

        return env

    async def notify(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        source: str = "ACD",
        category: str = "general",
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send a notification.

        Args:
            title: Notification title
            message: Notification body
            priority: Priority level
            source: Source component
            category: Category for filtering
            data: Additional data

        Returns:
            True if notification was sent
        """
        if not self.enabled:
            logger.debug("notifications_disabled", title=title)
            return False

        notification = Notification(
            title=title,
            message=message,
            priority=priority,
            source=source,
            category=category,
            data=data,
        )

        # Check rate limiting
        if not self._check_rate_limit(notification):
            if priority.value < NotificationPriority.HIGH.value:
                # Batch low-priority notifications
                self._pending_batch.append(notification)
                logger.debug("notification_batched", title=title)
                return False

        # Send based on priority
        success = await self._send_notification(notification)

        if success:
            self._notification_history.append(notification)
            self._last_notification_time = datetime.now()
            await self._save_to_log(notification)

        return success

    def _check_rate_limit(self, notification: Notification) -> bool:
        """Check if notification can be sent under rate limits.

        Args:
            notification: Notification to check

        Returns:
            True if rate limit allows sending
        """
        # CRITICAL and URGENT always go through
        if notification.priority.value >= NotificationPriority.URGENT.value:
            return True

        # Check minimum interval
        if self._last_notification_time:
            elapsed = (datetime.now() - self._last_notification_time).total_seconds()
            if elapsed < self.min_interval_seconds:
                return False

        # Check hourly limit
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_count = sum(
            1 for n in self._notification_history
            if n.timestamp > one_hour_ago
        )

        if recent_count >= self.max_per_hour:
            return False

        return True

    async def _send_notification(self, notification: Notification) -> bool:
        """Send notification through appropriate channels.

        Args:
            notification: Notification to send

        Returns:
            True if any channel succeeded
        """
        success = False

        # Desktop notification
        if self.desktop_enabled:
            desktop_success = await self._send_desktop(notification)
            notification.sent_desktop = desktop_success
            success = success or desktop_success

        # Voice notification for HIGH+ priority
        if (
            self.voice_enabled
            and notification.priority.value >= NotificationPriority.HIGH.value
        ):
            voice_success = await self._send_voice(notification)
            notification.sent_voice = voice_success
            success = success or voice_success

        logger.info(
            "notification_sent",
            title=notification.title,
            priority=notification.priority.name,
            desktop=notification.sent_desktop,
            voice=notification.sent_voice,
        )

        return success

    async def _send_desktop(self, notification: Notification) -> bool:
        """Send desktop notification via notify-send.

        Args:
            notification: Notification to send

        Returns:
            True if successful
        """
        try:
            # Map priority to urgency
            urgency_map = {
                NotificationPriority.INFO: "low",
                NotificationPriority.NORMAL: "normal",
                NotificationPriority.HIGH: "normal",
                NotificationPriority.URGENT: "critical",
                NotificationPriority.CRITICAL: "critical",
            }
            urgency = urgency_map.get(notification.priority, "normal")

            # Map priority to timeout
            timeout_map = {
                NotificationPriority.INFO: 5000,
                NotificationPriority.NORMAL: 8000,
                NotificationPriority.HIGH: 10000,
                NotificationPriority.URGENT: 0,  # No timeout
                NotificationPriority.CRITICAL: 0,
            }
            timeout = timeout_map.get(notification.priority, 8000)

            # Build command
            cmd = [
                "notify-send",
                f"--urgency={urgency}",
                f"--expire-time={timeout}",
                f"--app-name=Pixel-ACD",
                "--icon=dialog-information",
                f"🐕 {notification.title}",
                notification.message,
            ]

            # Run async
            process = await asyncio.create_subprocess_exec(
                *cmd,
                env=self._display_env,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )

            _, stderr = await process.communicate()

            if process.returncode != 0:
                logger.warning(
                    "desktop_notification_failed",
                    error=stderr.decode() if stderr else "Unknown error",
                )
                return False

            return True

        except Exception as e:
            logger.error("desktop_notification_error", error=str(e))
            return False

    async def _send_voice(self, notification: Notification) -> bool:
        """Send voice notification via voice-mode MCP.

        Args:
            notification: Notification to send

        Returns:
            True if successful
        """
        try:
            # Build spoken message
            prefix_map = {
                NotificationPriority.HIGH: "Attention Marc:",
                NotificationPriority.URGENT: "Urgent notification:",
                NotificationPriority.CRITICAL: "Critical alert Marc:",
            }
            prefix = prefix_map.get(notification.priority, "")

            spoken_text = f"{prefix} {notification.title}. {notification.message}"

            # Call voice-mode MCP via unix socket or HTTP
            # Using the speak tool from voice-mode MCP
            voice_cmd = [
                "curl", "-s", "-X", "POST",
                f"http://{self.voice_host}:{self.voice_port}/speak",
                "-H", "Content-Type: application/json",
                "-d", json.dumps({"text": spoken_text, "voice": "en-IE-EmilyNeural"}),
            ]

            # Try direct MCP call first using Claude's MCP infrastructure
            # Fall back to edge-tts direct if MCP unavailable
            try:
                edge_tts_cmd = [
                    "edge-tts",
                    "--voice", "en-IE-EmilyNeural",
                    "--text", spoken_text,
                    "--write-media", "/tmp/pixel_notification.mp3",
                ]

                process = await asyncio.create_subprocess_exec(
                    *edge_tts_cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )

                _, stderr = await process.communicate()

                if process.returncode == 0:
                    # Play the audio
                    play_cmd = ["mpv", "--no-terminal", "/tmp/pixel_notification.mp3"]
                    play_process = await asyncio.create_subprocess_exec(
                        *play_cmd,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await play_process.communicate()
                    return True

            except FileNotFoundError:
                logger.debug("edge_tts_not_found_trying_espeak")

            # Fallback to espeak
            espeak_cmd = ["espeak", "-v", "en", spoken_text]
            process = await asyncio.create_subprocess_exec(
                *espeak_cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await process.communicate()
            return process.returncode == 0

        except Exception as e:
            logger.warning("voice_notification_error", error=str(e))
            return False

    async def _save_to_log(self, notification: Notification) -> None:
        """Save notification to JSON log.

        Args:
            notification: Notification to save
        """
        try:
            # Load existing log
            log_data = []
            if self.notification_log_path.exists():
                with open(self.notification_log_path) as f:
                    log_data = json.load(f)

            # Add new notification
            log_data.append({
                "timestamp": notification.timestamp.isoformat(),
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.name,
                "source": notification.source,
                "category": notification.category,
                "sent_desktop": notification.sent_desktop,
                "sent_voice": notification.sent_voice,
                "data": notification.data,
            })

            # Keep last 1000 notifications
            log_data = log_data[-1000:]

            # Save
            with open(self.notification_log_path, "w") as f:
                json.dump(log_data, f, indent=2)

        except Exception as e:
            logger.warning("notification_log_error", error=str(e))

    async def send_batch(self) -> int:
        """Send batched low-priority notifications as summary.

        Returns:
            Number of notifications in batch
        """
        if not self._pending_batch:
            return 0

        count = len(self._pending_batch)

        # Create summary notification
        summary_title = f"{count} Notifications"
        summary_messages = [f"• {n.title}" for n in self._pending_batch[:5]]
        if count > 5:
            summary_messages.append(f"... and {count - 5} more")

        summary_message = "\n".join(summary_messages)

        notification = Notification(
            title=summary_title,
            message=summary_message,
            priority=NotificationPriority.INFO,
            source="ACD-Batch",
            category="batch",
        )

        await self._send_notification(notification)

        # Clear batch
        self._pending_batch.clear()

        return count

    async def notify_goal_stalled(self, goal_name: str, task_count: int) -> bool:
        """Notify about a stalled goal.

        Args:
            goal_name: Name of stalled goal
            task_count: Number of pending tasks

        Returns:
            True if notification sent
        """
        return await self.notify(
            title=f"Goal Stalled: {goal_name}",
            message=f"Goal has {task_count} pending tasks with no recent progress.",
            priority=NotificationPriority.HIGH,
            source="GoalMonitor",
            category="goals",
            data={"goal_name": goal_name, "pending_tasks": task_count},
        )

    async def notify_knowledge_gap_critical(
        self, domain: str, description: str, severity: float
    ) -> bool:
        """Notify about a critical knowledge gap.

        Args:
            domain: Knowledge domain
            description: Gap description
            severity: Severity score

        Returns:
            True if notification sent
        """
        return await self.notify(
            title=f"Critical Knowledge Gap: {domain}",
            message=f"Severity {severity:.1f}: {description[:100]}",
            priority=NotificationPriority.NORMAL,
            source="GapResearcher",
            category="learning",
            data={"domain": domain, "severity": severity},
        )

    async def notify_cluster_issue(
        self, node_name: str, issue: str, severity: str
    ) -> bool:
        """Notify about a cluster issue.

        Args:
            node_name: Affected node
            issue: Issue description
            severity: Issue severity

        Returns:
            True if notification sent
        """
        priority = (
            NotificationPriority.URGENT
            if severity == "critical"
            else NotificationPriority.HIGH
        )

        return await self.notify(
            title=f"Cluster Alert: {node_name}",
            message=issue,
            priority=priority,
            source="ClusterCoordinator",
            category="cluster",
            data={"node": node_name, "severity": severity},
        )

    async def notify_consolidation_complete(
        self, patterns_found: int, memories_compressed: int
    ) -> bool:
        """Notify about completed memory consolidation.

        Args:
            patterns_found: Number of patterns extracted
            memories_compressed: Number of memories compressed

        Returns:
            True if notification sent
        """
        return await self.notify(
            title="Memory Consolidation Complete",
            message=f"Found {patterns_found} patterns, compressed {memories_compressed} memories.",
            priority=NotificationPriority.INFO,
            source="MemoryCurator",
            category="memory",
            data={"patterns": patterns_found, "compressed": memories_compressed},
        )

    async def notify_session_ready(self, agenda_items: int) -> bool:
        """Notify that session briefing is ready.

        Args:
            agenda_items: Number of agenda items

        Returns:
            True if notification sent
        """
        return await self.notify(
            title="Session Briefing Ready",
            message=f"Prepared {agenda_items} agenda items for your next session.",
            priority=NotificationPriority.INFO,
            source="SessionPreparer",
            category="session",
            data={"agenda_items": agenda_items},
        )

    async def test_notification(self) -> bool:
        """Send a test notification to verify setup.

        Returns:
            True if test notification sent successfully
        """
        return await self.notify(
            title="Test Notification",
            message="If you see this, Pixel's notification system is working!",
            priority=NotificationPriority.NORMAL,
            source="NotifierTest",
            category="test",
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics.

        Returns:
            Statistics dictionary
        """
        one_hour_ago = datetime.now() - timedelta(hours=1)
        one_day_ago = datetime.now() - timedelta(days=1)

        return {
            "enabled": self.enabled,
            "voice_enabled": self.voice_enabled,
            "desktop_enabled": self.desktop_enabled,
            "total_sent": len(self._notification_history),
            "sent_last_hour": sum(
                1 for n in self._notification_history if n.timestamp > one_hour_ago
            ),
            "sent_last_day": sum(
                1 for n in self._notification_history if n.timestamp > one_day_ago
            ),
            "pending_batch": len(self._pending_batch),
            "last_notification": (
                self._last_notification_time.isoformat()
                if self._last_notification_time
                else None
            ),
        }
