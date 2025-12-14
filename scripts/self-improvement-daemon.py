#!/usr/bin/env python3
"""
Self-Improvement Daemon

Monitors eval data and takes automated actions to improve system performance.
This is the feedback loop that makes the system actually self-improving.

Key capabilities:
1. Anomaly detection - detect when metrics deviate from baseline
2. Regression alerts - detect when quality drops
3. Parameter tuning - adjust system parameters based on metrics
4. Learning consolidation - trigger memory consolidation when patterns detected
5. Improvement tracking - record all actions taken for analysis

Based on research: "Sleep-Inspired Memory Consolidation for Persistent AI Agents"
"""

import asyncio
import json
import logging
import sqlite3
import time
import subprocess
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configuration
CONFIG = {
    "check_interval_seconds": 60,  # How often to check metrics
    "anomaly_threshold_std": 2.0,  # Standard deviations for anomaly
    "regression_threshold": 0.15,  # 15% drop triggers alert
    "min_samples_for_baseline": 50,  # Minimum samples before detecting anomalies
    "improvement_cooldown_seconds": 300,  # Wait between improvement actions
    "db_path": Path.home() / ".claude/enhanced_memories/memory.db",
    "log_file": "/var/log/self-improvement.log",
}

# Metrics to monitor with their targets and actions
MONITORED_METRICS = {
    "action_success_rate": {
        "query": """
            SELECT AVG(success_score) FROM action_outcomes
            WHERE executed_at > datetime('now', '-1 hour')
        """,
        "target": 0.90,
        "alert_below": 0.80,
        "action": "alert",
    },
    "hook_latency_p99": {
        "query": """
            SELECT execution_time_ms FROM hook_evals
            WHERE recorded_at > datetime('now', '-1 hour')
            ORDER BY execution_time_ms DESC
            LIMIT 1 OFFSET (SELECT COUNT(*)/100 FROM hook_evals WHERE recorded_at > datetime('now', '-1 hour'))
        """,
        "target": 200,  # ms
        "alert_above": 500,
        "action": "alert",
    },
    "memory_retrieval_relevance": {
        "query": """
            SELECT AVG(metric_value) FROM component_evals
            WHERE component = 'enhanced-memory' AND metric_name = 'retrieval_relevance'
            AND recorded_at > datetime('now', '-1 hour')
        """,
        "target": 0.75,
        "alert_below": 0.50,
        "action": "tune_retrieval",
    },
    "agent_success_rate": {
        "query": """
            SELECT AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) FROM agent_evals
            WHERE recorded_at > datetime('now', '-1 hour')
        """,
        "target": 0.85,
        "alert_below": 0.70,
        "action": "alert",
    },
    "soundtrack_intensity_accuracy": {
        "query": """
            SELECT AVG(intensity_accuracy) FROM soundtrack_evals
            WHERE recorded_at > datetime('now', '-1 hour')
        """,
        "target": 0.85,
        "alert_below": 0.70,
        "action": "tune_soundtrack",
    },
    "error_rate_1h": {
        "query": """
            SELECT COUNT(*) * 1.0 / NULLIF((SELECT COUNT(*) FROM action_outcomes WHERE executed_at > datetime('now', '-1 hour')), 0)
            FROM action_outcomes
            WHERE success_score < 0.5 AND executed_at > datetime('now', '-1 hour')
        """,
        "target": 0.05,
        "alert_above": 0.15,
        "action": "investigate_errors",
    },
}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(CONFIG["log_file"], mode='a') if os.access(os.path.dirname(CONFIG["log_file"]) or '/tmp', os.W_OK) else logging.StreamHandler()
    ]
)
logger = logging.getLogger("SelfImprovement")


class ActionType(Enum):
    ALERT = "alert"
    PARAMETER_TUNE = "parameter_tune"
    CONSOLIDATE = "consolidate"
    INVESTIGATE = "investigate"
    RESTART_SERVICE = "restart_service"


@dataclass
class ImprovementAction:
    trigger_metric: str
    trigger_value: float
    trigger_threshold: float
    action_type: ActionType
    action_details: Dict[str, Any]
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class SelfImprovementDaemon:
    def __init__(self):
        self.db_path = CONFIG["db_path"]
        self.last_improvement_time: Dict[str, datetime] = {}
        self.baseline_metrics: Dict[str, Tuple[float, float]] = {}  # (mean, std)
        self.running = True

    def get_db_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def get_metric_value(self, metric_name: str) -> Optional[float]:
        """Get current value for a metric"""
        config = MONITORED_METRICS.get(metric_name)
        if not config:
            return None

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(config["query"])
            result = cursor.fetchone()
            conn.close()
            return result[0] if result and result[0] is not None else None
        except Exception as e:
            logger.warning(f"Failed to get metric {metric_name}: {e}")
            return None

    def calculate_baseline(self, metric_name: str, hours: int = 24) -> Tuple[float, float]:
        """Calculate baseline mean and std for a metric over time"""
        config = MONITORED_METRICS.get(metric_name)
        if not config:
            return (0, 1)

        # Modify query to get historical data
        base_query = config["query"].replace("-1 hour", f"-{hours} hours")

        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(base_query)
            result = cursor.fetchone()
            conn.close()

            if result and result[0] is not None:
                # For now, use target as baseline with 20% std
                mean = result[0]
                std = abs(mean * 0.2) if mean != 0 else 0.1
                return (mean, std)
        except Exception as e:
            logger.warning(f"Failed to calculate baseline for {metric_name}: {e}")

        # Default to target
        return (config.get("target", 0.5), 0.1)

    def detect_anomaly(self, metric_name: str, current_value: float) -> bool:
        """Detect if current value is anomalous"""
        if metric_name not in self.baseline_metrics:
            self.baseline_metrics[metric_name] = self.calculate_baseline(metric_name)

        mean, std = self.baseline_metrics[metric_name]
        if std == 0:
            std = 0.1

        z_score = abs(current_value - mean) / std
        return z_score > CONFIG["anomaly_threshold_std"]

    def check_threshold(self, metric_name: str, current_value: float) -> Optional[str]:
        """Check if metric crosses alert threshold"""
        config = MONITORED_METRICS.get(metric_name, {})

        if "alert_below" in config and current_value < config["alert_below"]:
            return f"below threshold ({current_value:.3f} < {config['alert_below']})"
        if "alert_above" in config and current_value > config["alert_above"]:
            return f"above threshold ({current_value:.3f} > {config['alert_above']})"

        return None

    def can_take_action(self, metric_name: str) -> bool:
        """Check if we're past cooldown for this metric"""
        last_time = self.last_improvement_time.get(metric_name)
        if last_time is None:
            return True
        return (datetime.now() - last_time).total_seconds() > CONFIG["improvement_cooldown_seconds"]

    def record_improvement_action(self, action: ImprovementAction, outcome: str = "pending"):
        """Record an improvement action to the database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO improvement_actions
                (trigger_metric, trigger_value, trigger_threshold, action_type, action_details, outcome)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                action.trigger_metric,
                action.trigger_value,
                action.trigger_threshold,
                action.action_type.value,
                json.dumps(action.action_details),
                outcome
            ))
            conn.commit()
            conn.close()
            logger.info(f"Recorded improvement action: {action.action_type.value} for {action.trigger_metric}")
        except Exception as e:
            logger.error(f"Failed to record improvement action: {e}")

    def take_action(self, metric_name: str, current_value: float, threshold_msg: str):
        """Take automated improvement action"""
        if not self.can_take_action(metric_name):
            logger.debug(f"Skipping action for {metric_name} - in cooldown")
            return

        config = MONITORED_METRICS.get(metric_name, {})
        action_type = config.get("action", "alert")
        threshold = config.get("alert_below", config.get("alert_above", 0))

        action = ImprovementAction(
            trigger_metric=metric_name,
            trigger_value=current_value,
            trigger_threshold=threshold,
            action_type=ActionType(action_type) if action_type in [e.value for e in ActionType] else ActionType.ALERT,
            action_details={"threshold_message": threshold_msg}
        )

        # Execute action based on type
        if action_type == "alert":
            self._action_alert(metric_name, current_value, threshold_msg)
        elif action_type == "tune_retrieval":
            self._action_tune_retrieval(metric_name, current_value)
        elif action_type == "tune_soundtrack":
            self._action_tune_soundtrack(metric_name, current_value)
        elif action_type == "investigate_errors":
            self._action_investigate_errors(metric_name, current_value)

        self.record_improvement_action(action)
        self.last_improvement_time[metric_name] = datetime.now()

    def _action_alert(self, metric_name: str, value: float, msg: str):
        """Send alert notification"""
        logger.warning(f"ALERT: {metric_name} {msg}")

        # Send to voice notification if available
        try:
            subprocess.run([
                "/mnt/agentic-system/scripts/hooks/voice-notify.sh",
                f"Performance alert: {metric_name.replace('_', ' ')} is degraded"
            ], timeout=5, capture_output=True)
        except:
            pass

        # Log to notifications
        try:
            with open("/home/marc/agentic-system/logs/performance-warnings.log", "a") as f:
                f.write(json.dumps({
                    "event": "performance_alert",
                    "metric": metric_name,
                    "value": value,
                    "message": msg,
                    "timestamp": datetime.now().isoformat()
                }) + "\n")
        except:
            pass

    def _action_tune_retrieval(self, metric_name: str, value: float):
        """Tune memory retrieval parameters"""
        logger.info(f"Tuning retrieval - relevance at {value:.3f}")

        # Could adjust: over_retrieve_factor, reranking model, hybrid weights
        # For now, just log the suggestion
        suggestion = {
            "action": "increase_over_retrieve_factor",
            "reason": f"Relevance score {value:.3f} below target",
            "current_value": value,
            "suggested_change": "Increase over_retrieve_factor from 4 to 6"
        }

        logger.info(f"Retrieval tuning suggestion: {json.dumps(suggestion)}")

    def _action_tune_soundtrack(self, metric_name: str, value: float):
        """Tune soundtrack parameters"""
        logger.info(f"Tuning soundtrack - accuracy at {value:.3f}")

        # Could adjust: intensity thresholds, decay rates
        suggestion = {
            "action": "adjust_intensity_thresholds",
            "reason": f"Intensity accuracy {value:.3f} below target",
            "current_value": value
        }

        logger.info(f"Soundtrack tuning suggestion: {json.dumps(suggestion)}")

    def _action_investigate_errors(self, metric_name: str, value: float):
        """Investigate high error rate"""
        logger.warning(f"Investigating errors - rate at {value:.3f}")

        # Query recent errors
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT action_type, COUNT(*) as count, AVG(success_score) as avg_score
                FROM action_outcomes
                WHERE success_score < 0.5 AND executed_at > datetime('now', '-1 hour')
                GROUP BY action_type
                ORDER BY count DESC
                LIMIT 5
            """)
            error_breakdown = cursor.fetchall()
            conn.close()

            if error_breakdown:
                logger.warning(f"Error breakdown: {error_breakdown}")
                # Could trigger specific fixes based on error patterns
        except Exception as e:
            logger.error(f"Failed to investigate errors: {e}")

    async def check_metrics(self):
        """Check all monitored metrics"""
        for metric_name, config in MONITORED_METRICS.items():
            try:
                value = self.get_metric_value(metric_name)
                if value is None:
                    continue

                # Check for threshold violation
                threshold_msg = self.check_threshold(metric_name, value)
                if threshold_msg:
                    logger.warning(f"Metric {metric_name}: {threshold_msg}")
                    self.take_action(metric_name, value, threshold_msg)
                    continue

                # Check for anomaly
                if self.detect_anomaly(metric_name, value):
                    logger.info(f"Anomaly detected for {metric_name}: {value:.3f}")

            except Exception as e:
                logger.error(f"Error checking metric {metric_name}: {e}")

    async def check_for_consolidation_triggers(self):
        """Check if memory consolidation should be triggered"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # Check if we have enough new episodes since last consolidation
            cursor.execute("""
                SELECT COUNT(*) FROM episodic_memories
                WHERE recorded_at > (
                    SELECT COALESCE(MAX(recorded_at), datetime('now', '-7 days'))
                    FROM consolidation_evals
                )
            """)
            new_episodes = cursor.fetchone()[0] or 0
            conn.close()

            if new_episodes > 100:
                logger.info(f"Triggering consolidation: {new_episodes} new episodes")
                try:
                    subprocess.run([
                        "systemctl", "restart", "memory-consolidation"
                    ], timeout=10, capture_output=True)
                except:
                    pass

        except Exception as e:
            logger.debug(f"Consolidation check failed: {e}")

    async def run(self):
        """Main daemon loop"""
        logger.info("Self-Improvement Daemon starting...")
        logger.info(f"Monitoring {len(MONITORED_METRICS)} metrics")

        while self.running:
            try:
                await self.check_metrics()
                await self.check_for_consolidation_triggers()
            except Exception as e:
                logger.error(f"Error in main loop: {e}")

            await asyncio.sleep(CONFIG["check_interval_seconds"])


def main():
    daemon = SelfImprovementDaemon()

    # Handle shutdown
    import signal
    def shutdown(sig, frame):
        logger.info("Shutting down...")
        daemon.running = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    asyncio.run(daemon.run())


if __name__ == "__main__":
    main()
