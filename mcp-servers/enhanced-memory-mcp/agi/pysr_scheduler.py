#!/usr/bin/env python3
"""
PySR Periodic Discovery Scheduler

Provides scheduled automatic execution of PySR equation discovery
based on configurable intervals and conditions.

This allows the AGI system to continuously learn and update its
mathematical models as new data accumulates.
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Callable
import threading

logger = logging.getLogger("pysr-scheduler")

# Memory directory
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
SCHEDULER_STATE_FILE = MEMORY_DIR / "pysr_scheduler_state.json"


class PySRScheduler:
    """
    Manages periodic PySR discovery jobs.

    Features:
    - Configurable discovery intervals
    - Automatic triggering based on hooks
    - Manual trigger capability
    - State persistence across restarts
    - Async execution for non-blocking operation
    """

    def __init__(self):
        self.state = self._load_state()
        self.running = False
        self.scheduler_thread: Optional[threading.Thread] = None

        # Default configuration
        self.config = {
            "auto_discovery_enabled": True,
            "discovery_interval_hours": 168,  # 7 days default
            "check_interval_seconds": 3600,  # Check every hour
            "consolidation_before_discovery": True,
            "min_time_since_last_discovery": 24  # Minimum 24 hours between discoveries
        }

        # Load saved config
        if "config" in self.state:
            self.config.update(self.state["config"])

    def _load_state(self) -> Dict[str, Any]:
        """Load scheduler state from file."""
        if SCHEDULER_STATE_FILE.exists():
            try:
                with open(SCHEDULER_STATE_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load scheduler state: {e}")

        return {
            "last_check": None,
            "last_discovery": None,
            "next_scheduled": None,
            "discovery_count": 0,
            "auto_discoveries": 0,
            "manual_discoveries": 0
        }

    def _save_state(self):
        """Save scheduler state to file."""
        try:
            MEMORY_DIR.mkdir(parents=True, exist_ok=True)
            self.state["config"] = self.config

            with open(SCHEDULER_STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save scheduler state: {e}")

    def configure(
        self,
        auto_discovery_enabled: Optional[bool] = None,
        discovery_interval_hours: Optional[int] = None,
        check_interval_seconds: Optional[int] = None,
        consolidation_before_discovery: Optional[bool] = None,
        min_time_since_last_discovery: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Configure scheduler settings.

        Args:
            auto_discovery_enabled: Enable/disable automatic discovery
            discovery_interval_hours: Hours between scheduled discoveries
            check_interval_seconds: Seconds between scheduler checks
            consolidation_before_discovery: Run consolidation before discovery
            min_time_since_last_discovery: Minimum hours between discoveries

        Returns:
            Updated configuration
        """
        if auto_discovery_enabled is not None:
            self.config["auto_discovery_enabled"] = auto_discovery_enabled

        if discovery_interval_hours is not None:
            self.config["discovery_interval_hours"] = discovery_interval_hours

        if check_interval_seconds is not None:
            self.config["check_interval_seconds"] = check_interval_seconds

        if consolidation_before_discovery is not None:
            self.config["consolidation_before_discovery"] = consolidation_before_discovery

        if min_time_since_last_discovery is not None:
            self.config["min_time_since_last_discovery"] = min_time_since_last_discovery

        self._save_state()

        logger.info(f"Scheduler configured: {self.config}")

        return {
            "success": True,
            "config": self.config
        }

    def should_run_discovery(self) -> Dict[str, Any]:
        """
        Check if discovery should run now.

        Returns:
            Decision and reasons
        """
        if not self.config["auto_discovery_enabled"]:
            return {
                "should_run": False,
                "reason": "Auto-discovery disabled"
            }

        # Check minimum time since last discovery
        last_discovery = self.state.get("last_discovery")
        if last_discovery:
            try:
                last_time = datetime.fromisoformat(last_discovery)
                hours_since = (datetime.now() - last_time).total_seconds() / 3600

                if hours_since < self.config["min_time_since_last_discovery"]:
                    return {
                        "should_run": False,
                        "reason": f"Too soon since last discovery ({hours_since:.1f}h < {self.config['min_time_since_last_discovery']}h)"
                    }
            except Exception as e:
                logger.error(f"Failed to parse last discovery time: {e}")

        # Check scheduled interval
        if last_discovery:
            try:
                last_time = datetime.fromisoformat(last_discovery)
                hours_since = (datetime.now() - last_time).total_seconds() / 3600

                if hours_since >= self.config["discovery_interval_hours"]:
                    return {
                        "should_run": True,
                        "reason": f"Scheduled interval reached ({hours_since:.1f}h >= {self.config['discovery_interval_hours']}h)"
                    }
            except Exception as e:
                logger.error(f"Failed to parse last discovery time: {e}")
        else:
            # Never run before
            return {
                "should_run": True,
                "reason": "First discovery (never run before)"
            }

        # Check hooks triggers
        try:
            from agi.pysr_hooks import should_trigger_discovery
            trigger_check = should_trigger_discovery()

            if trigger_check["should_trigger"]:
                return {
                    "should_run": True,
                    "reason": f"Hooks triggered: {', '.join(trigger_check['reasons'])}",
                    "trigger_details": trigger_check
                }
        except Exception as e:
            logger.debug(f"Hooks check failed: {e}")

        return {
            "should_run": False,
            "reason": "No trigger conditions met"
        }

    async def run_discovery_cycle(self, triggered_by: str = "scheduler") -> Dict[str, Any]:
        """
        Execute a complete discovery cycle.

        Args:
            triggered_by: What triggered this discovery ("scheduler", "manual", "hooks")

        Returns:
            Results from discovery cycle
        """
        logger.info(f"Starting discovery cycle (triggered by: {triggered_by})")

        results = {
            "started_at": datetime.now().isoformat(),
            "triggered_by": triggered_by
        }

        # Step 1: Run consolidation (if enabled)
        if self.config["consolidation_before_discovery"]:
            try:
                logger.info("Running memory consolidation before discovery...")
                from agi.consolidation import ConsolidationEngine

                consolidation = ConsolidationEngine()
                consolidation_results = consolidation.run_full_consolidation(
                    time_window_hours=self.config["discovery_interval_hours"]
                )

                results["consolidation"] = consolidation_results
                logger.info(f"Consolidation complete: {consolidation_results}")

            except Exception as e:
                logger.error(f"Consolidation failed: {e}")
                results["consolidation"] = {"error": str(e)}

        # Step 2: Run PySR discovery
        try:
            logger.info("Running PySR equation discovery...")
            from agi.pysr_symbolic_regression import get_engine

            engine = get_engine()
            discovery_results = engine.run_full_discovery()

            results["discovery"] = discovery_results
            logger.info(f"PySR discovery complete")

            # Update state
            self.state["last_discovery"] = datetime.now().isoformat()
            self.state["discovery_count"] = self.state.get("discovery_count", 0) + 1

            if triggered_by == "scheduler":
                self.state["auto_discoveries"] = self.state.get("auto_discoveries", 0) + 1
            elif triggered_by == "manual":
                self.state["manual_discoveries"] = self.state.get("manual_discoveries", 0) + 1

            # Calculate next scheduled time
            next_time = datetime.now() + timedelta(hours=self.config["discovery_interval_hours"])
            self.state["next_scheduled"] = next_time.isoformat()

            self._save_state()

            # Notify hooks of completion
            try:
                from agi.pysr_hooks import on_discovery_complete
                on_discovery_complete(discovery_results)
            except Exception as e:
                logger.debug(f"Hooks notification failed: {e}")

        except Exception as e:
            logger.error(f"PySR discovery failed: {e}")
            results["discovery"] = {"error": str(e)}

        results["completed_at"] = datetime.now().isoformat()

        logger.info(f"Discovery cycle completed: {triggered_by}")

        return results

    def _scheduler_loop(self):
        """Background scheduler loop (runs in thread)."""
        logger.info("PySR scheduler started")

        while self.running:
            try:
                # Check if discovery should run
                self.state["last_check"] = datetime.now().isoformat()
                self._save_state()

                check_result = self.should_run_discovery()

                if check_result["should_run"]:
                    logger.info(f"Triggering automatic discovery: {check_result['reason']}")

                    # Run discovery cycle synchronously in thread
                    # (Can't use async in daemon thread easily)
                    import subprocess
                    import sys

                    # Create a simple script to run discovery
                    script = f"""
import asyncio
from agi.pysr_scheduler import get_scheduler

async def run():
    scheduler = get_scheduler()
    await scheduler.run_discovery_cycle(triggered_by="scheduler")

asyncio.run(run())
"""

                    # Execute in subprocess to avoid blocking
                    result = subprocess.run(
                        [sys.executable, "-c", script],
                        capture_output=True,
                        text=True,
                        cwd=str(Path(__file__).parent.parent)
                    )

                    if result.returncode != 0:
                        logger.error(f"Discovery subprocess failed: {result.stderr}")
                    else:
                        logger.info("Automatic discovery completed successfully")

            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")

            # Sleep until next check
            import time
            time.sleep(self.config["check_interval_seconds"])

        logger.info("PySR scheduler stopped")

    def start(self) -> Dict[str, Any]:
        """Start the scheduler background thread."""
        if self.running:
            return {
                "success": False,
                "message": "Scheduler already running"
            }

        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="PySRScheduler"
        )
        self.scheduler_thread.start()

        logger.info("PySR scheduler started successfully")

        return {
            "success": True,
            "message": "Scheduler started",
            "config": self.config,
            "next_check": (
                datetime.now() + timedelta(seconds=self.config["check_interval_seconds"])
            ).isoformat()
        }

    def stop(self) -> Dict[str, Any]:
        """Stop the scheduler background thread."""
        if not self.running:
            return {
                "success": False,
                "message": "Scheduler not running"
            }

        self.running = False

        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)

        logger.info("PySR scheduler stopped")

        return {
            "success": True,
            "message": "Scheduler stopped"
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        return {
            "running": self.running,
            "config": self.config,
            "state": self.state,
            "next_scheduled": self.state.get("next_scheduled"),
            "last_discovery": self.state.get("last_discovery"),
            "discovery_count": self.state.get("discovery_count", 0),
            "auto_discoveries": self.state.get("auto_discoveries", 0),
            "manual_discoveries": self.state.get("manual_discoveries", 0)
        }


# Singleton instance
_scheduler: Optional[PySRScheduler] = None


def get_scheduler() -> PySRScheduler:
    """Get or create singleton PySRScheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = PySRScheduler()
    return _scheduler
