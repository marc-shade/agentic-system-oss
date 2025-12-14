#!/usr/bin/env python3
"""
PySR Automatic Discovery Hooks

Provides hooks and triggers for automatic equation discovery based on
system events and data accumulation thresholds.
"""

import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

logger = logging.getLogger("pysr-hooks")

# Memory database path
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"
HOOKS_STATE_FILE = MEMORY_DIR / "pysr_hooks_state.json"


class PySRHooksManager:
    """
    Manages automatic PySR discovery triggers based on system events.

    Triggers include:
    - Data threshold reached (enough samples for training)
    - Scheduled periodic discovery (weekly/monthly)
    - Prediction accuracy degradation detected
    - New consolidation jobs completed
    """

    def __init__(self):
        self.state = self._load_state()
        self.thresholds = {
            "importance_min_samples": 50,
            "consolidation_min_samples": 20,
            "access_pattern_min_samples": 100,
            "discovery_interval_hours": 168,  # 7 days
            "min_accuracy_threshold": 0.5  # Re-train if R² drops below this
        }

    def _load_state(self) -> Dict[str, Any]:
        """Load hooks state from file."""
        if HOOKS_STATE_FILE.exists():
            try:
                with open(HOOKS_STATE_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load hooks state: {e}")

        return {
            "last_discovery": None,
            "last_importance_samples": 0,
            "last_consolidation_samples": 0,
            "last_access_samples": 0,
            "discovery_count": 0
        }

    def _save_state(self):
        """Save hooks state to file."""
        try:
            with open(HOOKS_STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save hooks state: {e}")

    def check_data_thresholds(self) -> Dict[str, bool]:
        """
        Check if sufficient data has accumulated for discovery.

        Returns:
            Dict indicating which equations have enough data for training
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        results = {}

        # Check importance equation data
        cursor.execute("SELECT COUNT(*) FROM entities WHERE importance_score IS NOT NULL")
        importance_count = cursor.fetchone()[0]
        results["importance_ready"] = (
            importance_count >= self.thresholds["importance_min_samples"] and
            importance_count > self.state.get("last_importance_samples", 0)
        )

        # Check consolidation equation data
        cursor.execute("SELECT COUNT(*) FROM consolidation_jobs WHERE status = 'completed'")
        consolidation_count = cursor.fetchone()[0]
        results["consolidation_ready"] = (
            consolidation_count >= self.thresholds["consolidation_min_samples"] and
            consolidation_count > self.state.get("last_consolidation_samples", 0)
        )

        # Check access pattern data
        cursor.execute("SELECT COUNT(*) FROM entities WHERE access_count > 0")
        access_count = cursor.fetchone()[0]
        results["access_pattern_ready"] = (
            access_count >= self.thresholds["access_pattern_min_samples"] and
            access_count > self.state.get("last_access_samples", 0)
        )

        conn.close()

        results["any_ready"] = any([
            results["importance_ready"],
            results["consolidation_ready"],
            results["access_pattern_ready"]
        ])

        return results

    def check_scheduled_discovery(self) -> bool:
        """
        Check if it's time for scheduled periodic discovery.

        Returns:
            True if discovery should run based on schedule
        """
        last_discovery = self.state.get("last_discovery")

        if not last_discovery:
            return True  # Never run before

        try:
            last_time = datetime.fromisoformat(last_discovery)
            hours_since = (datetime.now() - last_time).total_seconds() / 3600

            return hours_since >= self.thresholds["discovery_interval_hours"]
        except Exception as e:
            logger.error(f"Failed to parse last discovery time: {e}")
            return False

    def should_trigger_discovery(self) -> Dict[str, Any]:
        """
        Determine if automatic discovery should be triggered.

        Returns:
            Dict with trigger decision and reasons
        """
        data_check = self.check_data_thresholds()
        scheduled_check = self.check_scheduled_discovery()

        reasons = []
        if data_check["importance_ready"]:
            reasons.append("New importance data available")
        if data_check["consolidation_ready"]:
            reasons.append("New consolidation data available")
        if data_check["access_pattern_ready"]:
            reasons.append("New access pattern data available")
        if scheduled_check:
            reasons.append("Scheduled discovery interval reached")

        should_trigger = data_check["any_ready"] or scheduled_check

        return {
            "should_trigger": should_trigger,
            "reasons": reasons,
            "data_thresholds": data_check,
            "scheduled_ready": scheduled_check
        }

    def on_consolidation_complete(self, job_id: int) -> Dict[str, Any]:
        """
        Hook called after consolidation job completes.

        Args:
            job_id: Consolidation job ID

        Returns:
            Action to take (if any)
        """
        logger.info(f"PySR hook: Consolidation job {job_id} completed")

        # Check if we should trigger discovery
        trigger_check = self.should_trigger_discovery()

        if trigger_check["should_trigger"]:
            logger.info(f"Triggering PySR discovery: {', '.join(trigger_check['reasons'])}")
            return {
                "action": "trigger_discovery",
                "reasons": trigger_check["reasons"],
                "timestamp": datetime.now().isoformat()
            }

        return {"action": "none"}

    def on_memory_created(self, memory_id: str) -> Dict[str, Any]:
        """
        Hook called after new memory is created.

        Args:
            memory_id: Memory entity ID

        Returns:
            Action to take (if any)
        """
        # Check periodically (every 100 memories)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM entities")
        total_count = cursor.fetchone()[0]
        conn.close()

        if total_count % 100 == 0:  # Check every 100 memories
            trigger_check = self.should_trigger_discovery()

            if trigger_check["should_trigger"]:
                logger.info(f"Memory milestone reached: {total_count} memories")
                return {
                    "action": "trigger_discovery",
                    "reasons": trigger_check["reasons"] + [f"Memory milestone: {total_count}"],
                    "timestamp": datetime.now().isoformat()
                }

        return {"action": "none"}

    def on_discovery_complete(self, results: Dict[str, Any]):
        """
        Hook called after PySR discovery completes.

        Updates state to track discovery history.

        Args:
            results: Discovery results
        """
        logger.info("PySR discovery completed, updating state")

        # Update state
        self.state["last_discovery"] = datetime.now().isoformat()
        self.state["discovery_count"] = self.state.get("discovery_count", 0) + 1

        # Update sample counts
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM entities WHERE importance_score IS NOT NULL")
        self.state["last_importance_samples"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM consolidation_jobs WHERE status = 'completed'")
        self.state["last_consolidation_samples"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM entities WHERE access_count > 0")
        self.state["last_access_samples"] = cursor.fetchone()[0]

        conn.close()

        # Store results summary
        if "discovery_history" not in self.state:
            self.state["discovery_history"] = []

        self.state["discovery_history"].append({
            "timestamp": datetime.now().isoformat(),
            "importance_r2": results.get("importance", {}).get("r2_score"),
            "consolidation_r2": results.get("consolidation", {}).get("r2_score"),
            "access_pattern_r2": results.get("access_pattern", {}).get("r2_score")
        })

        # Keep only last 10 discoveries
        if len(self.state["discovery_history"]) > 10:
            self.state["discovery_history"] = self.state["discovery_history"][-10:]

        self._save_state()

    def get_discovery_stats(self) -> Dict[str, Any]:
        """
        Get statistics about discovery history.

        Returns:
            Dict with discovery statistics
        """
        return {
            "total_discoveries": self.state.get("discovery_count", 0),
            "last_discovery": self.state.get("last_discovery"),
            "history": self.state.get("discovery_history", []),
            "next_scheduled": self._calculate_next_scheduled(),
            "current_thresholds": self.check_data_thresholds()
        }

    def _calculate_next_scheduled(self) -> Optional[str]:
        """Calculate when next scheduled discovery will trigger."""
        last_discovery = self.state.get("last_discovery")

        if not last_discovery:
            return "Now (never run before)"

        try:
            last_time = datetime.fromisoformat(last_discovery)
            next_time = last_time + timedelta(hours=self.thresholds["discovery_interval_hours"])

            if next_time < datetime.now():
                return "Now (overdue)"

            return next_time.isoformat()
        except:
            return None

    def configure_thresholds(
        self,
        importance_min: Optional[int] = None,
        consolidation_min: Optional[int] = None,
        access_min: Optional[int] = None,
        interval_hours: Optional[int] = None
    ):
        """
        Configure discovery trigger thresholds.

        Args:
            importance_min: Minimum samples for importance discovery
            consolidation_min: Minimum samples for consolidation discovery
            access_min: Minimum samples for access pattern discovery
            interval_hours: Hours between scheduled discoveries
        """
        if importance_min is not None:
            self.thresholds["importance_min_samples"] = importance_min
        if consolidation_min is not None:
            self.thresholds["consolidation_min_samples"] = consolidation_min
        if access_min is not None:
            self.thresholds["access_pattern_min_samples"] = access_min
        if interval_hours is not None:
            self.thresholds["discovery_interval_hours"] = interval_hours

        logger.info(f"Updated PySR hooks thresholds: {self.thresholds}")


# Singleton instance
_hooks_manager: Optional[PySRHooksManager] = None


def get_hooks_manager() -> PySRHooksManager:
    """Get or create singleton PySRHooksManager."""
    global _hooks_manager
    if _hooks_manager is None:
        _hooks_manager = PySRHooksManager()
    return _hooks_manager


# Convenience hook functions
def on_consolidation_complete(job_id: int) -> Dict[str, Any]:
    """Consolidation completion hook."""
    return get_hooks_manager().on_consolidation_complete(job_id)


def on_memory_created(memory_id: str) -> Dict[str, Any]:
    """Memory creation hook."""
    return get_hooks_manager().on_memory_created(memory_id)


def on_discovery_complete(results: Dict[str, Any]):
    """Discovery completion hook."""
    return get_hooks_manager().on_discovery_complete(results)


def should_trigger_discovery() -> Dict[str, Any]:
    """Check if discovery should be triggered."""
    return get_hooks_manager().should_trigger_discovery()


def get_discovery_stats() -> Dict[str, Any]:
    """Get discovery statistics."""
    return get_hooks_manager().get_discovery_stats()
