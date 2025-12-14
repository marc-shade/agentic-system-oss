#!/usr/bin/env python3
"""
Trajectory Recording System - God Agent Phase 4.1

Records complete decision trajectories from AI agents for:
1. Learning from successful patterns
2. Trajectory embedding and similarity search
3. Pattern weight adjustment (Sona-style feedback)
4. Retrospective analysis and improvement

Based on God Agent white paper Section 10.4: Trajectory-Based Learning
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import platform

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("trajectory-recorder")


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
DEFAULT_DB_PATH = STORAGE_BASE / "databases" / "trajectory" / "trajectories.db"


class TrajectoryStatus(Enum):
    """Status of a trajectory."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class StepOutcome(Enum):
    """Outcome of a trajectory step."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass
class TrajectoryStep:
    """
    Single step in an agent's decision trajectory.

    Captures the ReAct pattern: Thought -> Action -> Observation
    """
    step_id: str
    step_number: int

    # ReAct components
    thought: str              # Agent's reasoning before action
    action: str               # Tool/action taken (e.g., "Read", "Edit", "WebSearch")
    action_input: Dict[str, Any]  # Parameters passed to action
    observation: str          # Result observed

    # Metadata
    confidence: float         # Step confidence (0.0 - 1.0)
    outcome: StepOutcome      # Success/failure of step
    duration_ms: int          # Execution time in milliseconds
    timestamp: datetime       # When step was executed

    # Pattern tracking
    pattern_used: Optional[str] = None   # Pattern ID if applicable
    pattern_similarity: float = 0.0      # How well pattern matched

    # Context
    context_summary: str = ""  # Brief context at this step
    error_message: Optional[str] = None  # Error if failed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation[:500] if self.observation else "",  # Truncate long observations
            "confidence": self.confidence,
            "outcome": self.outcome.value,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "pattern_used": self.pattern_used,
            "pattern_similarity": self.pattern_similarity,
            "context_summary": self.context_summary,
            "error_message": self.error_message
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrajectoryStep":
        """Create from dictionary."""
        return cls(
            step_id=data["step_id"],
            step_number=data["step_number"],
            thought=data["thought"],
            action=data["action"],
            action_input=data.get("action_input", {}),
            observation=data["observation"],
            confidence=data["confidence"],
            outcome=StepOutcome(data["outcome"]),
            duration_ms=data["duration_ms"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            pattern_used=data.get("pattern_used"),
            pattern_similarity=data.get("pattern_similarity", 0.0),
            context_summary=data.get("context_summary", ""),
            error_message=data.get("error_message")
        )


@dataclass
class Trajectory:
    """
    Complete decision trajectory for a task.

    Captures the full sequence of agent decisions from goal to outcome.
    """
    trajectory_id: str
    task_description: str
    agent_id: str

    # Steps
    steps: List[TrajectoryStep] = field(default_factory=list)

    # Outcome
    status: TrajectoryStatus = TrajectoryStatus.IN_PROGRESS
    final_outcome: str = ""
    quality_score: float = 0.0  # 0.0 - 1.0 (from feedback)

    # Embedding for similarity search
    embedding: List[float] = field(default_factory=list)  # 768-dim trajectory embedding

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_duration_ms: int = 0

    # Context
    initial_context: Dict[str, Any] = field(default_factory=dict)
    goal_type: str = ""  # e.g., "coding", "research", "analysis"

    # Learning metadata
    feedback_received: bool = False
    feedback_timestamp: Optional[datetime] = None
    improvement_suggestions: List[str] = field(default_factory=list)

    def add_step(self, step: TrajectoryStep) -> None:
        """Add a step to the trajectory."""
        self.steps.append(step)
        self.total_duration_ms += step.duration_ms

    def complete(self, outcome: str, quality: float = 0.5) -> None:
        """Mark trajectory as completed."""
        self.status = TrajectoryStatus.COMPLETED
        self.final_outcome = outcome
        self.quality_score = quality
        self.completed_at = datetime.now()

    def fail(self, error: str) -> None:
        """Mark trajectory as failed."""
        self.status = TrajectoryStatus.FAILED
        self.final_outcome = f"FAILED: {error}"
        self.completed_at = datetime.now()

    def get_action_sequence(self) -> List[str]:
        """Get sequence of actions taken."""
        return [s.action for s in self.steps]

    def get_success_rate(self) -> float:
        """Calculate step success rate."""
        if not self.steps:
            return 0.0
        successes = sum(1 for s in self.steps if s.outcome == StepOutcome.SUCCESS)
        return successes / len(self.steps)

    def to_text(self) -> str:
        """Convert trajectory to text for embedding."""
        parts = [
            f"Task: {self.task_description}",
            f"Goal Type: {self.goal_type}",
            f"Actions: {' -> '.join(self.get_action_sequence())}",
            f"Outcome: {self.final_outcome}",
            f"Quality: {self.quality_score:.2f}",
            f"Steps: {len(self.steps)}",
            f"Success Rate: {self.get_success_rate():.2%}"
        ]
        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trajectory_id": self.trajectory_id,
            "task_description": self.task_description,
            "agent_id": self.agent_id,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "final_outcome": self.final_outcome,
            "quality_score": self.quality_score,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_duration_ms": self.total_duration_ms,
            "initial_context": self.initial_context,
            "goal_type": self.goal_type,
            "feedback_received": self.feedback_received,
            "feedback_timestamp": self.feedback_timestamp.isoformat() if self.feedback_timestamp else None,
            "improvement_suggestions": self.improvement_suggestions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trajectory":
        """Create from dictionary."""
        trajectory = cls(
            trajectory_id=data["trajectory_id"],
            task_description=data["task_description"],
            agent_id=data["agent_id"],
            status=TrajectoryStatus(data["status"]),
            final_outcome=data.get("final_outcome", ""),
            quality_score=data.get("quality_score", 0.0),
            embedding=data.get("embedding", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            total_duration_ms=data.get("total_duration_ms", 0),
            initial_context=data.get("initial_context", {}),
            goal_type=data.get("goal_type", ""),
            feedback_received=data.get("feedback_received", False),
            feedback_timestamp=datetime.fromisoformat(data["feedback_timestamp"]) if data.get("feedback_timestamp") else None,
            improvement_suggestions=data.get("improvement_suggestions", [])
        )

        for step_data in data.get("steps", []):
            trajectory.steps.append(TrajectoryStep.from_dict(step_data))

        return trajectory


class TrajectoryRecorder:
    """
    Records and manages decision trajectories.

    Provides:
    - Real-time trajectory recording
    - Trajectory completion and feedback
    - Similarity search for past trajectories
    - Pattern extraction from successful trajectories
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the trajectory recorder."""
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Active trajectories (in memory for fast access)
        self.active_trajectories: Dict[str, Trajectory] = {}

        # Current step tracking
        self.pending_steps: Dict[str, Dict[str, Any]] = {}  # trajectory_id -> pending step data

        # Initialize database
        self._init_database()

        logger.info(f"TrajectoryRecorder initialized with DB: {self.db_path}")

    def _init_database(self) -> None:
        """Initialize SQLite database for trajectory storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Trajectories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trajectories (
                trajectory_id TEXT PRIMARY KEY,
                task_description TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                status TEXT DEFAULT 'in_progress',
                final_outcome TEXT,
                quality_score REAL DEFAULT 0.0,
                embedding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                total_duration_ms INTEGER DEFAULT 0,
                initial_context TEXT,
                goal_type TEXT,
                feedback_received INTEGER DEFAULT 0,
                feedback_timestamp TIMESTAMP,
                improvement_suggestions TEXT,
                steps_json TEXT
            )
        ''')

        # Trajectory steps table (normalized for querying)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trajectory_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trajectory_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                step_number INTEGER NOT NULL,
                thought TEXT,
                action TEXT NOT NULL,
                action_input TEXT,
                observation TEXT,
                confidence REAL DEFAULT 0.5,
                outcome TEXT DEFAULT 'success',
                duration_ms INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                pattern_used TEXT,
                pattern_similarity REAL DEFAULT 0.0,
                context_summary TEXT,
                error_message TEXT,
                FOREIGN KEY (trajectory_id) REFERENCES trajectories(trajectory_id)
            )
        ''')

        # Pattern learning table - tracks action patterns and their success rates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_patterns (
                pattern_id TEXT PRIMARY KEY,
                action_sequence TEXT NOT NULL,
                goal_type TEXT,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                average_quality REAL DEFAULT 0.0,
                average_duration_ms INTEGER DEFAULT 0,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                embedding BLOB
            )
        ''')

        # Indexes for efficient queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_traj_agent ON trajectories(agent_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_traj_status ON trajectories(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_traj_goal_type ON trajectories(goal_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_traj_quality ON trajectories(quality_score)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_steps_traj ON trajectory_steps(trajectory_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_steps_action ON trajectory_steps(action)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_goal ON action_patterns(goal_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_patterns_success ON action_patterns(success_rate)')

        conn.commit()
        conn.close()

    # ==================== Trajectory Lifecycle ====================

    def start_trajectory(
        self,
        task_description: str,
        agent_id: str,
        goal_type: str = "",
        initial_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Start recording a new trajectory.

        Returns:
            trajectory_id for tracking
        """
        trajectory_id = f"traj_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"

        trajectory = Trajectory(
            trajectory_id=trajectory_id,
            task_description=task_description,
            agent_id=agent_id,
            goal_type=goal_type,
            initial_context=initial_context or {},
            created_at=datetime.now()
        )

        # Store in memory for fast access
        self.active_trajectories[trajectory_id] = trajectory

        # Persist to database
        self._save_trajectory(trajectory)

        logger.info(f"Started trajectory {trajectory_id}: {task_description[:50]}...")

        return trajectory_id

    def record_step_start(
        self,
        trajectory_id: str,
        thought: str,
        action: str,
        action_input: Dict[str, Any],
        context_summary: str = ""
    ) -> str:
        """
        Record the start of a trajectory step (pre-tool-use hook).

        Called before executing an action to capture the reasoning.

        Returns:
            step_id for tracking
        """
        if trajectory_id not in self.active_trajectories:
            logger.warning(f"Trajectory {trajectory_id} not found")
            return ""

        trajectory = self.active_trajectories[trajectory_id]
        step_number = len(trajectory.steps) + 1
        step_id = f"step_{trajectory_id}_{step_number}"

        # Store pending step data
        self.pending_steps[trajectory_id] = {
            "step_id": step_id,
            "step_number": step_number,
            "thought": thought,
            "action": action,
            "action_input": action_input,
            "context_summary": context_summary,
            "start_time": datetime.now()
        }

        return step_id

    def record_step_end(
        self,
        trajectory_id: str,
        observation: str,
        outcome: StepOutcome = StepOutcome.SUCCESS,
        confidence: float = 0.7,
        pattern_used: Optional[str] = None,
        pattern_similarity: float = 0.0,
        error_message: Optional[str] = None
    ) -> None:
        """
        Record the end of a trajectory step (post-tool-use hook).

        Called after executing an action to capture the result.
        """
        if trajectory_id not in self.active_trajectories:
            logger.warning(f"Trajectory {trajectory_id} not found")
            return

        if trajectory_id not in self.pending_steps:
            logger.warning(f"No pending step for trajectory {trajectory_id}")
            return

        trajectory = self.active_trajectories[trajectory_id]
        pending = self.pending_steps.pop(trajectory_id)

        # Calculate duration
        start_time = pending["start_time"]
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Create step
        step = TrajectoryStep(
            step_id=pending["step_id"],
            step_number=pending["step_number"],
            thought=pending["thought"],
            action=pending["action"],
            action_input=pending["action_input"],
            observation=observation,
            confidence=confidence,
            outcome=outcome,
            duration_ms=duration_ms,
            timestamp=start_time,
            pattern_used=pattern_used,
            pattern_similarity=pattern_similarity,
            context_summary=pending["context_summary"],
            error_message=error_message
        )

        # Add to trajectory
        trajectory.add_step(step)

        # Save step to database
        self._save_step(trajectory_id, step)

        logger.debug(f"Recorded step {step.step_number} for {trajectory_id}: {step.action} -> {outcome.value}")

    def complete_trajectory(
        self,
        trajectory_id: str,
        final_outcome: str,
        quality_score: float = 0.5
    ) -> Optional[Trajectory]:
        """
        Complete a trajectory and finalize it.

        Returns:
            Completed Trajectory object
        """
        if trajectory_id not in self.active_trajectories:
            logger.warning(f"Trajectory {trajectory_id} not found")
            return None

        trajectory = self.active_trajectories[trajectory_id]
        trajectory.complete(final_outcome, quality_score)

        # Generate embedding
        trajectory.embedding = self._generate_trajectory_embedding(trajectory)

        # Update database
        self._save_trajectory(trajectory)

        # Extract and update patterns
        self._extract_patterns(trajectory)

        # Remove from active (keep in DB)
        del self.active_trajectories[trajectory_id]

        logger.info(f"Completed trajectory {trajectory_id} with quality {quality_score:.2f}")

        return trajectory

    def fail_trajectory(
        self,
        trajectory_id: str,
        error: str
    ) -> Optional[Trajectory]:
        """
        Mark a trajectory as failed.

        Returns:
            Failed Trajectory object
        """
        if trajectory_id not in self.active_trajectories:
            logger.warning(f"Trajectory {trajectory_id} not found")
            return None

        trajectory = self.active_trajectories[trajectory_id]
        trajectory.fail(error)

        # Update database
        self._save_trajectory(trajectory)

        # Remove from active
        del self.active_trajectories[trajectory_id]

        logger.info(f"Failed trajectory {trajectory_id}: {error[:50]}...")

        return trajectory

    # ==================== Feedback & Learning ====================

    def provide_feedback(
        self,
        trajectory_id: str,
        quality_score: float,
        improvement_suggestions: Optional[List[str]] = None
    ) -> bool:
        """
        Provide feedback on a completed trajectory.

        This feedback is used for Sona-style pattern weight adjustment.

        Args:
            trajectory_id: Trajectory to provide feedback for
            quality_score: Quality rating 0.0 - 1.0
            improvement_suggestions: Optional list of suggestions

        Returns:
            Success status
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                UPDATE trajectories
                SET quality_score = ?,
                    feedback_received = 1,
                    feedback_timestamp = ?,
                    improvement_suggestions = ?
                WHERE trajectory_id = ?
            ''', (
                quality_score,
                datetime.now().isoformat(),
                json.dumps(improvement_suggestions or []),
                trajectory_id
            ))

            conn.commit()

            # Update pattern weights based on feedback
            self._update_pattern_weights(trajectory_id, quality_score)

            logger.info(f"Received feedback for {trajectory_id}: quality={quality_score:.2f}")
            return True

        except Exception as e:
            logger.error(f"Failed to store feedback: {e}")
            return False
        finally:
            conn.close()

    def _update_pattern_weights(self, trajectory_id: str, quality_score: float) -> None:
        """Update pattern success rates based on trajectory feedback."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get trajectory steps
            cursor.execute('''
                SELECT action FROM trajectory_steps
                WHERE trajectory_id = ?
                ORDER BY step_number
            ''', (trajectory_id,))

            actions = [row[0] for row in cursor.fetchall()]

            if len(actions) >= 2:
                # Create action sequence pattern
                action_sequence = " -> ".join(actions)
                pattern_id = hashlib.sha256(action_sequence.encode()).hexdigest()[:16]

                # Get goal type
                cursor.execute('SELECT goal_type FROM trajectories WHERE trajectory_id = ?', (trajectory_id,))
                result = cursor.fetchone()
                goal_type = result[0] if result else ""

                # Update or insert pattern
                cursor.execute('''
                    INSERT INTO action_patterns (pattern_id, action_sequence, goal_type, usage_count, success_count, average_quality)
                    VALUES (?, ?, ?, 1, ?, ?)
                    ON CONFLICT(pattern_id) DO UPDATE SET
                        usage_count = usage_count + 1,
                        success_count = success_count + CASE WHEN ? >= 0.6 THEN 1 ELSE 0 END,
                        success_rate = CAST(success_count + CASE WHEN ? >= 0.6 THEN 1 ELSE 0 END AS REAL) / (usage_count + 1),
                        average_quality = (average_quality * usage_count + ?) / (usage_count + 1),
                        last_seen = CURRENT_TIMESTAMP
                ''', (
                    pattern_id, action_sequence, goal_type,
                    1 if quality_score >= 0.6 else 0, quality_score,
                    quality_score, quality_score, quality_score
                ))

                conn.commit()

        except Exception as e:
            logger.error(f"Failed to update pattern weights: {e}")
        finally:
            conn.close()

    # ==================== Search & Retrieval ====================

    def find_similar_trajectories(
        self,
        task_description: str,
        goal_type: str = "",
        limit: int = 5,
        min_quality: float = 0.0
    ) -> List[Trajectory]:
        """
        Find similar past trajectories for a task.

        Uses text similarity (future: vector similarity with embeddings).

        Args:
            task_description: Description of current task
            goal_type: Type of goal (for filtering)
            limit: Max results to return
            min_quality: Minimum quality score filter

        Returns:
            List of similar trajectories
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Build query with optional goal_type filter
            if goal_type:
                cursor.execute('''
                    SELECT trajectory_id, task_description, agent_id, status, final_outcome,
                           quality_score, created_at, completed_at, total_duration_ms,
                           initial_context, goal_type, steps_json
                    FROM trajectories
                    WHERE status = 'completed'
                      AND goal_type = ?
                      AND quality_score >= ?
                    ORDER BY quality_score DESC
                    LIMIT ?
                ''', (goal_type, min_quality, limit * 3))  # Over-fetch for re-ranking
            else:
                cursor.execute('''
                    SELECT trajectory_id, task_description, agent_id, status, final_outcome,
                           quality_score, created_at, completed_at, total_duration_ms,
                           initial_context, goal_type, steps_json
                    FROM trajectories
                    WHERE status = 'completed'
                      AND quality_score >= ?
                    ORDER BY quality_score DESC
                    LIMIT ?
                ''', (min_quality, limit * 3))

            rows = cursor.fetchall()

            # Simple text similarity scoring
            results = []
            task_words = set(task_description.lower().split())

            for row in rows:
                traj_words = set(row[1].lower().split())
                similarity = len(task_words & traj_words) / max(len(task_words | traj_words), 1)

                # Create trajectory object
                trajectory = Trajectory(
                    trajectory_id=row[0],
                    task_description=row[1],
                    agent_id=row[2],
                    status=TrajectoryStatus(row[3]),
                    final_outcome=row[4] or "",
                    quality_score=row[5],
                    created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
                    completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                    total_duration_ms=row[8] or 0,
                    initial_context=json.loads(row[9]) if row[9] else {},
                    goal_type=row[10] or ""
                )

                # Load steps
                if row[11]:
                    steps_data = json.loads(row[11])
                    for step_data in steps_data:
                        trajectory.steps.append(TrajectoryStep.from_dict(step_data))

                results.append((similarity, trajectory))

            # Sort by similarity and return top results
            results.sort(key=lambda x: x[0], reverse=True)
            return [t for _, t in results[:limit]]

        except Exception as e:
            logger.error(f"Failed to find similar trajectories: {e}")
            return []
        finally:
            conn.close()

    def get_effective_patterns(
        self,
        goal_type: str = "",
        min_success_rate: float = 0.6,
        min_usage: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get effective action patterns for a goal type.

        Args:
            goal_type: Type of goal (empty for all)
            min_success_rate: Minimum success rate filter
            min_usage: Minimum usage count filter

        Returns:
            List of effective patterns with statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if goal_type:
                cursor.execute('''
                    SELECT pattern_id, action_sequence, goal_type, usage_count,
                           success_count, success_rate, average_quality
                    FROM action_patterns
                    WHERE goal_type = ?
                      AND success_rate >= ?
                      AND usage_count >= ?
                    ORDER BY success_rate DESC, average_quality DESC
                ''', (goal_type, min_success_rate, min_usage))
            else:
                cursor.execute('''
                    SELECT pattern_id, action_sequence, goal_type, usage_count,
                           success_count, success_rate, average_quality
                    FROM action_patterns
                    WHERE success_rate >= ?
                      AND usage_count >= ?
                    ORDER BY success_rate DESC, average_quality DESC
                ''', (min_success_rate, min_usage))

            patterns = []
            for row in cursor.fetchall():
                patterns.append({
                    "pattern_id": row[0],
                    "action_sequence": row[1],
                    "goal_type": row[2],
                    "usage_count": row[3],
                    "success_count": row[4],
                    "success_rate": row[5],
                    "average_quality": row[6]
                })

            return patterns

        except Exception as e:
            logger.error(f"Failed to get effective patterns: {e}")
            return []
        finally:
            conn.close()

    def get_trajectory(self, trajectory_id: str) -> Optional[Trajectory]:
        """Get a specific trajectory by ID."""
        # Check active first
        if trajectory_id in self.active_trajectories:
            return self.active_trajectories[trajectory_id]

        # Load from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT trajectory_id, task_description, agent_id, status, final_outcome,
                       quality_score, created_at, completed_at, total_duration_ms,
                       initial_context, goal_type, steps_json, embedding,
                       feedback_received, feedback_timestamp, improvement_suggestions
                FROM trajectories
                WHERE trajectory_id = ?
            ''', (trajectory_id,))

            row = cursor.fetchone()
            if not row:
                return None

            trajectory = Trajectory(
                trajectory_id=row[0],
                task_description=row[1],
                agent_id=row[2],
                status=TrajectoryStatus(row[3]),
                final_outcome=row[4] or "",
                quality_score=row[5],
                created_at=datetime.fromisoformat(row[6]) if row[6] else datetime.now(),
                completed_at=datetime.fromisoformat(row[7]) if row[7] else None,
                total_duration_ms=row[8] or 0,
                initial_context=json.loads(row[9]) if row[9] else {},
                goal_type=row[10] or "",
                embedding=json.loads(row[12]) if row[12] else [],
                feedback_received=bool(row[13]),
                feedback_timestamp=datetime.fromisoformat(row[14]) if row[14] else None,
                improvement_suggestions=json.loads(row[15]) if row[15] else []
            )

            # Load steps
            if row[11]:
                steps_data = json.loads(row[11])
                for step_data in steps_data:
                    trajectory.steps.append(TrajectoryStep.from_dict(step_data))

            return trajectory

        except Exception as e:
            logger.error(f"Failed to get trajectory {trajectory_id}: {e}")
            return None
        finally:
            conn.close()

    def list_trajectories(
        self,
        agent_id: Optional[str] = None,
        status: Optional[TrajectoryStatus] = None,
        goal_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List trajectories with optional filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            query = '''
                SELECT trajectory_id, task_description, agent_id, status,
                       quality_score, created_at, completed_at, goal_type,
                       (SELECT COUNT(*) FROM trajectory_steps WHERE trajectory_id = t.trajectory_id) as step_count
                FROM trajectories t
                WHERE 1=1
            '''
            params = []

            if agent_id:
                query += ' AND agent_id = ?'
                params.append(agent_id)

            if status:
                query += ' AND status = ?'
                params.append(status.value)

            if goal_type:
                query += ' AND goal_type = ?'
                params.append(goal_type)

            query += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)

            results = []
            for row in cursor.fetchall():
                results.append({
                    "trajectory_id": row[0],
                    "task_description": row[1][:100],  # Truncate
                    "agent_id": row[2],
                    "status": row[3],
                    "quality_score": row[4],
                    "created_at": row[5],
                    "completed_at": row[6],
                    "goal_type": row[7],
                    "step_count": row[8]
                })

            return results

        except Exception as e:
            logger.error(f"Failed to list trajectories: {e}")
            return []
        finally:
            conn.close()

    # ==================== Statistics ====================

    def get_statistics(self) -> Dict[str, Any]:
        """Get trajectory system statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            stats = {
                "active_trajectories": len(self.active_trajectories),
                "total_trajectories": 0,
                "completed_trajectories": 0,
                "failed_trajectories": 0,
                "average_quality": 0.0,
                "total_steps": 0,
                "total_patterns": 0,
                "effective_patterns": 0
            }

            # Total counts
            cursor.execute('SELECT COUNT(*) FROM trajectories')
            stats["total_trajectories"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM trajectories WHERE status = 'completed'")
            stats["completed_trajectories"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM trajectories WHERE status = 'failed'")
            stats["failed_trajectories"] = cursor.fetchone()[0]

            # Average quality
            cursor.execute("SELECT AVG(quality_score) FROM trajectories WHERE status = 'completed' AND feedback_received = 1")
            result = cursor.fetchone()
            stats["average_quality"] = result[0] if result[0] else 0.0

            # Total steps
            cursor.execute('SELECT COUNT(*) FROM trajectory_steps')
            stats["total_steps"] = cursor.fetchone()[0]

            # Pattern stats
            cursor.execute('SELECT COUNT(*) FROM action_patterns')
            stats["total_patterns"] = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM action_patterns WHERE success_rate >= 0.6 AND usage_count >= 3')
            stats["effective_patterns"] = cursor.fetchone()[0]

            return stats

        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {"error": str(e)}
        finally:
            conn.close()

    # ==================== Internal Methods ====================

    def _save_trajectory(self, trajectory: Trajectory) -> None:
        """Save or update trajectory in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT OR REPLACE INTO trajectories (
                    trajectory_id, task_description, agent_id, status, final_outcome,
                    quality_score, embedding, created_at, completed_at, total_duration_ms,
                    initial_context, goal_type, feedback_received, feedback_timestamp,
                    improvement_suggestions, steps_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trajectory.trajectory_id,
                trajectory.task_description,
                trajectory.agent_id,
                trajectory.status.value,
                trajectory.final_outcome,
                trajectory.quality_score,
                json.dumps(trajectory.embedding) if trajectory.embedding else None,
                trajectory.created_at.isoformat(),
                trajectory.completed_at.isoformat() if trajectory.completed_at else None,
                trajectory.total_duration_ms,
                json.dumps(trajectory.initial_context),
                trajectory.goal_type,
                1 if trajectory.feedback_received else 0,
                trajectory.feedback_timestamp.isoformat() if trajectory.feedback_timestamp else None,
                json.dumps(trajectory.improvement_suggestions),
                json.dumps([s.to_dict() for s in trajectory.steps])
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"Failed to save trajectory: {e}")
        finally:
            conn.close()

    def _save_step(self, trajectory_id: str, step: TrajectoryStep) -> None:
        """Save a step to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO trajectory_steps (
                    trajectory_id, step_id, step_number, thought, action, action_input,
                    observation, confidence, outcome, duration_ms, timestamp,
                    pattern_used, pattern_similarity, context_summary, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trajectory_id,
                step.step_id,
                step.step_number,
                step.thought,
                step.action,
                json.dumps(step.action_input),
                step.observation[:2000] if step.observation else "",  # Truncate long observations
                step.confidence,
                step.outcome.value,
                step.duration_ms,
                step.timestamp.isoformat(),
                step.pattern_used,
                step.pattern_similarity,
                step.context_summary,
                step.error_message
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"Failed to save step: {e}")
        finally:
            conn.close()

    def _generate_trajectory_embedding(self, trajectory: Trajectory) -> List[float]:
        """
        Generate embedding for trajectory.

        For now, returns empty list. Integration with embedding service
        should be added for vector similarity search.
        """
        # TODO: Integrate with enhanced-memory-mcp embedding service
        # trajectory_text = trajectory.to_text()
        # return await embed_text(trajectory_text)
        return []

    def _extract_patterns(self, trajectory: Trajectory) -> None:
        """Extract and store action patterns from completed trajectory."""
        if len(trajectory.steps) < 2:
            return

        # Extract action sequence
        action_sequence = " -> ".join([s.action for s in trajectory.steps])
        pattern_id = hashlib.sha256(action_sequence.encode()).hexdigest()[:16]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get total duration
            total_duration = trajectory.total_duration_ms

            cursor.execute('''
                INSERT INTO action_patterns (
                    pattern_id, action_sequence, goal_type, usage_count,
                    success_count, success_rate, average_quality, average_duration_ms
                ) VALUES (?, ?, ?, 1, ?, ?, ?, ?)
                ON CONFLICT(pattern_id) DO UPDATE SET
                    usage_count = usage_count + 1,
                    success_count = success_count + CASE WHEN ? >= 0.6 THEN 1 ELSE 0 END,
                    success_rate = CAST(success_count AS REAL) / usage_count,
                    average_quality = (average_quality * (usage_count - 1) + ?) / usage_count,
                    average_duration_ms = (average_duration_ms * (usage_count - 1) + ?) / usage_count,
                    last_seen = CURRENT_TIMESTAMP
            ''', (
                pattern_id,
                action_sequence,
                trajectory.goal_type,
                1 if trajectory.quality_score >= 0.6 else 0,
                trajectory.quality_score if trajectory.quality_score >= 0.6 else 0.0,
                trajectory.quality_score,
                total_duration,
                trajectory.quality_score,
                trajectory.quality_score,
                total_duration
            ))

            conn.commit()

        except Exception as e:
            logger.error(f"Failed to extract patterns: {e}")
        finally:
            conn.close()


# ==================== MCP Tool Registration ====================

def register_trajectory_tools(app, db_path: Optional[Path] = None):
    """
    Register trajectory recording tools with MCP app.

    Args:
        app: FastMCP app instance
        db_path: Path to database
    """
    recorder = TrajectoryRecorder(db_path)

    @app.tool()
    async def start_trajectory(
        task_description: str,
        agent_id: str,
        goal_type: str = "",
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start recording a new agent trajectory.

        Call this at the beginning of a task to track the decision path.

        Args:
            task_description: Description of the task being performed
            agent_id: ID of the agent performing the task
            goal_type: Type of goal (e.g., "coding", "research", "analysis")
            initial_context: Optional context dictionary

        Returns:
            trajectory_id for tracking subsequent steps
        """
        trajectory_id = recorder.start_trajectory(
            task_description=task_description,
            agent_id=agent_id,
            goal_type=goal_type,
            initial_context=initial_context
        )
        return {
            "trajectory_id": trajectory_id,
            "status": "started",
            "message": f"Trajectory recording started: {trajectory_id}"
        }

    @app.tool()
    async def record_trajectory_step(
        trajectory_id: str,
        thought: str,
        action: str,
        observation: str,
        action_input: Optional[Dict[str, Any]] = None,
        confidence: float = 0.7,
        outcome: str = "success",
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Record a step in an active trajectory.

        Captures the ReAct pattern: Thought -> Action -> Observation.

        Args:
            trajectory_id: ID of active trajectory
            thought: Agent's reasoning before action
            action: Tool/action taken (e.g., "Read", "Edit")
            observation: Result observed
            action_input: Parameters passed to action
            confidence: Confidence level (0.0-1.0)
            outcome: Step outcome ("success", "failure", "partial", "skipped")
            error_message: Error message if failed

        Returns:
            Confirmation of step recording
        """
        # Start step
        step_id = recorder.record_step_start(
            trajectory_id=trajectory_id,
            thought=thought,
            action=action,
            action_input=action_input or {},
            context_summary=""
        )

        if not step_id:
            return {"error": f"Failed to start step for trajectory {trajectory_id}"}

        # End step immediately (for synchronous recording)
        recorder.record_step_end(
            trajectory_id=trajectory_id,
            observation=observation,
            outcome=StepOutcome(outcome),
            confidence=confidence,
            error_message=error_message
        )

        return {
            "step_id": step_id,
            "status": "recorded",
            "message": f"Step recorded: {action} -> {outcome}"
        }

    @app.tool()
    async def complete_trajectory(
        trajectory_id: str,
        final_outcome: str,
        quality_score: float = 0.5
    ) -> Dict[str, Any]:
        """
        Complete and finalize a trajectory.

        Call this when the task is finished to close the trajectory.

        Args:
            trajectory_id: ID of trajectory to complete
            final_outcome: Description of final outcome
            quality_score: Initial quality assessment (0.0-1.0)

        Returns:
            Summary of completed trajectory
        """
        trajectory = recorder.complete_trajectory(
            trajectory_id=trajectory_id,
            final_outcome=final_outcome,
            quality_score=quality_score
        )

        if not trajectory:
            return {"error": f"Trajectory {trajectory_id} not found or already completed"}

        return {
            "trajectory_id": trajectory_id,
            "status": "completed",
            "final_outcome": final_outcome,
            "quality_score": quality_score,
            "total_steps": len(trajectory.steps),
            "total_duration_ms": trajectory.total_duration_ms,
            "success_rate": trajectory.get_success_rate()
        }

    @app.tool()
    async def provide_trajectory_feedback(
        trajectory_id: str,
        quality_score: float,
        improvement_suggestions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Provide quality feedback on a completed trajectory.

        This feedback is used for Sona-style pattern weight adjustment.
        Patterns from high-quality trajectories are weighted higher.

        Args:
            trajectory_id: ID of completed trajectory
            quality_score: Quality rating (0.0-1.0)
            improvement_suggestions: Optional list of improvement suggestions

        Returns:
            Confirmation of feedback recording
        """
        success = recorder.provide_feedback(
            trajectory_id=trajectory_id,
            quality_score=quality_score,
            improvement_suggestions=improvement_suggestions
        )

        if not success:
            return {"error": f"Failed to record feedback for {trajectory_id}"}

        return {
            "trajectory_id": trajectory_id,
            "status": "feedback_recorded",
            "quality_score": quality_score,
            "message": "Pattern weights updated based on feedback"
        }

    @app.tool()
    async def find_similar_trajectories(
        task_description: str,
        goal_type: str = "",
        limit: int = 5,
        min_quality: float = 0.5
    ) -> Dict[str, Any]:
        """
        Find similar past trajectories for learning.

        Use this before starting a task to learn from past experiences.

        Args:
            task_description: Description of current task
            goal_type: Type of goal for filtering
            limit: Maximum results
            min_quality: Minimum quality score filter

        Returns:
            List of similar trajectories with action sequences
        """
        trajectories = recorder.find_similar_trajectories(
            task_description=task_description,
            goal_type=goal_type,
            limit=limit,
            min_quality=min_quality
        )

        return {
            "query": task_description,
            "count": len(trajectories),
            "trajectories": [
                {
                    "trajectory_id": t.trajectory_id,
                    "task_description": t.task_description[:100],
                    "action_sequence": t.get_action_sequence(),
                    "quality_score": t.quality_score,
                    "success_rate": t.get_success_rate(),
                    "total_steps": len(t.steps)
                }
                for t in trajectories
            ]
        }

    @app.tool()
    async def get_effective_patterns(
        goal_type: str = "",
        min_success_rate: float = 0.6,
        min_usage: int = 3
    ) -> Dict[str, Any]:
        """
        Get effective action patterns for a goal type.

        Returns patterns that have proven successful across multiple trajectories.

        Args:
            goal_type: Type of goal (empty for all)
            min_success_rate: Minimum success rate (0.0-1.0)
            min_usage: Minimum number of uses

        Returns:
            List of effective patterns with statistics
        """
        patterns = recorder.get_effective_patterns(
            goal_type=goal_type,
            min_success_rate=min_success_rate,
            min_usage=min_usage
        )

        return {
            "goal_type": goal_type or "all",
            "count": len(patterns),
            "patterns": patterns
        }

    @app.tool()
    async def get_trajectory_statistics() -> Dict[str, Any]:
        """
        Get statistics about the trajectory recording system.

        Returns:
            Comprehensive statistics including totals, averages, and pattern counts
        """
        return recorder.get_statistics()

    logger.info(f"Registered 7 trajectory recording tools (God Agent Phase 4.1)")
    return recorder


# ==================== Standalone Testing ====================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("Trajectory Recording System - God Agent Phase 4.1")
    print("=" * 60)

    # Create recorder
    recorder = TrajectoryRecorder()

    # Test trajectory lifecycle
    print("\n1. Starting trajectory...")
    traj_id = recorder.start_trajectory(
        task_description="Implement a REST API endpoint for user authentication",
        agent_id="test-agent-001",
        goal_type="coding",
        initial_context={"language": "Python", "framework": "FastAPI"}
    )
    print(f"   Created: {traj_id}")

    # Record steps
    print("\n2. Recording steps...")

    # Step 1: Read existing code
    recorder.record_step_start(traj_id, "Need to understand existing code structure", "Read", {"file_path": "/app/main.py"})
    recorder.record_step_end(traj_id, "Found existing FastAPI app with 5 endpoints", StepOutcome.SUCCESS, 0.9)
    print("   Step 1: Read -> SUCCESS")

    # Step 2: Write new endpoint
    recorder.record_step_start(traj_id, "Writing authentication endpoint", "Write", {"file_path": "/app/auth.py"})
    recorder.record_step_end(traj_id, "Created auth.py with login/register endpoints", StepOutcome.SUCCESS, 0.85)
    print("   Step 2: Write -> SUCCESS")

    # Step 3: Run tests
    recorder.record_step_start(traj_id, "Need to verify implementation works", "Bash", {"command": "pytest tests/"})
    recorder.record_step_end(traj_id, "All 12 tests passed", StepOutcome.SUCCESS, 0.95)
    print("   Step 3: Bash (tests) -> SUCCESS")

    # Complete trajectory
    print("\n3. Completing trajectory...")
    trajectory = recorder.complete_trajectory(
        traj_id,
        "Successfully implemented REST API authentication endpoint with tests",
        quality_score=0.85
    )
    print(f"   Status: {trajectory.status.value}")
    print(f"   Quality: {trajectory.quality_score:.2f}")
    print(f"   Steps: {len(trajectory.steps)}")
    print(f"   Success rate: {trajectory.get_success_rate():.2%}")

    # Provide feedback
    print("\n4. Providing feedback...")
    recorder.provide_feedback(traj_id, 0.9, ["Consider adding rate limiting"])
    print("   Feedback recorded with quality 0.9")

    # Find similar trajectories
    print("\n5. Finding similar trajectories...")
    similar = recorder.find_similar_trajectories(
        "Create an API endpoint for password reset",
        goal_type="coding"
    )
    print(f"   Found {len(similar)} similar trajectories")

    # Get effective patterns
    print("\n6. Getting effective patterns...")
    patterns = recorder.get_effective_patterns(goal_type="coding")
    print(f"   Found {len(patterns)} effective patterns")
    if patterns:
        print(f"   Top pattern: {patterns[0]['action_sequence']}")

    # Get statistics
    print("\n7. System Statistics:")
    stats = recorder.get_statistics()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    print("\n" + "=" * 60)
    print("Trajectory Recording System - Tests Complete")
    print("=" * 60)
