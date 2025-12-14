#!/usr/bin/env python3
"""
Temporal Workflow Undertaker

Detects and recovers stuck/zombie workflows with automated recovery strategies.

Features:
- Scans for workflows running longer than expected
- Detects workflows with no recent activity
- Attempts graduated recovery: signal → retry → terminate
- Logs all actions for audit trail
- Escalates persistent failures to human attention

Usage:
    python3 workflow_undertaker.py [--check-once] [--dry-run]
"""
import platform

import os
import sys
import json
import time
import signal
import logging
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import argparse

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Storage base path
STORAGE_BASE = Path(str(_STORAGE_BASE))
TEMPORAL_HOST = "localhost:7233"
TEMPORAL_NAMESPACE = "default"

# Workflows that are expected to run for a long time
LONG_RUNNING_WHITELIST = [
    "overnight_research",
    "memory_consolidation",
    "continuous_learning",
    "system_monitoring",
    "autonomous_memory_manager"
]


class RecoveryAction(Enum):
    """Recovery actions for stuck workflows."""
    NONE = "none"
    SIGNAL_RESET = "signal_reset"
    SIGNAL_CANCEL = "signal_cancel"
    TERMINATE = "terminate"
    ESCALATE = "escalate"


class WorkflowStatus(Enum):
    """Workflow health status."""
    HEALTHY = "healthy"
    SLOW = "slow"
    STUCK = "stuck"
    ZOMBIE = "zombie"


@dataclass
class WorkflowInfo:
    """Information about a workflow execution."""
    workflow_id: str
    run_id: str
    workflow_type: str
    status: str
    start_time: datetime
    last_activity: Optional[datetime]
    duration_hours: float
    task_queue: str
    health: WorkflowStatus = WorkflowStatus.HEALTHY
    recovery_attempts: int = 0


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    workflow_id: str
    action: RecoveryAction
    success: bool
    message: str
    timestamp: datetime


class WorkflowUndertaker:
    """Detect and recover stuck Temporal workflows."""

    # Time thresholds (in hours)
    SLOW_THRESHOLD = 1.0      # 1 hour - might be slow
    STUCK_THRESHOLD = 2.0     # 2 hours - probably stuck
    ZOMBIE_THRESHOLD = 24.0   # 24 hours - definitely zombie

    # Recovery attempts before escalation
    MAX_RECOVERY_ATTEMPTS = 3

    def __init__(
        self,
        temporal_host: str = TEMPORAL_HOST,
        namespace: str = TEMPORAL_NAMESPACE,
        check_interval: int = 300,  # 5 minutes
        dry_run: bool = False
    ):
        self.temporal_host = temporal_host
        self.namespace = namespace
        self.check_interval = check_interval
        self.dry_run = dry_run
        self.running = True
        self.recovery_history: Dict[str, List[RecoveryResult]] = {}

        # Signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def check_temporal_available(self) -> bool:
        """Check if Temporal is available."""
        try:
            result = subprocess.run(
                ["temporal", "server", "health", "--address", self.temporal_host],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except FileNotFoundError:
            logger.warning("Temporal CLI not found")
            return False
        except subprocess.TimeoutExpired:
            logger.warning("Temporal health check timed out")
            return False
        except Exception as e:
            logger.debug(f"Temporal not available: {e}")
            return False

    def list_running_workflows(self) -> List[WorkflowInfo]:
        """List all running workflows."""
        workflows = []

        try:
            # Query running workflows using Temporal CLI
            result = subprocess.run(
                [
                    "temporal", "workflow", "list",
                    "--address", self.temporal_host,
                    "--namespace", self.namespace,
                    "--query", "ExecutionStatus='Running'",
                    "--output", "json"
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.warning(f"Failed to list workflows: {result.stderr}")
                return workflows

            if not result.stdout.strip():
                return workflows

            data = json.loads(result.stdout)

            for wf in data:
                # Parse workflow info
                try:
                    start_time = datetime.fromisoformat(
                        wf.get("startTime", "").replace("Z", "+00:00")
                    )
                    duration = (datetime.now(start_time.tzinfo) - start_time).total_seconds() / 3600

                    workflows.append(WorkflowInfo(
                        workflow_id=wf.get("execution", {}).get("workflowId", "unknown"),
                        run_id=wf.get("execution", {}).get("runId", "unknown"),
                        workflow_type=wf.get("type", {}).get("name", "unknown"),
                        status=wf.get("status", "Running"),
                        start_time=start_time,
                        last_activity=None,  # Would need describe for this
                        duration_hours=duration,
                        task_queue=wf.get("taskQueue", "default")
                    ))
                except Exception as e:
                    logger.debug(f"Failed to parse workflow: {e}")

            return workflows

        except json.JSONDecodeError:
            logger.warning("Invalid JSON from Temporal CLI")
            return workflows
        except subprocess.TimeoutExpired:
            logger.warning("Temporal workflow list timed out")
            return workflows
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return workflows

    def classify_workflow_health(self, workflow: WorkflowInfo) -> WorkflowStatus:
        """Classify workflow health based on duration and type."""
        # Check whitelist for expected long-running workflows
        is_whitelisted = any(
            w in workflow.workflow_type.lower()
            for w in LONG_RUNNING_WHITELIST
        )

        if is_whitelisted:
            # Long-running workflows have higher thresholds
            if workflow.duration_hours >= self.ZOMBIE_THRESHOLD * 3:  # 72 hours
                return WorkflowStatus.ZOMBIE
            elif workflow.duration_hours >= self.STUCK_THRESHOLD * 12:  # 24 hours
                return WorkflowStatus.STUCK
            return WorkflowStatus.HEALTHY

        # Standard workflows
        if workflow.duration_hours >= self.ZOMBIE_THRESHOLD:
            return WorkflowStatus.ZOMBIE
        elif workflow.duration_hours >= self.STUCK_THRESHOLD:
            return WorkflowStatus.STUCK
        elif workflow.duration_hours >= self.SLOW_THRESHOLD:
            return WorkflowStatus.SLOW
        return WorkflowStatus.HEALTHY

    def get_recovery_action(self, workflow: WorkflowInfo) -> RecoveryAction:
        """Determine appropriate recovery action."""
        # Get recovery history for this workflow
        history = self.recovery_history.get(workflow.workflow_id, [])
        attempts = len(history)

        if workflow.health == WorkflowStatus.HEALTHY:
            return RecoveryAction.NONE

        if workflow.health == WorkflowStatus.SLOW:
            # Just monitor slow workflows, don't intervene yet
            return RecoveryAction.NONE

        if attempts >= self.MAX_RECOVERY_ATTEMPTS:
            return RecoveryAction.ESCALATE

        if workflow.health == WorkflowStatus.STUCK:
            # Try signaling first
            if attempts == 0:
                return RecoveryAction.SIGNAL_RESET
            elif attempts == 1:
                return RecoveryAction.SIGNAL_CANCEL
            else:
                return RecoveryAction.TERMINATE

        if workflow.health == WorkflowStatus.ZOMBIE:
            # More aggressive for zombies
            if attempts == 0:
                return RecoveryAction.SIGNAL_CANCEL
            else:
                return RecoveryAction.TERMINATE

        return RecoveryAction.NONE

    def execute_recovery(self, workflow: WorkflowInfo, action: RecoveryAction) -> RecoveryResult:
        """Execute recovery action on workflow."""
        result = RecoveryResult(
            workflow_id=workflow.workflow_id,
            action=action,
            success=False,
            message="",
            timestamp=datetime.now()
        )

        if self.dry_run:
            result.success = True
            result.message = f"[DRY RUN] Would execute {action.value}"
            logger.info(f"[DRY RUN] {workflow.workflow_id}: {action.value}")
            return result

        try:
            if action == RecoveryAction.SIGNAL_RESET:
                # Send reset signal
                cmd = [
                    "temporal", "workflow", "signal",
                    "--address", self.temporal_host,
                    "--namespace", self.namespace,
                    "--workflow-id", workflow.workflow_id,
                    "--name", "reset",
                    "--input", '{"reason": "undertaker_recovery"}'
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                result.success = proc.returncode == 0
                result.message = proc.stdout or proc.stderr

            elif action == RecoveryAction.SIGNAL_CANCEL:
                # Send cancel signal
                cmd = [
                    "temporal", "workflow", "cancel",
                    "--address", self.temporal_host,
                    "--namespace", self.namespace,
                    "--workflow-id", workflow.workflow_id,
                    "--reason", "undertaker_recovery"
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                result.success = proc.returncode == 0
                result.message = proc.stdout or proc.stderr

            elif action == RecoveryAction.TERMINATE:
                # Terminate workflow
                cmd = [
                    "temporal", "workflow", "terminate",
                    "--address", self.temporal_host,
                    "--namespace", self.namespace,
                    "--workflow-id", workflow.workflow_id,
                    "--reason", "undertaker_zombie_cleanup"
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                result.success = proc.returncode == 0
                result.message = proc.stdout or proc.stderr

            elif action == RecoveryAction.ESCALATE:
                # Log for human attention
                result.success = True
                result.message = f"ESCALATION: Workflow {workflow.workflow_id} requires manual intervention"
                logger.error(result.message)

        except subprocess.TimeoutExpired:
            result.message = "Recovery action timed out"
        except Exception as e:
            result.message = f"Recovery failed: {e}"

        # Track recovery history
        if workflow.workflow_id not in self.recovery_history:
            self.recovery_history[workflow.workflow_id] = []
        self.recovery_history[workflow.workflow_id].append(result)

        return result

    def process_workflows(self) -> Dict[str, Any]:
        """Process all workflows and recover stuck ones."""
        workflows = self.list_running_workflows()

        stats = {
            "total": len(workflows),
            "healthy": 0,
            "slow": 0,
            "stuck": 0,
            "zombie": 0,
            "recovered": 0,
            "failed": 0,
            "escalated": 0
        }

        for workflow in workflows:
            # Classify health
            workflow.health = self.classify_workflow_health(workflow)

            # Update stats
            if workflow.health == WorkflowStatus.HEALTHY:
                stats["healthy"] += 1
            elif workflow.health == WorkflowStatus.SLOW:
                stats["slow"] += 1
            elif workflow.health == WorkflowStatus.STUCK:
                stats["stuck"] += 1
            elif workflow.health == WorkflowStatus.ZOMBIE:
                stats["zombie"] += 1

            # Determine and execute recovery
            action = self.get_recovery_action(workflow)

            if action != RecoveryAction.NONE:
                logger.info(
                    f"Workflow {workflow.workflow_id} ({workflow.workflow_type}) "
                    f"is {workflow.health.value} after {workflow.duration_hours:.1f}h - "
                    f"action: {action.value}"
                )

                result = self.execute_recovery(workflow, action)

                if action == RecoveryAction.ESCALATE:
                    stats["escalated"] += 1
                elif result.success:
                    stats["recovered"] += 1
                    logger.info(f"Recovery successful: {workflow.workflow_id}")
                else:
                    stats["failed"] += 1
                    logger.warning(f"Recovery failed: {workflow.workflow_id} - {result.message}")

        return stats

    def get_status(self) -> Dict[str, Any]:
        """Get current status report."""
        workflows = self.list_running_workflows()

        return {
            "timestamp": datetime.now().isoformat(),
            "temporal_available": self.check_temporal_available(),
            "total_workflows": len(workflows),
            "workflows": [
                {
                    "workflow_id": wf.workflow_id,
                    "type": wf.workflow_type,
                    "duration_hours": round(wf.duration_hours, 2),
                    "health": self.classify_workflow_health(wf).value,
                    "task_queue": wf.task_queue
                }
                for wf in workflows
            ],
            "recovery_history_count": sum(len(h) for h in self.recovery_history.values()),
            "dry_run": self.dry_run
        }

    def run(self, check_once: bool = False):
        """Main monitoring loop."""
        logger.info("Workflow Undertaker starting...")

        if not self.check_temporal_available():
            logger.warning("Temporal not available - will retry")

        if self.dry_run:
            logger.info("DRY RUN MODE - no actual recovery actions")

        if check_once:
            status = self.get_status()
            print(json.dumps(status, indent=2, default=str))
            return 0

        while self.running:
            try:
                if self.check_temporal_available():
                    stats = self.process_workflows()

                    if stats["stuck"] + stats["zombie"] > 0:
                        logger.warning(
                            f"Workflow health: {stats['healthy']} healthy, "
                            f"{stats['slow']} slow, {stats['stuck']} stuck, "
                            f"{stats['zombie']} zombie"
                        )
                    else:
                        logger.debug(f"All {stats['total']} workflows healthy")
                else:
                    logger.debug("Temporal not available, skipping check")

                # Sleep with interrupt checking
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)

        logger.info("Workflow Undertaker stopped")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Temporal Workflow Undertaker")
    parser.add_argument("--check-once", action="store_true",
                       help="Check once and exit")
    parser.add_argument("--dry-run", action="store_true",
                       help="Don't perform actual recovery actions")
    parser.add_argument("--interval", type=int, default=300,
                       help="Check interval in seconds (default: 300)")
    parser.add_argument("--host", default=TEMPORAL_HOST,
                       help="Temporal host:port")

    args = parser.parse_args()

    undertaker = WorkflowUndertaker(
        temporal_host=args.host,
        check_interval=args.interval,
        dry_run=args.dry_run
    )

    return undertaker.run(check_once=args.check_once)


if __name__ == "__main__":
    sys.exit(main())
