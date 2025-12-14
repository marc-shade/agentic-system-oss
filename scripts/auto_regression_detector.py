#!/usr/bin/env python3
"""
Auto Regression Detector and Rollback System

Continuously monitors system performance metrics and automatically
detects + rolls back performance regressions.

Features:
- Pulls metrics from Prometheus
- Compares against baseline thresholds
- Triggers rollback on significant degradation (>15%)
- Uses git to find last known good commit
- Integrates with marker system to prevent watchdog conflicts

Usage:
    python3 auto_regression_detector.py [--check-once] [--dry-run]
"""

import os
import sys
import json
import time
import signal
import subprocess
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Platform-aware storage path detection
import platform

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


# Storage base path
STORAGE_BASE = _get_storage_base()
PROMETHEUS_URL = "http://localhost:9700"
BASELINE_FILE = STORAGE_BASE / "performance-snapshots" / "baseline_metrics.json"
MARKER_FILE = Path.home() / ".claude" / ".config_modifications.jsonl"


@dataclass
class MetricThreshold:
    """Threshold for a single metric."""
    name: str
    query: str
    threshold: float  # max acceptable value (or min for inverse metrics)
    regression_pct: float = 0.15  # 15% degradation triggers alert
    inverse: bool = False  # True if lower is worse (e.g., success rate)
    critical: bool = False  # Critical metrics trigger immediate rollback


@dataclass
class RegressionEvent:
    """A detected regression event."""
    metric: str
    baseline_value: float
    current_value: float
    degradation_pct: float
    timestamp: datetime
    critical: bool


class AutoRegressionDetector:
    """Automatically detect and rollback performance regressions."""

    # Default metrics to monitor
    DEFAULT_METRICS = [
        MetricThreshold(
            name="mcp_request_latency",
            query='histogram_quantile(0.95, rate(mcp_request_duration_seconds_bucket[5m]))',
            threshold=2.0,  # 2 seconds max
            regression_pct=0.20,
            critical=True
        ),
        MetricThreshold(
            name="memory_usage_pct",
            query='(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100',
            threshold=85.0,  # 85% max
            regression_pct=0.15
        ),
        MetricThreshold(
            name="cpu_usage_pct",
            query='100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            threshold=80.0,  # 80% max
            regression_pct=0.20
        ),
        MetricThreshold(
            name="service_up",
            query='sum(up)',
            threshold=0.0,  # Any services down is bad
            inverse=True,  # Higher is better
            regression_pct=0.10,
            critical=True
        ),
    ]

    def __init__(
        self,
        prometheus_url: str = PROMETHEUS_URL,
        check_interval: int = 60,
        dry_run: bool = False
    ):
        self.prometheus_url = prometheus_url
        self.check_interval = check_interval
        self.dry_run = dry_run
        self.metrics = self.DEFAULT_METRICS
        self.baseline: Dict[str, float] = {}
        self.running = True
        self.regression_history: List[RegressionEvent] = []
        self.consecutive_regressions: Dict[str, int] = {}

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def load_baseline(self) -> bool:
        """Load baseline metrics from file or create from current state."""
        if BASELINE_FILE.exists():
            try:
                with open(BASELINE_FILE) as f:
                    self.baseline = json.load(f)
                logger.info(f"Loaded baseline from {BASELINE_FILE}")
                return True
            except Exception as e:
                logger.warning(f"Failed to load baseline: {e}")

        # Create baseline from current metrics
        logger.info("Creating new baseline from current metrics...")
        return self.update_baseline()

    def update_baseline(self) -> bool:
        """Update baseline with current metrics."""
        try:
            for metric in self.metrics:
                value = self.query_prometheus(metric.query)
                if value is not None:
                    self.baseline[metric.name] = value
                    logger.info(f"Baseline {metric.name}: {value:.4f}")

            # Save baseline
            BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(BASELINE_FILE, 'w') as f:
                json.dump(self.baseline, f, indent=2)

            logger.info(f"Saved baseline to {BASELINE_FILE}")
            return True

        except Exception as e:
            logger.error(f"Failed to update baseline: {e}")
            return False

    def query_prometheus(self, query: str) -> Optional[float]:
        """Query Prometheus for a metric value."""
        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/query",
                params={"query": query},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()

            if data["status"] == "success" and data["data"]["result"]:
                value = float(data["data"]["result"][0]["value"][1])
                return value
            return None

        except requests.exceptions.ConnectionError:
            logger.debug("Prometheus not available")
            return None
        except Exception as e:
            logger.debug(f"Prometheus query failed: {e}")
            return None

    def check_metric(self, metric: MetricThreshold) -> Optional[RegressionEvent]:
        """Check a single metric for regression."""
        current = self.query_prometheus(metric.query)
        if current is None:
            return None

        baseline = self.baseline.get(metric.name)
        if baseline is None:
            # First time seeing this metric, set baseline
            self.baseline[metric.name] = current
            return None

        # Calculate degradation
        if metric.inverse:
            # Lower is worse (e.g., success rate)
            if baseline == 0:
                degradation_pct = 0
            else:
                degradation_pct = (baseline - current) / baseline
        else:
            # Higher is worse (e.g., latency)
            if baseline == 0:
                degradation_pct = 1.0 if current > 0 else 0
            else:
                degradation_pct = (current - baseline) / baseline

        # Check if regression threshold exceeded
        if degradation_pct > metric.regression_pct:
            return RegressionEvent(
                metric=metric.name,
                baseline_value=baseline,
                current_value=current,
                degradation_pct=degradation_pct,
                timestamp=datetime.now(),
                critical=metric.critical
            )

        return None

    def check_all_metrics(self) -> List[RegressionEvent]:
        """Check all metrics for regressions."""
        regressions = []

        for metric in self.metrics:
            event = self.check_metric(metric)
            if event:
                # Track consecutive regressions
                self.consecutive_regressions[metric.name] = \
                    self.consecutive_regressions.get(metric.name, 0) + 1
                regressions.append(event)
            else:
                # Reset consecutive count on healthy check
                self.consecutive_regressions[metric.name] = 0

        return regressions

    def find_last_good_commit(self) -> Optional[str]:
        """Find the last known good commit before regression."""
        try:
            # Get recent commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-20"],
                capture_output=True,
                text=True,
                cwd=STORAGE_BASE,
                timeout=10
            )

            if result.returncode != 0:
                return None

            commits = result.stdout.strip().split('\n')
            if len(commits) > 1:
                # Return second commit (one before current)
                return commits[1].split()[0]
            return None

        except Exception as e:
            logger.error(f"Failed to find last good commit: {e}")
            return None

    def execute_rollback(self, commit: str, reason: str) -> bool:
        """Execute git rollback to specified commit."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would rollback to commit {commit}")
            return True

        try:
            # First, stash any local changes
            subprocess.run(
                ["git", "stash"],
                cwd=STORAGE_BASE,
                timeout=30
            )

            # Reset to previous commit
            result = subprocess.run(
                ["git", "reset", "--hard", commit],
                capture_output=True,
                text=True,
                cwd=STORAGE_BASE,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Git reset failed: {result.stderr}")
                return False

            # Record rollback in marker file
            self.record_marker({
                "action": "auto_rollback",
                "commit": commit,
                "reason": reason,
                "timestamp": datetime.now().isoformat(),
                "source": "auto_regression_detector"
            })

            logger.info(f"Successfully rolled back to commit {commit}")
            return True

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False

    def record_marker(self, marker: Dict[str, Any]):
        """Record action in marker file for watchdog compatibility."""
        try:
            with open(MARKER_FILE, 'a') as f:
                f.write(json.dumps(marker) + '\n')
        except Exception as e:
            logger.warning(f"Failed to record marker: {e}")

    def restart_services(self) -> bool:
        """Restart affected services after rollback."""
        logger.info("Restarting services after rollback...")

        try:
            # Restart MCP servers by killing parent process
            # (they'll be restarted by health monitor)
            subprocess.run(
                ["pkill", "-f", "mcp-servers"],
                timeout=10
            )

            # Restart Temporal workers if running
            subprocess.run(
                ["systemctl", "--user", "restart", "temporal-worker"],
                timeout=30,
                capture_output=True
            )

            logger.info("Services restarted")
            return True

        except Exception as e:
            logger.warning(f"Service restart partially failed: {e}")
            return False

    def handle_regression(self, regressions: List[RegressionEvent]):
        """Handle detected regressions."""
        critical = [r for r in regressions if r.critical]
        non_critical = [r for r in regressions if not r.critical]

        # Log all regressions
        for reg in regressions:
            logger.warning(
                f"REGRESSION: {reg.metric} - "
                f"baseline: {reg.baseline_value:.4f}, "
                f"current: {reg.current_value:.4f}, "
                f"degradation: {reg.degradation_pct*100:.1f}%"
                f"{' [CRITICAL]' if reg.critical else ''}"
            )
            self.regression_history.append(reg)

        # Check for consecutive critical regressions
        should_rollback = False
        rollback_reason = ""

        if critical:
            # Critical regression - check if persistent (2+ consecutive)
            for reg in critical:
                if self.consecutive_regressions.get(reg.metric, 0) >= 2:
                    should_rollback = True
                    rollback_reason = f"Critical regression: {reg.metric} degraded {reg.degradation_pct*100:.1f}%"
                    break

        elif len(non_critical) >= 3:
            # Multiple non-critical regressions
            should_rollback = True
            rollback_reason = f"Multiple regressions: {[r.metric for r in non_critical]}"

        if should_rollback:
            logger.error(f"ROLLBACK TRIGGERED: {rollback_reason}")

            commit = self.find_last_good_commit()
            if commit:
                if self.execute_rollback(commit, rollback_reason):
                    self.restart_services()
                    # Update baseline after rollback
                    time.sleep(10)  # Wait for services to stabilize
                    self.update_baseline()
            else:
                logger.error("Could not find commit to rollback to")

    def get_status(self) -> Dict[str, Any]:
        """Get current status report."""
        healthy_metrics = []
        degraded_metrics = []

        for metric in self.metrics:
            current = self.query_prometheus(metric.query)
            baseline = self.baseline.get(metric.name)

            if current is None:
                continue

            status = {
                "name": metric.name,
                "current": current,
                "baseline": baseline,
                "threshold": metric.threshold
            }

            if baseline and current:
                if metric.inverse:
                    degradation = (baseline - current) / baseline if baseline else 0
                else:
                    degradation = (current - baseline) / baseline if baseline else 0

                status["degradation_pct"] = degradation
                status["healthy"] = degradation <= metric.regression_pct

                if status["healthy"]:
                    healthy_metrics.append(status)
                else:
                    degraded_metrics.append(status)
            else:
                healthy_metrics.append(status)

        return {
            "timestamp": datetime.now().isoformat(),
            "prometheus_available": self.query_prometheus("up") is not None,
            "healthy_count": len(healthy_metrics),
            "degraded_count": len(degraded_metrics),
            "healthy_metrics": healthy_metrics,
            "degraded_metrics": degraded_metrics,
            "recent_regressions": len(self.regression_history),
            "dry_run": self.dry_run
        }

    def run(self, check_once: bool = False):
        """Main monitoring loop."""
        logger.info("Auto Regression Detector starting...")

        if not self.load_baseline():
            logger.warning("Running without baseline - will create from first check")

        if self.dry_run:
            logger.info("DRY RUN MODE - no actual rollbacks will be performed")

        if check_once:
            regressions = self.check_all_metrics()
            status = self.get_status()
            print(json.dumps(status, indent=2, default=str))
            return 0 if not regressions else 1

        while self.running:
            try:
                regressions = self.check_all_metrics()

                if regressions:
                    self.handle_regression(regressions)
                else:
                    logger.debug("All metrics healthy")

                # Sleep with interrupt checking
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)

        logger.info("Auto Regression Detector stopped")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Auto Regression Detector")
    parser.add_argument("--check-once", action="store_true",
                       help="Check once and exit")
    parser.add_argument("--dry-run", action="store_true",
                       help="Don't perform actual rollbacks")
    parser.add_argument("--update-baseline", action="store_true",
                       help="Update baseline from current metrics")
    parser.add_argument("--interval", type=int, default=60,
                       help="Check interval in seconds (default: 60)")

    args = parser.parse_args()

    detector = AutoRegressionDetector(
        check_interval=args.interval,
        dry_run=args.dry_run
    )

    if args.update_baseline:
        detector.update_baseline()
        return 0

    return detector.run(check_once=args.check_once)


if __name__ == "__main__":
    sys.exit(main())
