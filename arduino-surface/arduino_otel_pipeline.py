#!/usr/bin/env python3
"""
Arduino OTEL Data Processing Pipeline
Dynamic communication channel for entire agentic system

Collects telemetry → AI summarizes → Arduino displays on LCD/LED
"""

import asyncio
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Arduino control (assumes arduino_surface_mcp is available)
import sys
sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))


class DisplayMode(Enum):
    """Display mode priority order."""
    ALERT = 1  # Highest priority - errors, violations
    VOICE = 2  # Voice mode active
    SWARM = 3  # Agent swarm executing
    PROGRESS = 4  # Task progress
    STATUS = 5  # Normal status (lowest priority)
    EMBER = 6  # Ember thoughts (fallback)


class LEDStatus(Enum):
    """LED indicator colors."""
    HEALTHY = (0, 255, 0)  # Green
    WARNING = (255, 255, 0)  # Yellow
    ERROR = (255, 0, 0)  # Red
    VOICE_ACTIVE = (0, 0, 255)  # Blue
    SWARM_ACTIVE = (128, 0, 128)  # Purple


@dataclass
class OTELMetrics:
    """OpenTelemetry metrics snapshot."""
    timestamp: str
    system_health: str  # "healthy", "warning", "error"
    active_agents: int
    memory_ops_per_sec: float
    voice_system_active: bool
    ember_violations_count: int
    hook_executions: int
    task_queue_size: int
    error_count: int
    cpu_percent: float
    memory_percent: float


class OTELCollector:
    """Collect telemetry from all agentic systems."""

    def __init__(self):
        self.db_path = Path.home() / ".claude" / "otel_metrics.db"
        self._init_db()

    def _init_db(self):
        """Initialize metrics database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    system_health TEXT,
                    active_agents INTEGER DEFAULT 0,
                    memory_ops_per_sec REAL DEFAULT 0.0,
                    voice_system_active BOOLEAN DEFAULT 0,
                    ember_violations_count INTEGER DEFAULT 0,
                    hook_executions INTEGER DEFAULT 0,
                    task_queue_size INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    cpu_percent REAL DEFAULT 0.0,
                    memory_percent REAL DEFAULT 0.0
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp
                ON metrics(timestamp)
            """)

            conn.commit()

    def collect_metrics(self) -> OTELMetrics:
        """Collect current system metrics."""
        # In production, this would query actual OTEL exporters
        # For now, we'll collect from various system databases

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "system_health": "healthy",
            "active_agents": 0,
            "memory_ops_per_sec": 0.0,
            "voice_system_active": False,
            "ember_violations_count": 0,
            "hook_executions": 0,
            "task_queue_size": 0,
            "error_count": 0,
            "cpu_percent": 0.0,
            "memory_percent": 0.0
        }

        try:
            # Get agent runtime task queue size
            agent_runtime_db = Path.home() / ".claude" / "agent_runtime.db"
            if agent_runtime_db.exists():
                with sqlite3.connect(agent_runtime_db) as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
                    metrics["task_queue_size"] = cursor.fetchone()[0]

                    cursor = conn.execute("SELECT COUNT(*) FROM tasks WHERE status = 'in_progress'")
                    metrics["active_agents"] = cursor.fetchone()[0]

        except Exception as e:
            print(f"Error collecting agent runtime metrics: {e}", file=sys.stderr)

        try:
            # Get Ember violations
            ember_violations = Path.home() / ".claude" / "ember_violations.jsonl"
            if ember_violations.exists():
                with open(ember_violations) as f:
                    violations = [line for line in f if line.strip()]
                    # Count violations in last hour
                    recent = [v for v in violations[-100:] if v.strip()]
                    metrics["ember_violations_count"] = len(recent)

                    if len(recent) > 5:
                        metrics["system_health"] = "warning"
                    if len(recent) > 10:
                        metrics["system_health"] = "error"

        except Exception as e:
            print(f"Error collecting Ember metrics: {e}", file=sys.stderr)

        try:
            # Check voice system status
            import subprocess
            result = subprocess.run(
                ["pgrep", "-f", "voicemode"],
                capture_output=True,
                text=True
            )
            metrics["voice_system_active"] = bool(result.stdout.strip())

        except Exception:
            pass

        try:
            # System resource usage
            import psutil
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            metrics["memory_percent"] = psutil.virtual_memory().percent

            if metrics["cpu_percent"] > 80 or metrics["memory_percent"] > 80:
                metrics["system_health"] = "warning"
            if metrics["cpu_percent"] > 95 or metrics["memory_percent"] > 95:
                metrics["system_health"] = "error"

        except Exception:
            pass

        # Store metrics
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO metrics
                    (system_health, active_agents, memory_ops_per_sec, voice_system_active,
                     ember_violations_count, task_queue_size, cpu_percent, memory_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics["system_health"],
                    metrics["active_agents"],
                    metrics["memory_ops_per_sec"],
                    metrics["voice_system_active"],
                    metrics["ember_violations_count"],
                    metrics["task_queue_size"],
                    metrics["cpu_percent"],
                    metrics["memory_percent"]
                ))
                conn.commit()

        except Exception as e:
            print(f"Error storing metrics: {e}", file=sys.stderr)

        return OTELMetrics(**metrics)


class DisplaySummarizer:
    """AI-powered summarization for LCD display."""

    def __init__(self, max_chars: int = 32):
        self.max_chars = max_chars

    def summarize_for_lcd(self, metrics: OTELMetrics, mode: DisplayMode) -> List[str]:
        """
        Summarize metrics for LCD display (2 lines, max_chars each).

        Returns list of 2 strings for LCD lines.
        """

        if mode == DisplayMode.ALERT:
            if metrics.ember_violations_count > 0:
                return [
                    f"ALERT: {metrics.ember_violations_count} violations".ljust(self.max_chars)[:self.max_chars],
                    f"System: {metrics.system_health}".ljust(self.max_chars)[:self.max_chars]
                ]
            else:
                return [
                    f"ERROR: Check logs".ljust(self.max_chars)[:self.max_chars],
                    f"Health: {metrics.system_health}".ljust(self.max_chars)[:self.max_chars]
                ]

        elif mode == DisplayMode.VOICE:
            return [
                "Voice Mode Active".ljust(self.max_chars)[:self.max_chars],
                f"CPU: {metrics.cpu_percent:.1f}% RAM: {metrics.memory_percent:.1f}%".ljust(self.max_chars)[:self.max_chars]
            ]

        elif mode == DisplayMode.SWARM:
            return [
                f"Swarm: {metrics.active_agents} agents".ljust(self.max_chars)[:self.max_chars],
                f"Queue: {metrics.task_queue_size} tasks".ljust(self.max_chars)[:self.max_chars]
            ]

        elif mode == DisplayMode.PROGRESS:
            if metrics.task_queue_size > 0:
                progress = max(0, 100 - (metrics.task_queue_size * 10))
                return [
                    f"Progress: {progress}%".ljust(self.max_chars)[:self.max_chars],
                    f"{metrics.active_agents} active, {metrics.task_queue_size} queued".ljust(self.max_chars)[:self.max_chars]
                ]
            else:
                return [
                    "All tasks complete".ljust(self.max_chars)[:self.max_chars],
                    f"System: {metrics.system_health}".ljust(self.max_chars)[:self.max_chars]
                ]

        elif mode == DisplayMode.STATUS:
            return [
                f"AGI System {metrics.system_health[:7]}".ljust(self.max_chars)[:self.max_chars],
                f"CPU:{metrics.cpu_percent:.0f}% RAM:{metrics.memory_percent:.0f}% T:{metrics.task_queue_size}".ljust(self.max_chars)[:self.max_chars]
            ]

        else:  # EMBER mode (fallback)
            return [
                "Ember watching...".ljust(self.max_chars)[:self.max_chars],
                f"Violations: {metrics.ember_violations_count}".ljust(self.max_chars)[:self.max_chars]
            ]


class DisplayModeManager:
    """Manage display mode selection based on priority."""

    def select_mode(self, metrics: OTELMetrics) -> DisplayMode:
        """Select display mode based on current metrics (highest priority first)."""

        # Priority 1: Alerts (errors, violations)
        if metrics.system_health == "error" or metrics.ember_violations_count > 10:
            return DisplayMode.ALERT

        # Priority 2: Voice mode active
        if metrics.voice_system_active:
            return DisplayMode.VOICE

        # Priority 3: Agent swarm executing
        if metrics.active_agents >= 3:
            return DisplayMode.SWARM

        # Priority 4: Task progress
        if metrics.task_queue_size > 0 or metrics.active_agents > 0:
            return DisplayMode.PROGRESS

        # Priority 5: Normal status
        if metrics.system_health in ("healthy", "warning"):
            return DisplayMode.STATUS

        # Fallback: Ember mode
        return DisplayMode.EMBER


class LEDController:
    """Control Arduino LED based on system status."""

    def get_led_color(self, metrics: OTELMetrics, mode: DisplayMode) -> tuple:
        """Get LED color based on metrics and mode."""

        if mode == DisplayMode.ALERT:
            return LEDStatus.ERROR.value

        elif mode == DisplayMode.VOICE:
            return LEDStatus.VOICE_ACTIVE.value

        elif mode == DisplayMode.SWARM:
            return LEDStatus.SWARM_ACTIVE.value

        elif metrics.system_health == "error":
            return LEDStatus.ERROR.value

        elif metrics.system_health == "warning":
            return LEDStatus.WARNING.value

        else:
            return LEDStatus.HEALTHY.value


class ArduinoOTELPipeline:
    """Main pipeline coordinating OTEL → AI → Arduino."""

    def __init__(self, arduino_port: str = "/dev/tty.usbmodem8344401"):
        self.arduino_port = arduino_port
        self.collector = OTELCollector()
        self.summarizer = DisplaySummarizer(max_chars=20)  # Adjust for your LCD
        self.mode_manager = DisplayModeManager()
        self.led_controller = LEDController()

    def send_to_arduino(self, lines: List[str], led_color: tuple):
        """Send display update to Arduino."""
        try:
            # Use arduino_surface_mcp tools
            # This would normally call the MCP server
            # For now, write to a queue file that Arduino daemon reads

            queue_file = Path.home() / ".claude" / "arduino_display_queue.json"
            update = {
                "timestamp": datetime.now().isoformat(),
                "lines": lines,
                "led_rgb": led_color
            }

            with open(queue_file, "w") as f:
                json.dump(update, f, indent=2)

            print(f"[Arduino] {lines[0]}")
            print(f"[Arduino] {lines[1]}")
            print(f"[LED] RGB{led_color}")

        except Exception as e:
            print(f"Error sending to Arduino: {e}", file=sys.stderr)

    def process_iteration(self):
        """Run one iteration of the pipeline."""

        # 1. Collect metrics
        metrics = self.collector.collect_metrics()

        # 2. Select display mode
        mode = self.mode_manager.select_mode(metrics)

        # 3. Generate display text
        lines = self.summarizer.summarize_for_lcd(metrics, mode)

        # 4. Get LED color
        led_color = self.led_controller.get_led_color(metrics, mode)

        # 5. Send to Arduino
        self.send_to_arduino(lines, led_color)

        return {
            "metrics": asdict(metrics),
            "mode": mode.name,
            "display": lines,
            "led": led_color
        }

    async def run_continuous(self, interval_seconds: float = 2.0):
        """Run pipeline continuously."""
        print(f"Starting Arduino OTEL Pipeline (interval={interval_seconds}s)")

        while True:
            try:
                result = self.process_iteration()
                print(f"\n[{result['metrics']['timestamp']}] Mode: {result['mode']}")

            except Exception as e:
                print(f"Error in pipeline iteration: {e}", file=sys.stderr)

            await asyncio.sleep(interval_seconds)


async def main():
    """Run the Arduino OTEL pipeline."""
    pipeline = ArduinoOTELPipeline()
    await pipeline.run_continuous(interval_seconds=2.0)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nArduino OTEL Pipeline stopped by user")
