#!/usr/bin/env python3
"""
Pattern Weight Manager - God Agent Phase 4.2 (Sona-Style Learning)

Implements adaptive pattern weight adjustment based on trajectory outcomes:
1. Learning rate-based weight updates
2. EWC++ style forgetting prevention
3. Drift detection and auto-rollback
4. Task-relevance weighted rewards

Based on God Agent white paper Section 10.5: Sona Learning Engine
"""

import asyncio
import copy
import hashlib
import json
import logging
import math
import sqlite3
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import platform

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pattern-weight-manager")


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    system = platform.system()
    if system == "Darwin":
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


STORAGE_BASE = _get_storage_base()
DEFAULT_DB_PATH = STORAGE_BASE / "databases" / "learning" / "pattern_weights.db"


class DriftSeverity(Enum):
    """Severity of weight drift from baseline."""
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PatternWeight:
    """
    Weight information for a pattern.

    Tracks the pattern's effectiveness and learning history.
    """
    pattern_id: str
    pattern_type: str  # "action_sequence", "strategy", "tool_combo"
    description: str

    # Current weight (0.0 - 1.0)
    weight: float = 0.5

    # Baseline for drift detection
    baseline_weight: float = 0.5

    # Learning statistics
    usage_count: int = 0
    success_count: int = 0
    total_reward: float = 0.0
    average_quality: float = 0.5

    # EWC++ parameters
    fisher_information: float = 0.0  # Importance measure
    ewc_protected: bool = False  # Whether to protect from large updates

    # History
    weight_history: List[Tuple[datetime, float]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    # Context
    goal_types: Set[str] = field(default_factory=set)  # Goal types this pattern applies to
    tags: Set[str] = field(default_factory=set)

    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.usage_count == 0:
            return 0.5
        return self.success_count / self.usage_count

    def get_drift(self) -> float:
        """Calculate drift from baseline."""
        return abs(self.weight - self.baseline_weight)

    def get_drift_severity(self) -> DriftSeverity:
        """Determine drift severity."""
        drift = self.get_drift()
        if drift < 0.05:
            return DriftSeverity.NONE
        elif drift < 0.15:
            return DriftSeverity.LOW
        elif drift < 0.30:
            return DriftSeverity.MODERATE
        elif drift < 0.50:
            return DriftSeverity.HIGH
        else:
            return DriftSeverity.CRITICAL

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "weight": self.weight,
            "baseline_weight": self.baseline_weight,
            "usage_count": self.usage_count,
            "success_count": self.success_count,
            "success_rate": self.get_success_rate(),
            "total_reward": self.total_reward,
            "average_quality": self.average_quality,
            "fisher_information": self.fisher_information,
            "ewc_protected": self.ewc_protected,
            "drift": self.get_drift(),
            "drift_severity": self.get_drift_severity().value,
            "goal_types": list(self.goal_types),
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class WeightUpdate:
    """Record of a weight update."""
    update_id: str
    pattern_id: str
    old_weight: float
    new_weight: float
    delta: float
    reward: float
    quality: float
    similarity: float
    task_relevance: float
    trajectory_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    rolled_back: bool = False


@dataclass
class DriftAlert:
    """Alert for weight drift."""
    alert_id: str
    pattern_id: str
    severity: DriftSeverity
    current_weight: float
    baseline_weight: float
    drift_amount: float
    recommendation: str
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False


class PatternWeightManager:
    """
    Sona-Style Pattern Weight Manager.

    Implements:
    - Gradient-based weight updates from trajectory feedback
    - EWC++ catastrophic forgetting prevention
    - Drift detection with configurable thresholds
    - Auto-rollback for critical drift
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        learning_rate: float = 0.01,
        baseline_quality: float = 0.5,
        drift_threshold: float = 0.30,
        ewc_lambda: float = 0.4,
        auto_rollback_threshold: float = 0.50
    ):
        """
        Initialize the pattern weight manager.

        Args:
            db_path: Path to database
            learning_rate: Learning rate for weight updates (default 0.01)
            baseline_quality: Baseline quality expectation (default 0.5)
            drift_threshold: Threshold for drift alerts (default 0.30)
            ewc_lambda: EWC regularization strength (default 0.4)
            auto_rollback_threshold: Auto-rollback if drift exceeds (default 0.50)
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Hyperparameters
        self.learning_rate = learning_rate
        self.baseline_quality = baseline_quality
        self.drift_threshold = drift_threshold
        self.ewc_lambda = ewc_lambda
        self.auto_rollback_threshold = auto_rollback_threshold

        # In-memory weight cache
        self.weights: Dict[str, PatternWeight] = {}

        # Pending alerts
        self.alerts: List[DriftAlert] = []

        # Initialize database
        self._init_database()

        # Load weights from database
        self._load_weights()

        logger.info(f"PatternWeightManager initialized (lr={learning_rate}, ewc_λ={ewc_lambda})")

    def _init_database(self) -> None:
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Pattern weights table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_weights (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT NOT NULL,
                description TEXT,
                weight REAL DEFAULT 0.5,
                baseline_weight REAL DEFAULT 0.5,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                total_reward REAL DEFAULT 0.0,
                average_quality REAL DEFAULT 0.5,
                fisher_information REAL DEFAULT 0.0,
                ewc_protected INTEGER DEFAULT 0,
                goal_types TEXT,
                tags TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Weight update history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weight_updates (
                update_id TEXT PRIMARY KEY,
                pattern_id TEXT NOT NULL,
                old_weight REAL,
                new_weight REAL,
                delta REAL,
                reward REAL,
                quality REAL,
                similarity REAL,
                task_relevance REAL,
                trajectory_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                rolled_back INTEGER DEFAULT 0,
                FOREIGN KEY (pattern_id) REFERENCES pattern_weights(pattern_id)
            )
        ''')

        # Drift alerts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS drift_alerts (
                alert_id TEXT PRIMARY KEY,
                pattern_id TEXT NOT NULL,
                severity TEXT,
                current_weight REAL,
                baseline_weight REAL,
                drift_amount REAL,
                recommendation TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged INTEGER DEFAULT 0,
                FOREIGN KEY (pattern_id) REFERENCES pattern_weights(pattern_id)
            )
        ''')

        # Weight snapshots for rollback
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weight_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                pattern_id TEXT NOT NULL,
                weight REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reason TEXT,
                FOREIGN KEY (pattern_id) REFERENCES pattern_weights(pattern_id)
            )
        ''')

        # Indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_weights_type ON pattern_weights(pattern_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_updates_pattern ON weight_updates(pattern_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_updates_time ON weight_updates(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_pattern ON drift_alerts(pattern_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_severity ON drift_alerts(severity)')

        conn.commit()
        conn.close()

    def _load_weights(self) -> None:
        """Load weights from database into memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT pattern_id, pattern_type, description, weight, baseline_weight,
                       usage_count, success_count, total_reward, average_quality,
                       fisher_information, ewc_protected, goal_types, tags,
                       created_at, last_updated
                FROM pattern_weights
            ''')

            for row in cursor.fetchall():
                pattern = PatternWeight(
                    pattern_id=row[0],
                    pattern_type=row[1],
                    description=row[2] or "",
                    weight=row[3],
                    baseline_weight=row[4],
                    usage_count=row[5],
                    success_count=row[6],
                    total_reward=row[7],
                    average_quality=row[8],
                    fisher_information=row[9],
                    ewc_protected=bool(row[10]),
                    goal_types=set(json.loads(row[11])) if row[11] else set(),
                    tags=set(json.loads(row[12])) if row[12] else set(),
                    created_at=datetime.fromisoformat(row[13]) if row[13] else datetime.now(),
                    last_updated=datetime.fromisoformat(row[14]) if row[14] else datetime.now()
                )
                self.weights[pattern.pattern_id] = pattern

            logger.info(f"Loaded {len(self.weights)} pattern weights from database")

        except Exception as e:
            logger.error(f"Failed to load weights: {e}")
        finally:
            conn.close()

    # ==================== Core Weight Operations ====================

    def get_or_create_pattern(
        self,
        pattern_id: str,
        pattern_type: str = "action_sequence",
        description: str = "",
        goal_types: Optional[Set[str]] = None,
        tags: Optional[Set[str]] = None
    ) -> PatternWeight:
        """
        Get existing pattern weight or create new one.

        Args:
            pattern_id: Unique pattern identifier
            pattern_type: Type of pattern
            description: Human-readable description
            goal_types: Applicable goal types
            tags: Categorization tags

        Returns:
            PatternWeight object
        """
        if pattern_id in self.weights:
            return self.weights[pattern_id]

        # Create new pattern
        pattern = PatternWeight(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            description=description,
            goal_types=goal_types or set(),
            tags=tags or set()
        )

        self.weights[pattern_id] = pattern
        self._save_pattern(pattern)

        logger.info(f"Created new pattern weight: {pattern_id}")
        return pattern

    def update_weight(
        self,
        pattern_id: str,
        quality: float,
        similarity: float,
        task_relevance: float = 1.0,
        trajectory_id: str = ""
    ) -> Tuple[float, float, Optional[DriftAlert]]:
        """
        Update pattern weight based on trajectory outcome.

        Sona-style update:
            reward = quality × similarity × task_relevance
            delta = learning_rate × (reward - baseline) × activation
            new_weight = old_weight + delta (with EWC++ regularization)

        Args:
            pattern_id: Pattern to update
            quality: Quality score from trajectory (0.0 - 1.0)
            similarity: How well pattern matched the task (0.0 - 1.0)
            task_relevance: Relevance to current task type (0.0 - 1.0)
            trajectory_id: Associated trajectory for tracking

        Returns:
            Tuple of (new_weight, delta, optional_drift_alert)
        """
        if pattern_id not in self.weights:
            pattern = self.get_or_create_pattern(pattern_id)
        else:
            pattern = self.weights[pattern_id]

        old_weight = pattern.weight

        # Calculate reward
        reward = quality * similarity * task_relevance

        # Calculate delta with learning rate
        activation = similarity  # How strongly pattern was activated
        delta = self.learning_rate * (reward - self.baseline_quality) * activation

        # Apply EWC++ regularization if protected
        if pattern.ewc_protected and pattern.fisher_information > 0:
            # Reduce delta based on Fisher information
            ewc_penalty = self.ewc_lambda * pattern.fisher_information * delta
            delta = delta - ewc_penalty
            logger.debug(f"EWC penalty applied to {pattern_id}: {ewc_penalty:.4f}")

        # Calculate new weight (bounded 0.1 - 0.9 to prevent extreme values)
        new_weight = max(0.1, min(0.9, old_weight + delta))

        # Update pattern
        pattern.weight = new_weight
        pattern.usage_count += 1
        if quality >= 0.6:
            pattern.success_count += 1
        pattern.total_reward += reward
        pattern.average_quality = (
            (pattern.average_quality * (pattern.usage_count - 1) + quality)
            / pattern.usage_count
        )
        pattern.last_updated = datetime.now()
        pattern.weight_history.append((datetime.now(), new_weight))

        # Check for drift
        drift_alert = self._check_drift(pattern)

        # Auto-rollback if critical drift
        if drift_alert and drift_alert.severity == DriftSeverity.CRITICAL:
            if self.auto_rollback_threshold > 0:
                logger.warning(f"Auto-rollback triggered for {pattern_id}")
                self._rollback_weight(pattern_id, "auto_rollback_critical_drift")
                new_weight = pattern.weight
                delta = new_weight - old_weight

        # Record update
        self._record_update(WeightUpdate(
            update_id=f"upd_{pattern_id}_{int(datetime.now().timestamp())}",
            pattern_id=pattern_id,
            old_weight=old_weight,
            new_weight=new_weight,
            delta=delta,
            reward=reward,
            quality=quality,
            similarity=similarity,
            task_relevance=task_relevance,
            trajectory_id=trajectory_id
        ))

        # Save to database
        self._save_pattern(pattern)

        logger.debug(f"Updated {pattern_id}: {old_weight:.3f} -> {new_weight:.3f} (Δ={delta:+.4f})")

        return new_weight, delta, drift_alert

    def get_adjusted_score(
        self,
        pattern_id: str,
        base_similarity: float
    ) -> float:
        """
        Get weight-adjusted score for pattern ranking.

        Used to re-rank patterns by learned effectiveness.

        Args:
            pattern_id: Pattern identifier
            base_similarity: Original similarity score

        Returns:
            Adjusted score (similarity × weight)
        """
        if pattern_id not in self.weights:
            return base_similarity * 0.5  # Default weight

        pattern = self.weights[pattern_id]
        return base_similarity * pattern.weight

    def get_adjusted_scores(
        self,
        patterns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Re-rank a list of patterns by learned weights.

        Args:
            patterns: List of {pattern_id, similarity, ...} dicts

        Returns:
            Patterns sorted by adjusted score
        """
        for p in patterns:
            pattern_id = p.get("pattern_id", "")
            similarity = p.get("similarity", 0.5)
            p["adjusted_score"] = self.get_adjusted_score(pattern_id, similarity)

        return sorted(patterns, key=lambda x: x["adjusted_score"], reverse=True)

    # ==================== EWC++ Forgetting Prevention ====================

    def compute_fisher_information(
        self,
        pattern_id: str,
        recent_updates: int = 10
    ) -> float:
        """
        Compute Fisher Information for a pattern.

        Higher values indicate the pattern is important and should resist change.
        Based on gradient variance from recent updates.

        Args:
            pattern_id: Pattern to compute for
            recent_updates: Number of recent updates to consider

        Returns:
            Fisher Information estimate
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT delta, reward FROM weight_updates
                WHERE pattern_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (pattern_id, recent_updates))

            rows = cursor.fetchall()
            if len(rows) < 3:  # Need minimum samples
                return 0.0

            deltas = [row[0] for row in rows]

            # Fisher Information = variance of gradients (squared deltas)
            squared_deltas = [d * d for d in deltas]
            fisher = statistics.mean(squared_deltas)

            # Update pattern
            if pattern_id in self.weights:
                self.weights[pattern_id].fisher_information = fisher
                self._save_pattern(self.weights[pattern_id])

            return fisher

        except Exception as e:
            logger.error(f"Failed to compute Fisher Information: {e}")
            return 0.0
        finally:
            conn.close()

    def protect_pattern(self, pattern_id: str) -> bool:
        """
        Enable EWC++ protection for a pattern.

        Protected patterns resist large weight changes.

        Args:
            pattern_id: Pattern to protect

        Returns:
            Success status
        """
        if pattern_id not in self.weights:
            return False

        pattern = self.weights[pattern_id]

        # Compute Fisher Information
        fisher = self.compute_fisher_information(pattern_id)

        pattern.ewc_protected = True
        pattern.fisher_information = fisher
        self._save_pattern(pattern)

        logger.info(f"Protected pattern {pattern_id} with Fisher={fisher:.4f}")
        return True

    def unprotect_pattern(self, pattern_id: str) -> bool:
        """Disable EWC++ protection for a pattern."""
        if pattern_id not in self.weights:
            return False

        pattern = self.weights[pattern_id]
        pattern.ewc_protected = False
        self._save_pattern(pattern)

        logger.info(f"Unprotected pattern {pattern_id}")
        return True

    # ==================== Drift Detection ====================

    def _check_drift(self, pattern: PatternWeight) -> Optional[DriftAlert]:
        """
        Check if pattern has drifted significantly from baseline.

        Args:
            pattern: Pattern to check

        Returns:
            DriftAlert if drift exceeds threshold, None otherwise
        """
        drift = pattern.get_drift()
        severity = pattern.get_drift_severity()

        if severity == DriftSeverity.NONE:
            return None

        # Only alert for moderate+ drift
        if severity in [DriftSeverity.MODERATE, DriftSeverity.HIGH, DriftSeverity.CRITICAL]:
            # Generate recommendation
            if pattern.weight > pattern.baseline_weight:
                direction = "increased"
                recommendation = "Pattern performing better than baseline. Consider updating baseline."
            else:
                direction = "decreased"
                recommendation = "Pattern performing worse. Investigate or rollback."

            if severity == DriftSeverity.CRITICAL:
                recommendation = f"CRITICAL: Weight {direction} {drift:.1%}. Auto-rollback recommended."

            alert = DriftAlert(
                alert_id=f"drift_{pattern.pattern_id}_{int(datetime.now().timestamp())}",
                pattern_id=pattern.pattern_id,
                severity=severity,
                current_weight=pattern.weight,
                baseline_weight=pattern.baseline_weight,
                drift_amount=drift,
                recommendation=recommendation
            )

            # Store alert
            self._save_alert(alert)
            self.alerts.append(alert)

            logger.warning(f"Drift alert: {pattern.pattern_id} ({severity.value}): {drift:.1%}")

            return alert

        return None

    def get_pending_alerts(
        self,
        severity: Optional[DriftSeverity] = None,
        acknowledged: bool = False
    ) -> List[DriftAlert]:
        """Get pending drift alerts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            query = '''
                SELECT alert_id, pattern_id, severity, current_weight, baseline_weight,
                       drift_amount, recommendation, timestamp, acknowledged
                FROM drift_alerts
                WHERE acknowledged = ?
            '''
            params = [1 if acknowledged else 0]

            if severity:
                query += ' AND severity = ?'
                params.append(severity.value)

            query += ' ORDER BY timestamp DESC'

            cursor.execute(query, params)

            alerts = []
            for row in cursor.fetchall():
                alerts.append(DriftAlert(
                    alert_id=row[0],
                    pattern_id=row[1],
                    severity=DriftSeverity(row[2]),
                    current_weight=row[3],
                    baseline_weight=row[4],
                    drift_amount=row[5],
                    recommendation=row[6],
                    timestamp=datetime.fromisoformat(row[7]) if row[7] else datetime.now(),
                    acknowledged=bool(row[8])
                ))

            return alerts

        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return []
        finally:
            conn.close()

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a drift alert."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE drift_alerts SET acknowledged = 1 WHERE alert_id = ?
            ''', (alert_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            return False
        finally:
            conn.close()

    # ==================== Rollback Operations ====================

    def create_snapshot(self, pattern_id: str, reason: str = "manual") -> str:
        """Create a weight snapshot for potential rollback."""
        if pattern_id not in self.weights:
            return ""

        pattern = self.weights[pattern_id]
        snapshot_id = f"snap_{pattern_id}_{int(datetime.now().timestamp())}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO weight_snapshots (snapshot_id, pattern_id, weight, reason)
                VALUES (?, ?, ?, ?)
            ''', (snapshot_id, pattern_id, pattern.weight, reason))
            conn.commit()

            logger.info(f"Created snapshot {snapshot_id} for {pattern_id}")
            return snapshot_id

        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            return ""
        finally:
            conn.close()

    def _rollback_weight(self, pattern_id: str, reason: str = "manual") -> bool:
        """
        Rollback pattern weight to baseline.

        Args:
            pattern_id: Pattern to rollback
            reason: Reason for rollback

        Returns:
            Success status
        """
        if pattern_id not in self.weights:
            return False

        pattern = self.weights[pattern_id]

        # Create snapshot before rollback
        self.create_snapshot(pattern_id, f"pre_rollback_{reason}")

        # Rollback to baseline
        old_weight = pattern.weight
        pattern.weight = pattern.baseline_weight
        pattern.last_updated = datetime.now()

        self._save_pattern(pattern)

        # Mark recent updates as rolled back
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE weight_updates SET rolled_back = 1
                WHERE pattern_id = ? AND rolled_back = 0
            ''', (pattern_id,))
            conn.commit()
        finally:
            conn.close()

        logger.info(f"Rolled back {pattern_id}: {old_weight:.3f} -> {pattern.baseline_weight:.3f}")
        return True

    def rollback_to_snapshot(self, snapshot_id: str) -> bool:
        """Rollback pattern to a specific snapshot."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT pattern_id, weight FROM weight_snapshots WHERE snapshot_id = ?
            ''', (snapshot_id,))

            row = cursor.fetchone()
            if not row:
                return False

            pattern_id, snapshot_weight = row

            if pattern_id not in self.weights:
                return False

            pattern = self.weights[pattern_id]
            pattern.weight = snapshot_weight
            pattern.last_updated = datetime.now()

            self._save_pattern(pattern)

            logger.info(f"Rolled back {pattern_id} to snapshot {snapshot_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback to snapshot: {e}")
            return False
        finally:
            conn.close()

    def update_baseline(self, pattern_id: str) -> bool:
        """
        Update baseline to current weight.

        Call this when current weight represents acceptable performance.
        """
        if pattern_id not in self.weights:
            return False

        pattern = self.weights[pattern_id]
        pattern.baseline_weight = pattern.weight
        self._save_pattern(pattern)

        logger.info(f"Updated baseline for {pattern_id} to {pattern.weight:.3f}")
        return True

    # ==================== Statistics & Queries ====================

    def get_pattern(self, pattern_id: str) -> Optional[Dict[str, Any]]:
        """Get pattern details."""
        if pattern_id not in self.weights:
            return None
        return self.weights[pattern_id].to_dict()

    def list_patterns(
        self,
        pattern_type: Optional[str] = None,
        goal_type: Optional[str] = None,
        min_weight: float = 0.0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List patterns with optional filters."""
        patterns = []

        for pattern in self.weights.values():
            # Apply filters
            if pattern_type and pattern.pattern_type != pattern_type:
                continue
            if goal_type and goal_type not in pattern.goal_types:
                continue
            if pattern.weight < min_weight:
                continue

            patterns.append(pattern.to_dict())

        # Sort by weight descending
        patterns.sort(key=lambda p: p["weight"], reverse=True)

        return patterns[:limit]

    def get_top_patterns(
        self,
        goal_type: str = "",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top-performing patterns for a goal type."""
        return self.list_patterns(
            goal_type=goal_type if goal_type else None,
            min_weight=0.5,
            limit=limit
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall statistics."""
        total_patterns = len(self.weights)
        if total_patterns == 0:
            return {
                "total_patterns": 0,
                "average_weight": 0.5,
                "protected_patterns": 0,
                "drifted_patterns": 0,
                "pending_alerts": 0
            }

        weights = [p.weight for p in self.weights.values()]
        protected = sum(1 for p in self.weights.values() if p.ewc_protected)
        drifted = sum(1 for p in self.weights.values()
                      if p.get_drift_severity() in [DriftSeverity.MODERATE, DriftSeverity.HIGH, DriftSeverity.CRITICAL])

        return {
            "total_patterns": total_patterns,
            "average_weight": statistics.mean(weights),
            "weight_stddev": statistics.stdev(weights) if total_patterns > 1 else 0,
            "min_weight": min(weights),
            "max_weight": max(weights),
            "protected_patterns": protected,
            "drifted_patterns": drifted,
            "pending_alerts": len(self.get_pending_alerts()),
            "learning_rate": self.learning_rate,
            "ewc_lambda": self.ewc_lambda
        }

    # ==================== Database Operations ====================

    def _save_pattern(self, pattern: PatternWeight) -> None:
        """Save pattern to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO pattern_weights (
                    pattern_id, pattern_type, description, weight, baseline_weight,
                    usage_count, success_count, total_reward, average_quality,
                    fisher_information, ewc_protected, goal_types, tags,
                    created_at, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                pattern.pattern_id,
                pattern.pattern_type,
                pattern.description,
                pattern.weight,
                pattern.baseline_weight,
                pattern.usage_count,
                pattern.success_count,
                pattern.total_reward,
                pattern.average_quality,
                pattern.fisher_information,
                1 if pattern.ewc_protected else 0,
                json.dumps(list(pattern.goal_types)),
                json.dumps(list(pattern.tags)),
                pattern.created_at.isoformat(),
                pattern.last_updated.isoformat()
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save pattern: {e}")
        finally:
            conn.close()

    def _record_update(self, update: WeightUpdate) -> None:
        """Record a weight update."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO weight_updates (
                    update_id, pattern_id, old_weight, new_weight, delta,
                    reward, quality, similarity, task_relevance, trajectory_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                update.update_id,
                update.pattern_id,
                update.old_weight,
                update.new_weight,
                update.delta,
                update.reward,
                update.quality,
                update.similarity,
                update.task_relevance,
                update.trajectory_id
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to record update: {e}")
        finally:
            conn.close()

    def _save_alert(self, alert: DriftAlert) -> None:
        """Save drift alert."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO drift_alerts (
                    alert_id, pattern_id, severity, current_weight, baseline_weight,
                    drift_amount, recommendation, acknowledged
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', (
                alert.alert_id,
                alert.pattern_id,
                alert.severity.value,
                alert.current_weight,
                alert.baseline_weight,
                alert.drift_amount,
                alert.recommendation
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save alert: {e}")
        finally:
            conn.close()


# ==================== MCP Tool Registration ====================

def register_pattern_weight_tools(app, db_path: Optional[Path] = None):
    """
    Register pattern weight management tools with MCP app.

    Args:
        app: FastMCP app instance
        db_path: Path to database
    """
    manager = PatternWeightManager(db_path)

    @app.tool()
    async def update_pattern_weight(
        pattern_id: str,
        quality: float,
        similarity: float,
        task_relevance: float = 1.0,
        trajectory_id: str = "",
        pattern_type: str = "action_sequence",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Update pattern weight based on outcome feedback.

        Sona-style learning: reward = quality × similarity × task_relevance.
        Weight is adjusted based on how much reward exceeds baseline.

        Args:
            pattern_id: Pattern identifier
            quality: Quality score (0.0-1.0)
            similarity: How well pattern matched task (0.0-1.0)
            task_relevance: Task relevance (0.0-1.0)
            trajectory_id: Associated trajectory
            pattern_type: Type if creating new pattern
            description: Description if creating new pattern

        Returns:
            Update result with new weight and any alerts
        """
        # Ensure pattern exists
        manager.get_or_create_pattern(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            description=description
        )

        new_weight, delta, alert = manager.update_weight(
            pattern_id=pattern_id,
            quality=quality,
            similarity=similarity,
            task_relevance=task_relevance,
            trajectory_id=trajectory_id
        )

        result = {
            "pattern_id": pattern_id,
            "new_weight": new_weight,
            "delta": delta,
            "reward": quality * similarity * task_relevance
        }

        if alert:
            result["alert"] = {
                "severity": alert.severity.value,
                "drift": alert.drift_amount,
                "recommendation": alert.recommendation
            }

        return result

    @app.tool()
    async def get_pattern_weight(pattern_id: str) -> Dict[str, Any]:
        """
        Get current weight and statistics for a pattern.

        Args:
            pattern_id: Pattern identifier

        Returns:
            Pattern details including weight, success rate, drift status
        """
        pattern = manager.get_pattern(pattern_id)
        if not pattern:
            return {"error": f"Pattern {pattern_id} not found"}
        return pattern

    @app.tool()
    async def get_adjusted_pattern_scores(
        patterns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Re-rank patterns by learned effectiveness.

        Takes a list of patterns with similarity scores and returns
        them sorted by weight-adjusted scores.

        Args:
            patterns: List of {pattern_id, similarity, ...} dicts

        Returns:
            Patterns sorted by adjusted score
        """
        adjusted = manager.get_adjusted_scores(patterns)
        return {
            "count": len(adjusted),
            "patterns": adjusted
        }

    @app.tool()
    async def protect_pattern_from_forgetting(pattern_id: str) -> Dict[str, Any]:
        """
        Enable EWC++ protection for a well-performing pattern.

        Protected patterns resist large weight changes, preventing
        catastrophic forgetting of learned behaviors.

        Args:
            pattern_id: Pattern to protect

        Returns:
            Confirmation with Fisher Information score
        """
        if pattern_id not in manager.weights:
            return {"error": f"Pattern {pattern_id} not found"}

        success = manager.protect_pattern(pattern_id)
        if success:
            pattern = manager.weights[pattern_id]
            return {
                "pattern_id": pattern_id,
                "protected": True,
                "fisher_information": pattern.fisher_information,
                "message": "Pattern is now protected from large weight changes"
            }
        return {"error": "Failed to protect pattern"}

    @app.tool()
    async def get_drift_alerts(
        severity: Optional[str] = None,
        include_acknowledged: bool = False
    ) -> Dict[str, Any]:
        """
        Get drift alerts for patterns that have diverged from baseline.

        Args:
            severity: Filter by severity (low, moderate, high, critical)
            include_acknowledged: Include already acknowledged alerts

        Returns:
            List of drift alerts
        """
        sev = DriftSeverity(severity) if severity else None
        alerts = manager.get_pending_alerts(severity=sev, acknowledged=include_acknowledged)

        return {
            "count": len(alerts),
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "pattern_id": a.pattern_id,
                    "severity": a.severity.value,
                    "drift": a.drift_amount,
                    "current_weight": a.current_weight,
                    "baseline_weight": a.baseline_weight,
                    "recommendation": a.recommendation,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in alerts
            ]
        }

    @app.tool()
    async def rollback_pattern_weight(
        pattern_id: str,
        reason: str = "manual_rollback"
    ) -> Dict[str, Any]:
        """
        Rollback pattern weight to baseline.

        Use this when a pattern has drifted too far or is performing poorly.

        Args:
            pattern_id: Pattern to rollback
            reason: Reason for rollback

        Returns:
            Confirmation with old and new weights
        """
        if pattern_id not in manager.weights:
            return {"error": f"Pattern {pattern_id} not found"}

        old_weight = manager.weights[pattern_id].weight
        success = manager._rollback_weight(pattern_id, reason)

        if success:
            new_weight = manager.weights[pattern_id].weight
            return {
                "pattern_id": pattern_id,
                "old_weight": old_weight,
                "new_weight": new_weight,
                "rolled_back": True,
                "reason": reason
            }
        return {"error": "Rollback failed"}

    @app.tool()
    async def get_pattern_weight_statistics() -> Dict[str, Any]:
        """
        Get overall statistics for the pattern weight system.

        Returns:
            Statistics including averages, protected count, alerts
        """
        return manager.get_statistics()

    @app.tool()
    async def list_top_patterns(
        goal_type: str = "",
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get top-performing patterns for a goal type.

        Args:
            goal_type: Filter by goal type (empty for all)
            limit: Maximum results

        Returns:
            Top patterns sorted by weight
        """
        patterns = manager.get_top_patterns(goal_type=goal_type, limit=limit)
        return {
            "goal_type": goal_type or "all",
            "count": len(patterns),
            "patterns": patterns
        }

    logger.info("Registered 8 pattern weight management tools (God Agent Phase 4.2)")
    return manager


# ==================== Standalone Testing ====================

if __name__ == "__main__":
    print("=" * 60)
    print("Pattern Weight Manager - God Agent Phase 4.2 (Sona-Style)")
    print("=" * 60)

    # Create manager
    manager = PatternWeightManager(learning_rate=0.05)  # Higher LR for testing

    # Create some patterns
    print("\n1. Creating patterns...")
    patterns = [
        ("pattern_read_edit_test", "action_sequence", "Read -> Edit -> Test workflow"),
        ("pattern_search_implement", "action_sequence", "Search -> Implement workflow"),
        ("pattern_analyze_fix", "strategy", "Analyze -> Fix strategy"),
    ]

    for pid, ptype, desc in patterns:
        manager.get_or_create_pattern(pid, ptype, desc, goal_types={"coding"})
        print(f"   Created: {pid}")

    # Simulate trajectory outcomes
    print("\n2. Simulating trajectory outcomes...")

    # Good outcomes for pattern 1
    for i in range(5):
        quality = 0.7 + (i * 0.05)  # Improving quality
        new_w, delta, alert = manager.update_weight(
            "pattern_read_edit_test",
            quality=quality,
            similarity=0.9,
            task_relevance=1.0,
            trajectory_id=f"traj_{i}"
        )
        print(f"   Update {i+1}: quality={quality:.2f}, weight={new_w:.3f}, Δ={delta:+.4f}")

    # Mixed outcomes for pattern 2
    print("\n3. Mixed outcomes for pattern_search_implement...")
    for i, q in enumerate([0.8, 0.4, 0.6, 0.3, 0.7]):
        new_w, delta, alert = manager.update_weight(
            "pattern_search_implement",
            quality=q,
            similarity=0.8,
            trajectory_id=f"traj_mix_{i}"
        )
        print(f"   Update {i+1}: quality={q:.2f}, weight={new_w:.3f}, Δ={delta:+.4f}")

    # Protect pattern 1 (it's performing well)
    print("\n4. Protecting pattern_read_edit_test...")
    manager.protect_pattern("pattern_read_edit_test")
    print(f"   Fisher Information: {manager.weights['pattern_read_edit_test'].fisher_information:.4f}")

    # Check drift
    print("\n5. Checking for drift alerts...")
    alerts = manager.get_pending_alerts()
    print(f"   Found {len(alerts)} alerts")
    for alert in alerts:
        print(f"   - {alert.pattern_id}: {alert.severity.value} ({alert.drift_amount:.1%})")

    # Get top patterns
    print("\n6. Top patterns for coding:")
    top = manager.get_top_patterns(goal_type="coding", limit=5)
    for p in top:
        print(f"   {p['pattern_id']}: weight={p['weight']:.3f}, success_rate={p['success_rate']:.1%}")

    # Get statistics
    print("\n7. System Statistics:")
    stats = manager.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.3f}")
        else:
            print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("Pattern Weight Manager - Tests Complete")
    print("=" * 60)
