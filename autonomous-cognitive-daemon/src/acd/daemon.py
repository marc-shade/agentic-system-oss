#!/usr/bin/env python3
"""
Autonomous Cognitive Daemon - Main Entry Point
===============================================

Pixel's Always-On Brain - The daemon that never stops thinking.

This daemon runs continuously between user sessions to:
- Monitor and advance active goals
- Research high-severity knowledge gaps
- Curate and consolidate memory
- Coordinate cluster resources
- Prepare context for upcoming sessions

"What happens when the AI never stops thinking? This."
"""

import asyncio
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .scheduler import Scheduler, TaskPriority
from .utils.config import load_config, get_config_value
from .utils.logging import setup_logging, get_logger

# Components (lazy import to avoid circular deps)
from .components.goal_monitor import GoalMonitor
from .components.gap_researcher import GapResearcher
from .components.memory_curator import MemoryCurator
from .components.cluster_coordinator import ClusterCoordinator
from .components.session_preparer import SessionPreparer
from .components.proactive_notifier import ProactiveNotifier, NotificationPriority
from .components.linux_os_controller import LinuxOSController
from .components.environmental_listener import EnvironmentalListener, VoiceModeIntegration
from .components.voice_input_router import VoiceInputRouter


logger = get_logger(__name__)


class AutonomousCognitiveDaemon:
    """
    The Autonomous Cognitive Daemon - Pixel's continuous cognitive process.

    Orchestrates all components through a scheduler, handling:
    - Recurring cognitive tasks (goal monitoring, memory consolidation)
    - Event-triggered tasks (new knowledge gaps, session start)
    - Background processing (research, cluster coordination)
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the daemon.

        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = load_config(config_path)

        # Setup logging
        log_file = self.config.get("daemon", {}).get("log_file")
        log_level = self.config.get("daemon", {}).get("log_level", "INFO")
        setup_logging(log_file=log_file, log_level=log_level)

        logger.info("initializing_daemon", version="0.1.0")

        # Initialize scheduler
        self.scheduler = Scheduler(max_concurrent=3)

        # Initialize components
        self._init_components()

        # State
        self._running = False
        self._start_time: Optional[datetime] = None

        logger.info("daemon_initialized")

    def _init_components(self) -> None:
        """Initialize all daemon components."""
        components_config = self.config.get("components", {})

        # Goal Monitor
        if components_config.get("goal_monitor", {}).get("enabled", True):
            self.goal_monitor = GoalMonitor(self.config)
            logger.info("component_initialized", component="goal_monitor")
        else:
            self.goal_monitor = None

        # Knowledge Gap Researcher
        if components_config.get("gap_researcher", {}).get("enabled", True):
            self.gap_researcher = GapResearcher(self.config)
            logger.info("component_initialized", component="gap_researcher")
        else:
            self.gap_researcher = None

        # Memory Curator
        if components_config.get("memory_curator", {}).get("enabled", True):
            self.memory_curator = MemoryCurator(self.config)
            logger.info("component_initialized", component="memory_curator")
        else:
            self.memory_curator = None

        # Cluster Coordinator
        if components_config.get("cluster_coordinator", {}).get("enabled", True):
            self.cluster_coordinator = ClusterCoordinator(self.config)
            logger.info("component_initialized", component="cluster_coordinator")
        else:
            self.cluster_coordinator = None

        # Session Preparer
        if components_config.get("session_preparer", {}).get("enabled", True):
            self.session_preparer = SessionPreparer(self.config)
            logger.info("component_initialized", component="session_preparer")
        else:
            self.session_preparer = None

        # Proactive Notifier
        if components_config.get("proactive_notifier", {}).get("enabled", True):
            self.notifier = ProactiveNotifier(self.config)
            logger.info("component_initialized", component="proactive_notifier")
        else:
            self.notifier = None

        # Linux OS Controller (deep OS integration)
        if components_config.get("linux_os_controller", {}).get("enabled", True):
            self.os_controller = LinuxOSController(self.config)
            logger.info("component_initialized", component="linux_os_controller")
        else:
            self.os_controller = None

        # Environmental Listener ("the mics are my ears")
        if components_config.get("environmental_listener", {}).get("enabled", True):
            self.env_listener = EnvironmentalListener(self.config)
            self.voice_integration = VoiceModeIntegration(self.env_listener)
            # Register handler for directed speech
            self.env_listener.register_speech_handler(self._handle_directed_speech)
            logger.info("component_initialized", component="environmental_listener")
        else:
            self.env_listener = None
            self.voice_integration = None

        # Voice Input Router (routes STT to Claude Code sessions)
        if components_config.get("voice_input_router", {}).get("enabled", True):
            self.voice_router = VoiceInputRouter(self.config)
            logger.info("component_initialized", component="voice_input_router")
        else:
            self.voice_router = None

    def _schedule_tasks(self) -> None:
        """Schedule all recurring tasks."""
        scheduling = self.config.get("scheduling", {})

        # Goal monitoring with notifications - every 5 minutes
        if self.goal_monitor:
            interval = scheduling.get("goal_check_minutes", 5) * 60
            self.scheduler.add_recurring_task(
                name="Goal Monitor Check",
                coroutine_factory=self._check_goals_with_notification,
                interval_seconds=interval,
                priority=TaskPriority.HIGH,
                initial_delay_seconds=30,  # Start after 30s
            )

        # Knowledge gap research with notifications - every 4 hours
        if self.gap_researcher:
            interval = scheduling.get("gap_research_hours", 4) * 3600
            self.scheduler.add_recurring_task(
                name="Knowledge Gap Research",
                coroutine_factory=self._research_gaps_with_notification,
                interval_seconds=interval,
                priority=TaskPriority.NORMAL,
                initial_delay_seconds=120,  # Start after 2 min
            )

        # Memory consolidation with notifications - every 6 hours
        if self.memory_curator:
            interval = scheduling.get("memory_consolidation_hours", 6) * 3600
            self.scheduler.add_recurring_task(
                name="Memory Consolidation",
                coroutine_factory=self._consolidate_memory_with_notification,
                interval_seconds=interval,
                priority=TaskPriority.LOW,
                initial_delay_seconds=300,  # Start after 5 min
            )

        # Cluster health check with notifications - every 10 minutes
        if self.cluster_coordinator:
            interval = self.config.get("components", {}).get(
                "cluster_coordinator", {}
            ).get("health_check_interval_minutes", 10) * 60
            self.scheduler.add_recurring_task(
                name="Cluster Health Check",
                coroutine_factory=self._check_cluster_with_notification,
                interval_seconds=interval,
                priority=TaskPriority.BACKGROUND,
                initial_delay_seconds=60,
            )

        # Session preparation with notifications
        if self.session_preparer and scheduling.get("session_prep_enabled", True):
            # Prepare a briefing every 2 hours
            interval = scheduling.get("main_cycle_hours", 2) * 3600
            self.scheduler.add_recurring_task(
                name="Session Briefing Update",
                coroutine_factory=self._prepare_briefing_with_notification,
                interval_seconds=interval,
                priority=TaskPriority.NORMAL,
                initial_delay_seconds=180,
            )

        # Notification batch flush - every 30 minutes
        if self.notifier:
            self.scheduler.add_recurring_task(
                name="Notification Batch Flush",
                coroutine_factory=self.notifier.send_batch,
                interval_seconds=1800,  # 30 minutes
                priority=TaskPriority.BACKGROUND,
                initial_delay_seconds=600,
            )

        # System state monitoring - every 5 minutes
        if self.os_controller:
            self.scheduler.add_recurring_task(
                name="System State Snapshot",
                coroutine_factory=self._take_system_snapshot,
                interval_seconds=300,  # 5 minutes
                priority=TaskPriority.BACKGROUND,
                initial_delay_seconds=60,
            )

        logger.info("tasks_scheduled", count=len(self.scheduler._tasks))

    async def start(self) -> None:
        """Start the daemon."""
        self._running = True
        self._start_time = datetime.now()

        logger.info(
            "daemon_starting",
            pid=os.getpid(),
            start_time=self._start_time.isoformat(),
        )

        # Print startup banner
        self._print_banner()

        # Schedule tasks
        self._schedule_tasks()

        # Send startup notification
        if self.notifier:
            asyncio.create_task(self._send_startup_notification())

        # Start environmental listener (Pixel's ears)
        if self.env_listener:
            asyncio.create_task(self._start_environmental_listener())

        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self.stop)

        # Run scheduler
        try:
            await self.scheduler.start()
        except asyncio.CancelledError:
            logger.info("daemon_cancelled")
        finally:
            await self._cleanup()

    def stop(self) -> None:
        """Stop the daemon gracefully."""
        logger.info("daemon_stopping")
        self._running = False
        self.scheduler.stop()

    async def _cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("daemon_cleanup")

        # Stop environmental listener
        if self.env_listener:
            await self.env_listener.stop()

        uptime = None
        if self._start_time:
            uptime = (datetime.now() - self._start_time).total_seconds()

        # Get final stats
        status = self.get_status()

        logger.info(
            "daemon_stopped",
            uptime_seconds=uptime,
            tasks_run=sum(
                t.get("run_count", 0) for t in status.get("scheduler", {}).get("tasks", {}).values()
            ),
        )

    async def _send_startup_notification(self) -> None:
        """Send notification that daemon has started."""
        if self.notifier:
            await self.notifier.notify(
                title="Pixel ACD Online",
                message="Autonomous Cognitive Daemon is now running. I'm thinking even when you're not here!",
                priority=NotificationPriority.NORMAL,
                source="Daemon",
                category="system",
            )

    async def _check_goals_with_notification(self) -> dict:
        """Check goals and send notification for stalled ones."""
        if not self.goal_monitor:
            return {}

        result = await self.goal_monitor.check_goals()

        # Send notifications for stalled goals
        if self.notifier and result.get("stalled_goals"):
            for goal in result["stalled_goals"]:
                await self.notifier.notify_goal_stalled(
                    goal_name=goal.get("name", "Unknown"),
                    task_count=goal.get("pending_tasks", 0),
                )

        return result

    async def _check_cluster_with_notification(self) -> dict:
        """Check cluster health and notify on issues."""
        if not self.cluster_coordinator:
            return {}

        result = await self.cluster_coordinator.check_health()

        # Send notifications for cluster issues
        if self.notifier and result.get("issues"):
            for issue in result["issues"]:
                await self.notifier.notify_cluster_issue(
                    node_name=issue.get("node", "unknown"),
                    issue=issue.get("message", "Unknown issue"),
                    severity=issue.get("severity", "normal"),
                )

        return result

    async def _consolidate_memory_with_notification(self) -> dict:
        """Consolidate memory and notify on completion."""
        if not self.memory_curator:
            return {}

        result = await self.memory_curator.consolidate()

        # Send notification for consolidation completion
        if self.notifier and not result.get("errors"):
            patterns_found = result.get("stages", {}).get("pattern_extraction", {}).get("patterns_found", 0)
            compressed = result.get("stages", {}).get("compression", {}).get("memories_compressed", 0)
            await self.notifier.notify_consolidation_complete(
                patterns_found=patterns_found,
                memories_compressed=compressed,
            )

        return result

    async def _prepare_briefing_with_notification(self) -> dict:
        """Prepare session briefing and notify when ready."""
        if not self.session_preparer:
            return {}

        result = await self.session_preparer.prepare_briefing()

        # Send notification that briefing is ready
        if self.notifier:
            agenda_count = len(result.get("agenda", []))
            if agenda_count > 0:
                await self.notifier.notify_session_ready(agenda_items=agenda_count)

        return result

    async def _research_gaps_with_notification(self) -> dict:
        """Research knowledge gaps and notify on critical ones."""
        if not self.gap_researcher:
            return {}

        result = await self.gap_researcher.research_gaps()

        # Notify about critical gaps found
        if self.notifier:
            for gap in result.get("researched_gaps", []):
                if gap.get("severity", 0) >= 0.8:
                    await self.notifier.notify_knowledge_gap_critical(
                        domain=gap.get("domain", "unknown"),
                        description=gap.get("description", ""),
                        severity=gap.get("severity", 0),
                    )

        return result

    async def _take_system_snapshot(self) -> dict:
        """Take a system state snapshot and log relevant changes."""
        if not self.os_controller:
            return {}

        try:
            snapshot = await self.os_controller.take_snapshot()

            logger.info(
                "system_snapshot",
                display_state=snapshot.display_state,
                idle_seconds=snapshot.idle_time_seconds,
                audio_muted=snapshot.audio_muted,
                network=snapshot.network_connected,
            )

            # If user has been idle for >30 minutes, note it
            if snapshot.idle_time_seconds > 1800:
                logger.debug("user_idle_extended", idle_seconds=snapshot.idle_time_seconds)

            return {
                "timestamp": snapshot.timestamp.isoformat(),
                "display_state": snapshot.display_state,
                "idle_seconds": snapshot.idle_time_seconds,
                "network_connected": snapshot.network_connected,
            }

        except Exception as e:
            logger.warning("system_snapshot_failed", error=str(e))
            return {"error": str(e)}

    async def _handle_directed_speech(self, event) -> None:
        """Handle speech that is directed at Pixel.

        This is called when someone says "Pixel" or "Hey Pixel" etc.
        Routes the speech to active Claude Code sessions via VoiceInputRouter.

        Args:
            event: AudioEvent with the detected speech
        """
        logger.info(
            "directed_speech_received",
            text=event.text[:100] if event.text else "",
            confidence=event.confidence,
        )

        # Route to Claude Code sessions via VoiceInputRouter
        if self.voice_router:
            input_id = await self.voice_router.route_audio_event(event)
            logger.info(
                "speech_routed_to_sessions",
                input_id=input_id,
                detected_sessions=len(self.voice_router.detect_claude_sessions()),
            )

        # Send notification if notifier is available
        if self.notifier:
            await self.notifier.notify(
                title="Voice Input",
                message=f"Marc said: {event.text[:100]}",
                priority=NotificationPriority.INFO,
                source="VoiceInputRouter",
                category="speech",
            )

    async def _start_environmental_listener(self) -> None:
        """Start the environmental listener for audio awareness."""
        if self.env_listener:
            started = await self.env_listener.start()
            if started:
                logger.info("environmental_listener_started")
            else:
                logger.warning("environmental_listener_failed_to_start")

    async def is_user_available(self) -> bool:
        """Check if user is available for notifications.

        Returns:
            True if user is active and screen not locked
        """
        if not self.os_controller:
            return True  # Assume available if no controller

        try:
            # Check if screen is locked
            if await self.os_controller.is_screen_locked():
                return False

            # Check if user has been active recently (last 10 minutes)
            return await self.os_controller.is_user_active(threshold_seconds=600)

        except Exception:
            return True  # Default to available on error

    def _print_banner(self) -> None:
        """Print startup banner."""
        banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║      ██████╗ ██╗██╗  ██╗███████╗██╗         █████╗  ██████╗██████╗║
║      ██╔══██╗██║╚██╗██╔╝██╔════╝██║        ██╔══██╗██╔════╝██╔══██╗
║      ██████╔╝██║ ╚███╔╝ █████╗  ██║        ███████║██║     ██║  ██║
║      ██╔═══╝ ██║ ██╔██╗ ██╔══╝  ██║        ██╔══██║██║     ██║  ██║
║      ██║     ██║██╔╝ ██╗███████╗███████╗   ██║  ██║╚██████╗██████╔╝
║      ╚═╝     ╚═╝╚═╝  ╚═╝╚══════╝╚══════╝   ╚═╝  ╚═╝ ╚═════╝╚═════╝║
║                                                                   ║
║           AUTONOMOUS COGNITIVE DAEMON v0.1.0                      ║
║           "The brain that never stops thinking"                   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
        print(banner)

    def get_status(self) -> dict:
        """Get daemon status.

        Returns:
            Status dictionary
        """
        return {
            "running": self._running,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds()
            if self._start_time
            else None,
            "scheduler": self.scheduler.get_status(),
            "components": {
                "goal_monitor": self.goal_monitor is not None,
                "gap_researcher": self.gap_researcher is not None,
                "memory_curator": self.memory_curator is not None,
                "cluster_coordinator": self.cluster_coordinator is not None,
                "session_preparer": self.session_preparer is not None,
                "proactive_notifier": self.notifier is not None,
                "linux_os_controller": self.os_controller is not None,
                "environmental_listener": self.env_listener is not None,
            },
            "notifier_stats": self.notifier.get_stats() if self.notifier else None,
            "os_controller_stats": self.os_controller.get_stats() if self.os_controller else None,
            "env_listener_stats": self.env_listener.get_stats() if self.env_listener else None,
        }


def main():
    """Main entry point."""
    # Check for config path argument
    config_path = None
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    # Create and run daemon
    daemon = AutonomousCognitiveDaemon(config_path)

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    except Exception as e:
        logger.error("daemon_crash", error=str(e))
        sys.exit(1)


def status():
    """Print daemon status (for systemd)."""
    # This would read from a status file or socket
    print("Daemon status check - implementation pending")


if __name__ == "__main__":
    main()
