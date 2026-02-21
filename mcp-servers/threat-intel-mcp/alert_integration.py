#!/usr/bin/env python3
"""
Threat Alert Integration
========================

Integrates threat intelligence alerts with:
- Voice Mode MCP (for spoken alerts)
- Enhanced Memory MCP (for persistent storage)
- Arduino Surface (for visual alerts via LED)

Provides real-time threat notifications when critical indicators are detected.
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logger = logging.getLogger("threat-alert-integration")

# Storage
STORAGE_BASE = Path(os.environ.get("STORAGE_BASE", Path(__file__).parent))
DB_PATH = STORAGE_BASE / "mcp-servers/threat-intel-mcp/data/threat_intel.db"
ALERT_LOG = STORAGE_BASE / "logs/threat_alerts.log"


class ThreatAlertManager:
    """Manages threat alerts and notifications."""

    def __init__(self):
        self.alert_queue: asyncio.Queue = asyncio.Queue()
        self.running = False

        # Alert thresholds
        self.critical_risk_threshold = 80
        self.high_risk_threshold = 60

        # Ensure log directory exists
        ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)

    async def process_threat_match(
        self,
        indicator: str,
        risk_score: int,
        threat_type: str,
        malware_family: Optional[str],
        source: str,
        context: str = ""
    ):
        """Process a threat match and generate appropriate alerts."""

        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "indicator": indicator,
            "risk_score": risk_score,
            "threat_type": threat_type,
            "malware_family": malware_family,
            "source": source,
            "context": context,
            "severity": self._calculate_severity(risk_score)
        }

        # Log alert
        self._log_alert(alert)

        # Queue for notification processing
        await self.alert_queue.put(alert)

        # Immediate notification for critical threats
        if risk_score >= self.critical_risk_threshold:
            await self._send_critical_alert(alert)

        return alert

    def _calculate_severity(self, risk_score: int) -> str:
        """Calculate severity level from risk score."""
        if risk_score >= 90:
            return "critical"
        elif risk_score >= 75:
            return "high"
        elif risk_score >= 50:
            return "medium"
        elif risk_score >= 25:
            return "low"
        return "info"

    def _log_alert(self, alert: Dict[str, Any]):
        """Log alert to file."""
        try:
            with open(ALERT_LOG, "a") as f:
                f.write(json.dumps(alert) + "\n")
        except Exception as e:
            logger.error(f"Failed to log alert: {e}")

    async def _send_critical_alert(self, alert: Dict[str, Any]):
        """Send immediate notification for critical threats."""
        message = self._format_alert_message(alert)

        # Try Voice Mode notification
        await self._notify_voice(message)

        # Try Arduino LED alert
        await self._notify_arduino(alert["severity"])

        # Store in enhanced memory
        await self._store_in_memory(alert)

    def _format_alert_message(self, alert: Dict[str, Any]) -> str:
        """Format alert for voice notification."""
        severity = alert["severity"].upper()
        indicator = alert["indicator"][:50]  # Truncate for voice
        threat_type = alert["threat_type"]

        if alert["malware_family"]:
            return (
                f"{severity} THREAT DETECTED. "
                f"{threat_type} indicator found: {indicator}. "
                f"Associated with {alert['malware_family']}. "
                f"Risk score: {alert['risk_score']}."
            )
        else:
            return (
                f"{severity} THREAT DETECTED. "
                f"{threat_type} indicator found: {indicator}. "
                f"Risk score: {alert['risk_score']}."
            )

    async def _notify_voice(self, message: str):
        """Send notification via Voice Mode MCP."""
        try:
            # Voice Mode MCP integration
            # This would typically use the MCP client to call voice-mode
            logger.info(f"Voice alert: {message}")

            # For now, log the message - actual MCP call would be:
            # await mcp_client.call_tool("mcp__voice-mode__converse", {
            #     "message": message,
            #     "wait_for_response": False
            # })

        except Exception as e:
            logger.error(f"Voice notification failed: {e}")

    async def _notify_arduino(self, severity: str):
        """Send visual alert via Arduino Surface MCP."""
        try:
            # Map severity to LED color
            colors = {
                "critical": (255, 0, 0),    # Red
                "high": (255, 128, 0),      # Orange
                "medium": (255, 255, 0),    # Yellow
                "low": (0, 255, 0),         # Green
                "info": (0, 0, 255),        # Blue
            }

            color = colors.get(severity, (255, 255, 255))
            logger.info(f"Arduino LED alert: {severity} -> RGB{color}")

            # For now, log - actual MCP call would be:
            # await mcp_client.call_tool("mcp__arduino-surface__led_set", {
            #     "red": color[0],
            #     "green": color[1],
            #     "blue": color[2]
            # })

        except Exception as e:
            logger.error(f"Arduino notification failed: {e}")

    async def _store_in_memory(self, alert: Dict[str, Any]):
        """Store alert in enhanced memory for persistence."""
        try:
            entity = {
                "name": f"threat_alert_{alert['timestamp'][:10]}_{alert['indicator'][:20]}",
                "entityType": "security_alert",
                "observations": [
                    f"indicator: {alert['indicator']}",
                    f"risk_score: {alert['risk_score']}",
                    f"threat_type: {alert['threat_type']}",
                    f"severity: {alert['severity']}",
                    f"source: {alert['source']}",
                    f"context: {alert['context']}",
                ]
            }

            if alert.get("malware_family"):
                entity["observations"].append(f"malware_family: {alert['malware_family']}")

            logger.info(f"Storing alert in memory: {entity['name']}")

            # Actual MCP call would be:
            # await mcp_client.call_tool("mcp__enhanced-memory__create_entities", {
            #     "entities": [entity]
            # })

        except Exception as e:
            logger.error(f"Memory storage failed: {e}")

    async def get_recent_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alerts from the last N hours."""
        alerts = []
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        try:
            if ALERT_LOG.exists():
                with open(ALERT_LOG, "r") as f:
                    for line in f:
                        if line.strip():
                            alert = json.loads(line)
                            if alert.get("timestamp", "") > cutoff:
                                alerts.append(alert)
        except Exception as e:
            logger.error(f"Failed to read alerts: {e}")

        return alerts

    async def generate_alert_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Generate summary of recent alerts."""
        alerts = await self.get_recent_alerts(hours)

        summary = {
            "period_hours": hours,
            "total_alerts": len(alerts),
            "by_severity": {},
            "by_threat_type": {},
            "top_indicators": [],
            "critical_alerts": []
        }

        for alert in alerts:
            # Count by severity
            sev = alert.get("severity", "unknown")
            summary["by_severity"][sev] = summary["by_severity"].get(sev, 0) + 1

            # Count by threat type
            tt = alert.get("threat_type", "unknown")
            summary["by_threat_type"][tt] = summary["by_threat_type"].get(tt, 0) + 1

            # Track critical alerts
            if alert.get("risk_score", 0) >= self.critical_risk_threshold:
                summary["critical_alerts"].append({
                    "indicator": alert["indicator"],
                    "risk_score": alert["risk_score"],
                    "threat_type": alert.get("threat_type"),
                    "timestamp": alert["timestamp"]
                })

        # Get top indicators by frequency
        indicator_counts: Dict[str, int] = {}
        for alert in alerts:
            ind = alert.get("indicator", "")
            indicator_counts[ind] = indicator_counts.get(ind, 0) + 1

        summary["top_indicators"] = sorted(
            [{"indicator": k, "count": v} for k, v in indicator_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        return summary


# Singleton instance
alert_manager = ThreatAlertManager()


async def check_and_alert(
    indicator: str,
    risk_score: int,
    threat_type: str,
    malware_family: Optional[str] = None,
    source: str = "unknown",
    context: str = ""
) -> Optional[Dict[str, Any]]:
    """
    Convenience function to check a threat and generate alerts.

    Use this when processing threat matches from the main server.
    """
    if risk_score >= alert_manager.high_risk_threshold:
        return await alert_manager.process_threat_match(
            indicator=indicator,
            risk_score=risk_score,
            threat_type=threat_type,
            malware_family=malware_family,
            source=source,
            context=context
        )
    return None


if __name__ == "__main__":
    # Test the alert system
    async def test():
        print("Testing Threat Alert Integration")
        print("=" * 50)

        # Test critical alert
        alert = await check_and_alert(
            indicator="198.51.100.42",
            risk_score=95,
            threat_type="botnet_c2",
            malware_family="Emotet",
            source="test",
            context="Unit test"
        )

        if alert:
            print(f"Alert generated: {json.dumps(alert, indent=2)}")

        # Test summary
        summary = await alert_manager.generate_alert_summary(24)
        print(f"\nAlert Summary: {json.dumps(summary, indent=2)}")

    asyncio.run(test())
