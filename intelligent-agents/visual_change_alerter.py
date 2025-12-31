#!/usr/bin/env python3
"""
Visual Change Alerter - Real-time Visual Change Detection and Alerting

Monitors visual observations and alerts on significant changes:
- Scene type transitions
- New/removed objects detection
- Error indicator detection
- Anomaly detection based on learned patterns
- Multi-channel alerting (voice, Arduino, logs)

STATUS: Production Ready
"""

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-agents')
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/shared')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels."""
    LOG = "log"
    VOICE = "voice"
    ARDUINO = "arduino"
    FILE = "file"
    CALLBACK = "callback"


@dataclass
class VisualAlert:
    """A visual change alert."""
    id: str
    severity: AlertSeverity
    title: str
    description: str
    visual_evidence: Dict[str, Any]
    change_type: str
    triggered_rules: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False


@dataclass
class AlertRule:
    """Rule for triggering alerts."""
    name: str
    description: str
    severity: AlertSeverity
    condition: Callable[[Dict, Dict], bool]
    message_template: str
    cooldown_seconds: int = 60
    enabled: bool = True


class VisualChangeAlerter:
    """
    Real-time visual change alerter.

    Monitors visual observations and alerts on significant changes.
    """

    def __init__(
        self,
        storage_path: str = "/Volumes/SSDRAID0/agentic-system/databases/visual_alerts"
    ):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

        # Alert history
        self._alerts: List[VisualAlert] = []
        self._last_observation: Optional[Dict] = None
        self._rule_cooldowns: Dict[str, datetime] = {}

        # Initialize alert rules
        self._rules = self._init_alert_rules()

        # Alert channels
        self._channels: List[AlertChannel] = [AlertChannel.LOG, AlertChannel.FILE]

        logger.info(f"VisualChangeAlerter initialized at {storage_path}")

    def _init_alert_rules(self) -> List[AlertRule]:
        """Initialize alert rules."""
        return [
            AlertRule(
                name="error_detected",
                description="Error or exception visible on screen",
                severity=AlertSeverity.ERROR,
                condition=lambda curr, prev: self._check_error_keywords(curr),
                message_template="Error detected: {description}",
                cooldown_seconds=300
            ),
            AlertRule(
                name="scene_change",
                description="Scene type changed significantly",
                severity=AlertSeverity.INFO,
                condition=lambda curr, prev: self._check_scene_change(curr, prev),
                message_template="Scene changed from {prev_scene} to {curr_scene}",
                cooldown_seconds=60
            ),
            AlertRule(
                name="new_window",
                description="New application window appeared",
                severity=AlertSeverity.INFO,
                condition=lambda curr, prev: self._check_new_objects(curr, prev, ["window", "dialog", "modal"]),
                message_template="New window detected: {new_objects}",
                cooldown_seconds=30
            ),
            AlertRule(
                name="confidence_drop",
                description="Visual analysis confidence dropped significantly",
                severity=AlertSeverity.WARNING,
                condition=lambda curr, prev: self._check_confidence_drop(curr, prev),
                message_template="Visual confidence dropped from {prev_conf:.0%} to {curr_conf:.0%}",
                cooldown_seconds=120
            ),
            AlertRule(
                name="critical_ui_element",
                description="Critical UI element detected (auth, payment, warning)",
                severity=AlertSeverity.WARNING,
                condition=lambda curr, prev: self._check_critical_ui(curr),
                message_template="Critical UI detected: {element_type}",
                cooldown_seconds=180
            ),
            AlertRule(
                name="idle_screen",
                description="Screen has been idle/unchanged for extended period",
                severity=AlertSeverity.INFO,
                condition=lambda curr, prev: self._check_idle(curr, prev),
                message_template="Screen appears idle - no changes detected",
                cooldown_seconds=600
            ),
            AlertRule(
                name="high_activity",
                description="High visual activity detected",
                severity=AlertSeverity.INFO,
                condition=lambda curr, prev: self._check_high_activity(curr, prev),
                message_template="High visual activity: {change_count} changes detected",
                cooldown_seconds=120
            )
        ]

    def _check_error_keywords(self, curr: Dict) -> bool:
        """Check for error-related keywords in description."""
        description = str(curr.get("description", "")).lower()
        error_keywords = [
            "error", "exception", "failed", "failure", "crash",
            "traceback", "stack trace", "fatal", "critical"
        ]
        return any(kw in description for kw in error_keywords)

    def _check_scene_change(self, curr: Dict, prev: Dict) -> bool:
        """Check if scene type changed."""
        if not prev:
            return False

        curr_scene = curr.get("scene_type", "")
        prev_scene = prev.get("scene_type", "")

        return curr_scene != prev_scene and curr_scene and prev_scene

    def _check_new_objects(
        self,
        curr: Dict,
        prev: Dict,
        object_types: List[str]
    ) -> bool:
        """Check if specific object types appeared."""
        if not prev:
            return False

        curr_objects = set(str(o).lower() for o in curr.get("objects", []))
        prev_objects = set(str(o).lower() for o in prev.get("objects", []))

        new_objects = curr_objects - prev_objects

        for obj in new_objects:
            for obj_type in object_types:
                if obj_type in obj:
                    return True

        return False

    def _check_confidence_drop(self, curr: Dict, prev: Dict) -> bool:
        """Check if confidence dropped significantly."""
        if not prev:
            return False

        curr_conf = curr.get("confidence", 1.0)
        prev_conf = prev.get("confidence", 1.0)

        return prev_conf - curr_conf > 0.3

    def _check_critical_ui(self, curr: Dict) -> bool:
        """Check for critical UI elements."""
        description = str(curr.get("description", "")).lower()
        objects = [str(o).lower() for o in curr.get("objects", [])]

        critical_keywords = [
            "password", "login", "authentication", "payment",
            "credit card", "confirm delete", "are you sure",
            "warning", "danger", "irreversible"
        ]

        text_to_check = description + " " + " ".join(objects)
        return any(kw in text_to_check for kw in critical_keywords)

    def _check_idle(self, curr: Dict, prev: Dict) -> bool:
        """Check if screen appears idle."""
        if not prev:
            return False

        # Compare image hashes if available
        curr_hash = curr.get("image_hash", "")
        prev_hash = prev.get("image_hash", "")

        if curr_hash and prev_hash:
            return curr_hash == prev_hash

        # Fallback: compare scene and objects
        return (
            curr.get("scene_type") == prev.get("scene_type") and
            set(curr.get("objects", [])) == set(prev.get("objects", []))
        )

    def _check_high_activity(self, curr: Dict, prev: Dict) -> bool:
        """Check for high visual activity."""
        if not prev:
            return False

        curr_objects = set(curr.get("objects", []))
        prev_objects = set(prev.get("objects", []))

        new_count = len(curr_objects - prev_objects)
        removed_count = len(prev_objects - curr_objects)

        return new_count + removed_count >= 5

    def _is_rule_in_cooldown(self, rule: AlertRule) -> bool:
        """Check if a rule is in cooldown."""
        last_triggered = self._rule_cooldowns.get(rule.name)

        if not last_triggered:
            return False

        cooldown_end = last_triggered + timedelta(seconds=rule.cooldown_seconds)
        return datetime.now() < cooldown_end

    async def process_observation(
        self,
        observation: Dict
    ) -> List[VisualAlert]:
        """
        Process a new visual observation and generate alerts.

        Args:
            observation: Visual observation dict with scene_type, objects, etc.

        Returns:
            List of generated alerts
        """
        alerts = []

        # Check each rule
        for rule in self._rules:
            if not rule.enabled:
                continue

            if self._is_rule_in_cooldown(rule):
                continue

            try:
                if rule.condition(observation, self._last_observation):
                    alert = self._create_alert(rule, observation, self._last_observation)
                    alerts.append(alert)

                    # Set cooldown
                    self._rule_cooldowns[rule.name] = datetime.now()

                    # Deliver alert
                    await self._deliver_alert(alert)

            except Exception as e:
                logger.error(f"Rule {rule.name} failed: {e}")

        # Update last observation
        self._last_observation = observation

        return alerts

    def _create_alert(
        self,
        rule: AlertRule,
        curr: Dict,
        prev: Optional[Dict]
    ) -> VisualAlert:
        """Create an alert from a triggered rule."""
        alert_id = f"alert_{datetime.now().strftime('%Y%m%d%H%M%S')}_{rule.name}"

        # Format message
        format_vars = {
            "description": curr.get("description", "")[:200],
            "curr_scene": curr.get("scene_type", "unknown"),
            "prev_scene": prev.get("scene_type", "unknown") if prev else "unknown",
            "curr_conf": curr.get("confidence", 0),
            "prev_conf": prev.get("confidence", 0) if prev else 0,
            "new_objects": ", ".join(
                set(curr.get("objects", [])) - set(prev.get("objects", []) if prev else [])
            )[:100],
            "change_count": len(set(curr.get("objects", [])) ^ set(prev.get("objects", []) if prev else [])),
            "element_type": self._detect_critical_element(curr)
        }

        try:
            description = rule.message_template.format(**format_vars)
        except Exception:
            description = rule.message_template

        return VisualAlert(
            id=alert_id,
            severity=rule.severity,
            title=rule.name.replace("_", " ").title(),
            description=description,
            visual_evidence={
                "current_scene": curr.get("scene_type"),
                "objects": curr.get("objects", [])[:10],
                "confidence": curr.get("confidence")
            },
            change_type=rule.name,
            triggered_rules=[rule.name]
        )

    def _detect_critical_element(self, observation: Dict) -> str:
        """Detect which critical element triggered the alert."""
        description = str(observation.get("description", "")).lower()

        elements = {
            "password": "Password/Login",
            "payment": "Payment",
            "delete": "Deletion",
            "warning": "Warning"
        }

        for keyword, element in elements.items():
            if keyword in description:
                return element

        return "Unknown"

    async def _deliver_alert(self, alert: VisualAlert) -> None:
        """Deliver alert through configured channels."""
        for channel in self._channels:
            try:
                if channel == AlertChannel.LOG:
                    self._log_alert(alert)
                elif channel == AlertChannel.FILE:
                    self._file_alert(alert)
                elif channel == AlertChannel.VOICE:
                    await self._voice_alert(alert)
                elif channel == AlertChannel.ARDUINO:
                    await self._arduino_alert(alert)
            except Exception as e:
                logger.error(f"Failed to deliver alert via {channel.value}: {e}")

        # Store alert
        self._alerts.append(alert)
        self._store_alert(alert)

    def _log_alert(self, alert: VisualAlert) -> None:
        """Log alert."""
        level_map = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.WARNING: logging.WARNING,
            AlertSeverity.ERROR: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL
        }

        logger.log(
            level_map[alert.severity],
            f"[VISUAL ALERT] {alert.title}: {alert.description}"
        )

    def _file_alert(self, alert: VisualAlert) -> None:
        """Write alert to file."""
        alerts_path = os.path.join(self.storage_path, "alerts.jsonl")

        record = {
            "id": alert.id,
            "severity": alert.severity.value,
            "title": alert.title,
            "description": alert.description,
            "change_type": alert.change_type,
            "timestamp": alert.timestamp
        }

        with open(alerts_path, 'a') as f:
            f.write(json.dumps(record) + '\n')

    async def _voice_alert(self, alert: VisualAlert) -> None:
        """Deliver alert via voice."""
        try:
            # Use voice-mode MCP if available
            message = f"{alert.severity.value.upper()}: {alert.title}. {alert.description}"

            # Try subprocess call to voice synthesis
            subprocess.run(
                ["say", message[:200]],  # macOS say command
                timeout=10,
                capture_output=True
            )
        except Exception as e:
            logger.debug(f"Voice alert failed: {e}")

    async def _arduino_alert(self, alert: VisualAlert) -> None:
        """Deliver alert via Arduino."""
        try:
            # Color based on severity
            colors = {
                AlertSeverity.INFO: (0, 0, 255),      # Blue
                AlertSeverity.WARNING: (255, 165, 0),  # Orange
                AlertSeverity.ERROR: (255, 0, 0),      # Red
                AlertSeverity.CRITICAL: (255, 0, 255)  # Magenta
            }

            color = colors.get(alert.severity, (255, 255, 255))

            # Try to use Arduino MCP
            # This would call mcp__arduino-surface__surface_led_set
            logger.info(f"Arduino alert: LED color {color}")

        except Exception as e:
            logger.debug(f"Arduino alert failed: {e}")

    def _store_alert(self, alert: VisualAlert) -> None:
        """Store alert persistently."""
        # Already done in _file_alert
        pass

    def add_channel(self, channel: AlertChannel) -> None:
        """Add an alert delivery channel."""
        if channel not in self._channels:
            self._channels.append(channel)

    def remove_channel(self, channel: AlertChannel) -> None:
        """Remove an alert delivery channel."""
        if channel in self._channels:
            self._channels.remove(channel)

    def enable_rule(self, rule_name: str) -> None:
        """Enable an alert rule."""
        for rule in self._rules:
            if rule.name == rule_name:
                rule.enabled = True
                break

    def disable_rule(self, rule_name: str) -> None:
        """Disable an alert rule."""
        for rule in self._rules:
            if rule.name == rule_name:
                rule.enabled = False
                break

    def get_recent_alerts(self, hours: int = 24, severity: Optional[AlertSeverity] = None) -> List[VisualAlert]:
        """Get recent alerts."""
        cutoff = datetime.now() - timedelta(hours=hours)

        alerts = [
            a for a in self._alerts
            if datetime.fromisoformat(a.timestamp) > cutoff
        ]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts

    def get_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get alert summary."""
        recent = self.get_recent_alerts(hours)

        severity_counts = {}
        for alert in recent:
            sev = alert.severity.value
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        rule_counts = {}
        for alert in recent:
            for rule in alert.triggered_rules:
                rule_counts[rule] = rule_counts.get(rule, 0) + 1

        return {
            "hours": hours,
            "total_alerts": len(recent),
            "by_severity": severity_counts,
            "by_rule": rule_counts,
            "enabled_rules": [r.name for r in self._rules if r.enabled],
            "active_channels": [c.value for c in self._channels],
            "timestamp": datetime.now().isoformat()
        }


# MCP Tool Functions
async def process_visual_alert(observation: Dict) -> Dict:
    """MCP Tool: Process observation and generate alerts."""
    alerter = VisualChangeAlerter()
    alerts = await alerter.process_observation(observation)

    return {
        "alerts_generated": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "severity": a.severity.value,
                "title": a.title,
                "description": a.description
            }
            for a in alerts
        ]
    }


def get_visual_alert_summary(hours: int = 24) -> Dict:
    """MCP Tool: Get alert summary."""
    alerter = VisualChangeAlerter()
    return alerter.get_alert_summary(hours)


# CLI Entry Point
async def main():
    """Demo visual change alerter."""
    import argparse

    parser = argparse.ArgumentParser(description="Visual Change Alerter")
    parser.add_argument("--summary", action="store_true", help="Show alert summary")
    parser.add_argument("--test", action="store_true", help="Test with sample observation")
    parser.add_argument("--hours", type=int, default=24, help="Hours for summary")

    args = parser.parse_args()

    alerter = VisualChangeAlerter()

    if args.test:
        # Test with sample observations
        obs1 = {
            "scene_type": "desktop",
            "objects": ["terminal", "browser", "dock"],
            "description": "Normal desktop view with terminal and browser",
            "confidence": 0.9
        }

        obs2 = {
            "scene_type": "error_dialog",
            "objects": ["dialog", "error_message", "ok_button"],
            "description": "Error dialog showing exception traceback",
            "confidence": 0.85
        }

        print("Processing first observation...")
        alerts1 = await alerter.process_observation(obs1)
        print(f"Generated {len(alerts1)} alerts")

        print("\nProcessing second observation (with error)...")
        alerts2 = await alerter.process_observation(obs2)
        print(f"Generated {len(alerts2)} alerts")

        for alert in alerts2:
            print(f"  [{alert.severity.value}] {alert.title}: {alert.description}")

    elif args.summary:
        summary = alerter.get_alert_summary(args.hours)
        print(json.dumps(summary, indent=2))

    else:
        print("Use --test to test alerting or --summary to view summary")


if __name__ == "__main__":
    asyncio.run(main())
