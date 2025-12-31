#!/usr/bin/env python3
"""
Visual AGI Daemon - Unified Visual Intelligence System

Orchestrates all Visual AGI components:
- Visual Perception (multi-provider capture and analysis)
- Visual Memory (storage, retrieval, knowledge graph)
- Cross-Modal Integration (visual + text + code correlation)
- Visual Reasoning (decision-making with visual context)
- Visual Alerting (change detection and notification)
- Visual-Code Correlation (linking code to visual outcomes)
- Visual Learning (continuous improvement loop)

Integrates with:
- Voice Mode MCP (audible notifications)
- Arduino Surface MCP (physical feedback)
- Enhanced Memory MCP (persistent knowledge)

Run: python3 visual_agi_daemon.py
"""

import asyncio
import json
import logging
import os
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import subprocess

sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("visual_agi_daemon")


class DaemonState(Enum):
    """Daemon operational states."""
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class DaemonConfig:
    """Configuration for the Visual AGI daemon."""
    # Capture settings
    capture_interval: int = 30  # seconds between captures
    capture_on_change: bool = True  # capture when activity detected

    # Processing settings
    reasoning_interval: int = 60  # seconds between reasoning cycles
    learning_interval: int = 300  # seconds between learning updates
    memory_sync_interval: int = 600  # seconds between memory syncs

    # Alert settings
    voice_alerts: bool = True
    arduino_alerts: bool = True
    alert_cooldown: int = 30  # seconds between same alert type

    # Integration settings
    sync_to_enhanced_memory: bool = True
    use_multi_provider: bool = True

    # Resource limits
    max_memories_per_hour: int = 120
    max_alerts_per_hour: int = 60


@dataclass
class DaemonStats:
    """Runtime statistics for the daemon."""
    start_time: str = ""
    captures_total: int = 0
    captures_analyzed: int = 0
    alerts_generated: int = 0
    reasoning_cycles: int = 0
    learning_updates: int = 0
    memory_syncs: int = 0
    errors: int = 0
    last_capture: str = ""
    last_alert: str = ""
    last_reasoning: str = ""
    uptime_seconds: float = 0


class VisualAGIDaemon:
    """
    Unified daemon orchestrating all Visual AGI components.

    Provides continuous visual intelligence with:
    - Periodic screen capture and analysis
    - Real-time change detection and alerting
    - Visual reasoning and decision support
    - Continuous learning from observations
    - Cross-modal memory integration
    """

    def __init__(self, config: Optional[DaemonConfig] = None):
        self.config = config or DaemonConfig()
        self.state = DaemonState.STOPPED
        self.stats = DaemonStats()
        self._shutdown_event = asyncio.Event()
        self._components_initialized = False

        # Component references (lazy loaded)
        self._perception = None
        self._memory = None
        self._cross_modal = None
        self._reasoning = None
        self._alerter = None
        self._correlator = None
        self._learning = None

        # Alert cooldown tracking
        self._last_alerts: Dict[str, datetime] = {}

        # Status file for external monitoring
        self.status_file = "/Volumes/SSDRAID0/agentic-system/databases/visual_agi_daemon_status.json"

    async def initialize_components(self) -> bool:
        """Initialize all Visual AGI components."""
        logger.info("Initializing Visual AGI components...")

        try:
            # Import and initialize components
            from visual_perception_agent import VisualPerceptionAgent
            from visual_memory_integration import VisualMemoryManager
            from cross_modal_integration import CrossModalMemoryManager
            from visual_reasoning_agent import VisualReasoningAgent, ReasoningMode
            from visual_change_alerter import VisualChangeAlerter
            from visual_code_correlator import VisualCodeCorrelator
            from visual_learning_loop import VisualLearningLoop

            self._perception = VisualPerceptionAgent()
            self._memory = VisualMemoryManager()
            self._cross_modal = CrossModalMemoryManager()
            self._reasoning = VisualReasoningAgent()
            self._alerter = VisualChangeAlerter()
            self._correlator = VisualCodeCorrelator()
            self._learning = VisualLearningLoop()

            self._components_initialized = True
            logger.info("All Visual AGI components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            return False

    async def start(self) -> None:
        """Start the Visual AGI daemon."""
        logger.info("Starting Visual AGI Daemon...")
        self.state = DaemonState.STARTING
        self.stats.start_time = datetime.now().isoformat()

        # Initialize components
        if not await self.initialize_components():
            logger.error("Component initialization failed, cannot start daemon")
            self.state = DaemonState.STOPPED
            return

        self.state = DaemonState.RUNNING

        # Announce startup
        await self._voice_announce("Visual AGI daemon starting")
        await self._arduino_alert("startup")

        # Start background tasks
        tasks = [
            asyncio.create_task(self._capture_loop()),
            asyncio.create_task(self._reasoning_loop()),
            asyncio.create_task(self._learning_loop()),
            asyncio.create_task(self._memory_sync_loop()),
            asyncio.create_task(self._status_update_loop()),
        ]

        logger.info("Visual AGI Daemon running")

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        # Cancel all tasks
        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        self.state = DaemonState.STOPPED
        await self._voice_announce("Visual AGI daemon stopped")
        logger.info("Visual AGI Daemon stopped")

    async def stop(self) -> None:
        """Stop the Visual AGI daemon."""
        logger.info("Stopping Visual AGI Daemon...")
        self.state = DaemonState.STOPPING
        self._shutdown_event.set()

    async def _capture_loop(self) -> None:
        """Main capture and analysis loop."""
        while self.state == DaemonState.RUNNING:
            try:
                await self._perform_capture_cycle()
                await asyncio.sleep(self.config.capture_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Capture loop error: {e}")
                self.stats.errors += 1
                await asyncio.sleep(5)

    async def _perform_capture_cycle(self) -> None:
        """Perform a single capture and analysis cycle."""
        self.stats.captures_total += 1

        try:
            # Capture screen
            observation = await self._perception.capture_and_analyze()

            if observation:
                self.stats.captures_analyzed += 1
                self.stats.last_capture = datetime.now().isoformat()

                # Process through learning loop
                await self._learning.observe(observation)

                # Check for alerts
                alerts = await self._alerter.process_observation(observation)

                for alert in alerts:
                    await self._handle_alert(alert)

                # Record visual-code correlation
                await self._correlator.record_visual_state(observation)

                logger.debug(f"Capture cycle complete: {observation.get('scene_type', 'unknown')}")

        except Exception as e:
            logger.error(f"Capture cycle error: {e}")
            self.stats.errors += 1

    async def _reasoning_loop(self) -> None:
        """Periodic reasoning and decision-making loop."""
        while self.state == DaemonState.RUNNING:
            try:
                await self._perform_reasoning_cycle()
                await asyncio.sleep(self.config.reasoning_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Reasoning loop error: {e}")
                self.stats.errors += 1
                await asyncio.sleep(10)

    async def _perform_reasoning_cycle(self) -> None:
        """Perform a reasoning cycle."""
        from visual_reasoning_agent import ReasoningMode

        try:
            # Proactive reasoning
            result = await self._reasoning.reason(mode=ReasoningMode.PROACTIVE)
            self.stats.reasoning_cycles += 1
            self.stats.last_reasoning = datetime.now().isoformat()

            # Check if action needed
            if result.confidence > 0.7 and result.action_type.value != "observe":
                logger.info(f"Reasoning suggests action: {result.decision[:100]}")

                # Announce significant decisions
                if result.confidence > 0.85:
                    await self._voice_announce(f"Visual insight: {result.decision[:50]}")

        except Exception as e:
            logger.error(f"Reasoning cycle error: {e}")

    async def _learning_loop(self) -> None:
        """Periodic learning and model update loop."""
        while self.state == DaemonState.RUNNING:
            try:
                await self._perform_learning_update()
                await asyncio.sleep(self.config.learning_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Learning loop error: {e}")
                self.stats.errors += 1
                await asyncio.sleep(30)

    async def _perform_learning_update(self) -> None:
        """Perform learning model updates."""
        try:
            summary = self._learning.get_learning_summary(hours=1)

            predictions_evaluated = summary.get("predictions_evaluated", 0)
            if predictions_evaluated > 0:
                self.stats.learning_updates += 1
                accuracy = summary.get("prediction_accuracy", 0)
                logger.info(f"Learning update: {predictions_evaluated} predictions, {accuracy:.1%} accuracy")

        except Exception as e:
            logger.error(f"Learning update error: {e}")

    async def _memory_sync_loop(self) -> None:
        """Periodic sync to enhanced-memory."""
        if not self.config.sync_to_enhanced_memory:
            return

        while self.state == DaemonState.RUNNING:
            try:
                await self._sync_to_enhanced_memory()
                await asyncio.sleep(self.config.memory_sync_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory sync error: {e}")
                self.stats.errors += 1
                await asyncio.sleep(60)

    async def _sync_to_enhanced_memory(self) -> None:
        """Sync visual knowledge to enhanced-memory MCP."""
        try:
            from cross_modal_enhanced_memory_bridge import EnhancedMemoryBridge

            bridge = EnhancedMemoryBridge()
            result = await bridge.full_sync(hours=1)

            self.stats.memory_syncs += 1
            synced = result.get("visual_synced", 0) + result.get("text_synced", 0) + result.get("code_synced", 0)

            if synced > 0:
                logger.info(f"Synced {synced} memories to enhanced-memory")

        except ImportError:
            logger.debug("Enhanced memory bridge not available")
        except Exception as e:
            logger.error(f"Memory sync error: {e}")

    async def _status_update_loop(self) -> None:
        """Update status file periodically."""
        while self.state == DaemonState.RUNNING:
            try:
                self._update_status_file()
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Status update error: {e}")

    def _update_status_file(self) -> None:
        """Write current status to file for monitoring."""
        if self.stats.start_time:
            start = datetime.fromisoformat(self.stats.start_time)
            self.stats.uptime_seconds = (datetime.now() - start).total_seconds()

        status = {
            "state": self.state.value,
            "stats": {
                "start_time": self.stats.start_time,
                "uptime_seconds": self.stats.uptime_seconds,
                "captures_total": self.stats.captures_total,
                "captures_analyzed": self.stats.captures_analyzed,
                "alerts_generated": self.stats.alerts_generated,
                "reasoning_cycles": self.stats.reasoning_cycles,
                "learning_updates": self.stats.learning_updates,
                "memory_syncs": self.stats.memory_syncs,
                "errors": self.stats.errors,
                "last_capture": self.stats.last_capture,
                "last_alert": self.stats.last_alert,
                "last_reasoning": self.stats.last_reasoning,
            },
            "config": {
                "capture_interval": self.config.capture_interval,
                "reasoning_interval": self.config.reasoning_interval,
                "learning_interval": self.config.learning_interval,
                "voice_alerts": self.config.voice_alerts,
                "arduino_alerts": self.config.arduino_alerts,
            },
            "updated": datetime.now().isoformat()
        }

        os.makedirs(os.path.dirname(self.status_file), exist_ok=True)
        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)

    async def _handle_alert(self, alert: Any) -> None:
        """Handle a visual alert with cooldown management."""
        alert_type = getattr(alert, 'alert_type', str(alert))

        # Check cooldown
        if alert_type in self._last_alerts:
            elapsed = (datetime.now() - self._last_alerts[alert_type]).total_seconds()
            if elapsed < self.config.alert_cooldown:
                return

        self._last_alerts[alert_type] = datetime.now()
        self.stats.alerts_generated += 1
        self.stats.last_alert = datetime.now().isoformat()

        # Get alert details
        severity = getattr(alert, 'severity', None)
        message = getattr(alert, 'message', str(alert))

        logger.info(f"Visual alert: {message[:100]}")

        # Voice announcement for important alerts
        if self.config.voice_alerts and severity:
            severity_name = severity.name if hasattr(severity, 'name') else str(severity)
            if severity_name in ["ERROR", "CRITICAL", "WARNING"]:
                await self._voice_announce(f"Visual alert: {message[:50]}")

        # Arduino feedback
        if self.config.arduino_alerts and severity:
            severity_name = severity.name if hasattr(severity, 'name') else str(severity)
            await self._arduino_alert(severity_name.lower())

    async def _voice_announce(self, message: str) -> None:
        """Announce via Voice Mode MCP."""
        if not self.config.voice_alerts:
            return

        try:
            # Use voice-mode MCP via subprocess
            result = subprocess.run(
                ["claude", "-p", f"Use voice-mode to say: {message}", "--output-format", "json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            logger.debug(f"Voice announcement: {message[:50]}")
        except Exception as e:
            logger.debug(f"Voice announcement failed: {e}")

    async def _arduino_alert(self, alert_type: str) -> None:
        """Send alert to Arduino Surface."""
        if not self.config.arduino_alerts:
            return

        try:
            # Map alert types to Arduino actions
            led_colors = {
                "startup": (0, 255, 0),      # Green
                "info": (0, 0, 255),         # Blue
                "warning": (255, 165, 0),    # Orange
                "error": (255, 0, 0),        # Red
                "critical": (255, 0, 255),   # Magenta
            }

            color = led_colors.get(alert_type, (255, 255, 255))

            # Send via arduino-surface MCP
            # This would use the MCP tool in production
            logger.debug(f"Arduino alert: {alert_type} -> RGB{color}")
        except Exception as e:
            logger.debug(f"Arduino alert failed: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get current daemon status."""
        if self.stats.start_time:
            start = datetime.fromisoformat(self.stats.start_time)
            self.stats.uptime_seconds = (datetime.now() - start).total_seconds()

        return {
            "state": self.state.value,
            "uptime_seconds": self.stats.uptime_seconds,
            "captures": self.stats.captures_analyzed,
            "alerts": self.stats.alerts_generated,
            "reasoning_cycles": self.stats.reasoning_cycles,
            "learning_updates": self.stats.learning_updates,
            "errors": self.stats.errors
        }


async def main():
    """Run the Visual AGI daemon."""
    daemon = VisualAGIDaemon()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(daemon.stop())

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    print("=" * 60)
    print("VISUAL AGI DAEMON")
    print("=" * 60)
    print("Starting unified visual intelligence system...")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    await daemon.start()

    # Print final stats
    status = daemon.get_status()
    print("\n" + "=" * 60)
    print("DAEMON STOPPED")
    print("=" * 60)
    print(f"  Uptime: {status['uptime_seconds']:.0f} seconds")
    print(f"  Captures analyzed: {status['captures']}")
    print(f"  Alerts generated: {status['alerts']}")
    print(f"  Reasoning cycles: {status['reasoning_cycles']}")
    print(f"  Learning updates: {status['learning_updates']}")
    print(f"  Errors: {status['errors']}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
