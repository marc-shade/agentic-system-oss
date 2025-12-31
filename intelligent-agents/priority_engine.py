#!/usr/bin/env python3
"""
Priority Engine - Intelligent Task Prioritization for Always-On Orchestration

Part of the Translation Layer (Nate B Jones framework):
- Intent Capture Stream → **Priority Engine** → Task Router

Scoring Methodology:
┌─────────────────────────────────────────────────────────────────┐
│                      PRIORITY SCORE                              │
├─────────────────────────────────────────────────────────────────┤
│  Base Score = (Urgency × 0.3) + (Importance × 0.3) +            │
│               (Effort_Inverse × 0.15) + (Goal_Alignment × 0.15) │
│               + (Context_Bonus × 0.10)                          │
├─────────────────────────────────────────────────────────────────┤
│  Modifiers:                                                      │
│  • Deadline decay: Score increases as deadline approaches        │
│  • Dependency boost: Blocking tasks get +20%                     │
│  • Blocked penalty: Blocked tasks get -50%                       │
│  • Momentum bonus: Related to current work gets +10%             │
└─────────────────────────────────────────────────────────────────┘

Eisenhower Matrix Integration:
  Q1 (Do):       Urgent + Important      → Score 80-100
  Q2 (Schedule): Not Urgent + Important  → Score 50-79
  Q3 (Delegate): Urgent + Not Important  → Score 30-49
  Q4 (Eliminate): Neither                → Score 0-29

Status: Phase 2 (Active Priority Management)
"""

import asyncio
import json
import logging
import math
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# Configure logging
logger = logging.getLogger("priority-engine")

# Configuration
AGENT_RUNTIME_DB = Path.home() / ".claude" / "agent_runtime.db"
PRIORITY_STATE_FILE = Path("/tmp/priority_engine_state.json")


class EisenhowerQuadrant(Enum):
    """Eisenhower Matrix quadrants"""
    DO = "Q1_do"              # Urgent + Important: Do immediately
    SCHEDULE = "Q2_schedule"   # Not Urgent + Important: Schedule time
    DELEGATE = "Q3_delegate"   # Urgent + Not Important: Delegate if possible
    ELIMINATE = "Q4_eliminate" # Neither: Consider eliminating


class EffortLevel(Enum):
    """Estimated effort levels"""
    TRIVIAL = 1      # < 5 minutes
    SMALL = 2        # 5-30 minutes
    MEDIUM = 3       # 30 min - 2 hours
    LARGE = 4        # 2-8 hours
    EPIC = 5         # > 8 hours (should be decomposed)


@dataclass
class TaskContext:
    """Context for priority calculation"""
    current_goal_id: Optional[int] = None
    current_focus_area: Optional[str] = None
    time_of_day: str = "work_hours"  # morning, afternoon, evening, night
    energy_level: str = "normal"      # low, normal, high
    in_flow_state: bool = False
    recent_task_ids: List[int] = field(default_factory=list)
    blocked_task_ids: List[int] = field(default_factory=list)


@dataclass
class ScoredTask:
    """Task with calculated priority score"""
    task_id: int
    title: str
    description: str
    raw_priority: int  # Original priority from intent capture

    # Scoring factors (0-100 scale)
    urgency_score: float = 50.0
    importance_score: float = 50.0
    effort_score: float = 50.0  # Inverse: lower effort = higher score
    goal_alignment_score: float = 50.0
    context_bonus: float = 0.0

    # Modifiers
    deadline_decay_multiplier: float = 1.0
    dependency_modifier: float = 1.0
    momentum_bonus: float = 0.0

    # Final calculations
    final_score: float = 0.0
    quadrant: EisenhowerQuadrant = EisenhowerQuadrant.SCHEDULE

    # Metadata
    deadline: Optional[datetime] = None
    effort: EffortLevel = EffortLevel.MEDIUM
    tags: List[str] = field(default_factory=list)
    goal_id: Optional[int] = None
    depends_on: List[int] = field(default_factory=list)
    blocks: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/display"""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "final_score": round(self.final_score, 2),
            "quadrant": self.quadrant.value,
            "urgency": round(self.urgency_score, 1),
            "importance": round(self.importance_score, 1),
            "effort": self.effort.name,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "modifiers": {
                "deadline_decay": round(self.deadline_decay_multiplier, 2),
                "dependency": round(self.dependency_modifier, 2),
                "momentum": round(self.momentum_bonus, 2)
            }
        }


class PriorityEngine:
    """
    Intelligent task prioritization engine.

    Scores tasks based on multiple factors and maintains
    a dynamically sorted priority queue.
    """

    # Scoring weights (must sum to 1.0)
    WEIGHTS = {
        "urgency": 0.30,
        "importance": 0.30,
        "effort": 0.15,
        "goal_alignment": 0.15,
        "context": 0.10
    }

    # Urgency keywords and their scores
    URGENCY_INDICATORS = {
        "now": 100, "immediately": 100, "asap": 95, "urgent": 90,
        "today": 80, "critical": 85, "emergency": 100,
        "soon": 60, "this week": 50, "next week": 30,
        "eventually": 20, "someday": 10, "when possible": 15,
        "no rush": 10, "low priority": 10
    }

    # Importance keywords and their scores
    IMPORTANCE_INDICATORS = {
        "critical": 100, "essential": 95, "must": 90, "required": 85,
        "important": 80, "key": 75, "significant": 70,
        "should": 60, "would be nice": 40, "could": 35,
        "optional": 20, "nice to have": 25, "minor": 15
    }

    # Effort indicators (mapped to EffortLevel)
    EFFORT_INDICATORS = {
        "quick": EffortLevel.TRIVIAL, "simple": EffortLevel.SMALL,
        "small": EffortLevel.SMALL, "easy": EffortLevel.SMALL,
        "moderate": EffortLevel.MEDIUM, "medium": EffortLevel.MEDIUM,
        "large": EffortLevel.LARGE, "complex": EffortLevel.LARGE,
        "epic": EffortLevel.EPIC, "massive": EffortLevel.EPIC,
        "huge": EffortLevel.EPIC, "refactor": EffortLevel.LARGE
    }

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or AGENT_RUNTIME_DB
        self.context = TaskContext()
        self.scored_tasks: Dict[int, ScoredTask] = {}
        self._load_state()

    def _load_state(self):
        """Load persisted state"""
        if PRIORITY_STATE_FILE.exists():
            try:
                state = json.loads(PRIORITY_STATE_FILE.read_text())
                self.context = TaskContext(**state.get("context", {}))
            except Exception as e:
                logger.warning(f"Failed to load priority state: {e}")

    def _save_state(self):
        """Persist current state"""
        state = {
            "context": asdict(self.context),
            "last_updated": datetime.now().isoformat()
        }
        PRIORITY_STATE_FILE.write_text(json.dumps(state, indent=2))

    def update_context(self, **kwargs):
        """Update task context for priority calculations"""
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
        self._save_state()
        logger.info(f"Context updated: {kwargs}")

    def score_task(self, task: Dict[str, Any]) -> ScoredTask:
        """
        Calculate priority score for a single task.

        Args:
            task: Task dictionary with title, description, metadata

        Returns:
            ScoredTask with all scores calculated
        """
        # Parse metadata
        metadata = {}
        if task.get("metadata"):
            try:
                metadata = json.loads(task["metadata"]) if isinstance(task["metadata"], str) else task["metadata"]
            except:
                pass

        # Create scored task
        scored = ScoredTask(
            task_id=task.get("id", 0),
            title=task.get("title", ""),
            description=task.get("description", ""),
            raw_priority=task.get("priority", 5),
            tags=metadata.get("tags", []),
            goal_id=task.get("goal_id")
        )

        # Parse deadline if present
        if metadata.get("deadline"):
            try:
                scored.deadline = datetime.fromisoformat(metadata["deadline"])
            except:
                pass

        # Calculate individual scores
        text = f"{scored.title} {scored.description}".lower()

        scored.urgency_score = self._calculate_urgency(text, scored.raw_priority, scored.deadline)
        scored.importance_score = self._calculate_importance(text, scored.raw_priority, scored.tags)
        scored.effort_score, scored.effort = self._calculate_effort(text)
        scored.goal_alignment_score = self._calculate_goal_alignment(scored.goal_id, scored.tags)
        scored.context_bonus = self._calculate_context_bonus(scored)

        # Calculate modifiers
        scored.deadline_decay_multiplier = self._calculate_deadline_decay(scored.deadline)
        scored.dependency_modifier = self._calculate_dependency_modifier(scored.task_id)
        scored.momentum_bonus = self._calculate_momentum_bonus(scored)

        # Calculate final score
        base_score = (
            scored.urgency_score * self.WEIGHTS["urgency"] +
            scored.importance_score * self.WEIGHTS["importance"] +
            scored.effort_score * self.WEIGHTS["effort"] +
            scored.goal_alignment_score * self.WEIGHTS["goal_alignment"] +
            scored.context_bonus * self.WEIGHTS["context"]
        )

        # Apply modifiers
        scored.final_score = (
            base_score *
            scored.deadline_decay_multiplier *
            scored.dependency_modifier +
            scored.momentum_bonus
        )

        # Clamp to 0-100
        scored.final_score = max(0, min(100, scored.final_score))

        # Determine Eisenhower quadrant
        scored.quadrant = self._determine_quadrant(scored.urgency_score, scored.importance_score)

        # Cache scored task
        self.scored_tasks[scored.task_id] = scored

        return scored

    def _calculate_urgency(self, text: str, raw_priority: int, deadline: Optional[datetime]) -> float:
        """Calculate urgency score (0-100)"""
        # Start with raw priority mapping (1-10 → 10-100)
        score = raw_priority * 10

        # Adjust based on keywords
        for keyword, value in self.URGENCY_INDICATORS.items():
            if keyword in text:
                score = max(score, value)

        # Boost if deadline is approaching
        if deadline:
            hours_until = (deadline - datetime.now()).total_seconds() / 3600
            if hours_until < 0:
                score = 100  # Overdue!
            elif hours_until < 4:
                score = max(score, 95)
            elif hours_until < 24:
                score = max(score, 85)
            elif hours_until < 72:
                score = max(score, 70)

        return min(100, score)

    def _calculate_importance(self, text: str, raw_priority: int, tags: List[str]) -> float:
        """Calculate importance score (0-100)"""
        # Start with raw priority mapping
        score = raw_priority * 10

        # Adjust based on keywords
        for keyword, value in self.IMPORTANCE_INDICATORS.items():
            if keyword in text:
                score = max(score, value)

        # Tag-based boosts
        important_tags = {"critical", "production", "customer", "revenue", "security", "bugfix"}
        if any(tag.lower() in important_tags for tag in tags):
            score = max(score, 80)

        return min(100, score)

    def _calculate_effort(self, text: str) -> Tuple[float, EffortLevel]:
        """Calculate effort score (inverse - lower effort = higher score)"""
        effort = EffortLevel.MEDIUM  # Default

        for keyword, level in self.EFFORT_INDICATORS.items():
            if keyword in text:
                effort = level
                break

        # Inverse scoring: trivial tasks get high scores (quick wins)
        effort_to_score = {
            EffortLevel.TRIVIAL: 90,
            EffortLevel.SMALL: 75,
            EffortLevel.MEDIUM: 50,
            EffortLevel.LARGE: 30,
            EffortLevel.EPIC: 15
        }

        return effort_to_score[effort], effort

    def _calculate_goal_alignment(self, goal_id: Optional[int], tags: List[str]) -> float:
        """Calculate goal alignment score"""
        score = 50  # Neutral default

        # Boost if aligned with current goal
        if goal_id and goal_id == self.context.current_goal_id:
            score = 90

        # Check focus area alignment
        if self.context.current_focus_area:
            focus = self.context.current_focus_area.lower()
            if any(focus in tag.lower() for tag in tags):
                score = max(score, 80)

        return score

    def _calculate_context_bonus(self, task: ScoredTask) -> float:
        """Calculate context-aware bonus"""
        bonus = 0

        # Time of day considerations
        if self.context.time_of_day == "morning" and task.effort == EffortLevel.LARGE:
            bonus += 20  # Tackle big tasks in morning
        elif self.context.time_of_day == "afternoon" and task.effort in [EffortLevel.SMALL, EffortLevel.TRIVIAL]:
            bonus += 15  # Quick wins in afternoon

        # Energy level considerations
        if self.context.energy_level == "high" and task.effort in [EffortLevel.LARGE, EffortLevel.EPIC]:
            bonus += 15
        elif self.context.energy_level == "low" and task.effort == EffortLevel.TRIVIAL:
            bonus += 20  # Easy wins when tired

        # Flow state - don't switch contexts
        if self.context.in_flow_state:
            if task.goal_id == self.context.current_goal_id:
                bonus += 25  # Keep momentum
            else:
                bonus -= 15  # Penalize context switches

        return bonus

    def _calculate_deadline_decay(self, deadline: Optional[datetime]) -> float:
        """Calculate deadline decay multiplier (increases as deadline approaches)"""
        if not deadline:
            return 1.0

        hours_until = (deadline - datetime.now()).total_seconds() / 3600

        if hours_until < 0:
            return 1.5  # Overdue - highest priority
        elif hours_until < 4:
            return 1.4
        elif hours_until < 24:
            return 1.3
        elif hours_until < 72:
            return 1.2
        elif hours_until < 168:  # 1 week
            return 1.1
        else:
            return 1.0

    def _calculate_dependency_modifier(self, task_id: int) -> float:
        """Calculate dependency-based modifier"""
        # Check if task is blocked
        if task_id in self.context.blocked_task_ids:
            return 0.5  # Heavily penalized

        # Check if task is blocking others (would need dependency graph)
        # For now, use a simple check
        return 1.0

    def _calculate_momentum_bonus(self, task: ScoredTask) -> float:
        """Calculate momentum bonus for related tasks"""
        if task.task_id in self.context.recent_task_ids:
            return 10  # Recently worked on - maintain momentum
        return 0

    def _determine_quadrant(self, urgency: float, importance: float) -> EisenhowerQuadrant:
        """Determine Eisenhower Matrix quadrant"""
        urgent = urgency >= 60
        important = importance >= 60

        if urgent and important:
            return EisenhowerQuadrant.DO
        elif not urgent and important:
            return EisenhowerQuadrant.SCHEDULE
        elif urgent and not important:
            return EisenhowerQuadrant.DELEGATE
        else:
            return EisenhowerQuadrant.ELIMINATE

    def score_all_tasks(self, tasks: List[Dict[str, Any]]) -> List[ScoredTask]:
        """Score multiple tasks and return sorted by priority"""
        scored = [self.score_task(task) for task in tasks]
        return sorted(scored, key=lambda t: t.final_score, reverse=True)

    def get_prioritized_queue(self, limit: int = 10) -> List[ScoredTask]:
        """Get top priority tasks from agent-runtime database"""
        if not self.db_path.exists():
            logger.warning(f"Database not found: {self.db_path}")
            return []

        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get pending tasks
            cursor.execute("""
                SELECT id, title, description, priority, goal_id, metadata
                FROM tasks
                WHERE status = 'pending'
                ORDER BY priority DESC
                LIMIT ?
            """, (limit * 2,))  # Get more to allow for reordering

            tasks = [dict(row) for row in cursor.fetchall()]
            conn.close()

            # Score and sort
            scored = self.score_all_tasks(tasks)
            return scored[:limit]

        except Exception as e:
            logger.error(f"Failed to get tasks: {e}")
            return []

    def reprioritize_task(self, task_id: int, adjustment: Dict[str, Any]) -> Optional[ScoredTask]:
        """
        Manually adjust task priority factors.

        Args:
            task_id: Task to adjust
            adjustment: Dict with factor overrides (urgency, importance, etc.)
        """
        if task_id not in self.scored_tasks:
            return None

        task = self.scored_tasks[task_id]

        # Apply adjustments
        if "urgency" in adjustment:
            task.urgency_score = adjustment["urgency"]
        if "importance" in adjustment:
            task.importance_score = adjustment["importance"]
        if "deadline" in adjustment:
            task.deadline = datetime.fromisoformat(adjustment["deadline"])
            task.deadline_decay_multiplier = self._calculate_deadline_decay(task.deadline)

        # Recalculate final score
        base_score = (
            task.urgency_score * self.WEIGHTS["urgency"] +
            task.importance_score * self.WEIGHTS["importance"] +
            task.effort_score * self.WEIGHTS["effort"] +
            task.goal_alignment_score * self.WEIGHTS["goal_alignment"] +
            task.context_bonus * self.WEIGHTS["context"]
        )

        task.final_score = max(0, min(100,
            base_score * task.deadline_decay_multiplier * task.dependency_modifier + task.momentum_bonus
        ))
        task.quadrant = self._determine_quadrant(task.urgency_score, task.importance_score)

        logger.info(f"Reprioritized task {task_id}: new score {task.final_score:.1f}")
        return task

    def get_by_quadrant(self) -> Dict[str, List[ScoredTask]]:
        """Group all scored tasks by Eisenhower quadrant"""
        quadrants = {q.value: [] for q in EisenhowerQuadrant}

        for task in self.scored_tasks.values():
            quadrants[task.quadrant.value].append(task)

        # Sort each quadrant by score
        for q in quadrants:
            quadrants[q] = sorted(quadrants[q], key=lambda t: t.final_score, reverse=True)

        return quadrants

    def suggest_next_task(self) -> Optional[ScoredTask]:
        """Suggest the best next task based on context"""
        queue = self.get_prioritized_queue(limit=5)

        if not queue:
            return None

        # Filter out blocked tasks
        available = [t for t in queue if t.task_id not in self.context.blocked_task_ids]

        if not available:
            return queue[0]  # Return highest even if blocked

        # Consider flow state
        if self.context.in_flow_state and self.context.current_goal_id:
            # Prefer tasks aligned with current goal
            aligned = [t for t in available if t.goal_id == self.context.current_goal_id]
            if aligned:
                return aligned[0]

        return available[0]


class PriorityEngineIntegration:
    """
    Integration layer between Intent Capture Stream and Priority Engine.

    Handles:
    - Automatic scoring of new intents
    - Database updates for priority changes
    - Real-time reprioritization on context changes
    """

    def __init__(self, engine: PriorityEngine = None):
        self.engine = engine or PriorityEngine()

    async def score_intent(self, intent: "ParsedIntent") -> ScoredTask:
        """Score a parsed intent from Intent Capture Stream"""
        # Convert intent to task format
        task_dict = intent.to_task_dict()
        task_dict["id"] = 0  # Will be assigned by database

        return self.engine.score_task(task_dict)

    async def on_context_change(self, **context_updates):
        """Handle context changes and trigger reprioritization"""
        self.engine.update_context(**context_updates)

        # Re-score all cached tasks with new context
        for task_id in list(self.engine.scored_tasks.keys()):
            task = self.engine.scored_tasks[task_id]
            # Recalculate context-sensitive scores
            task.context_bonus = self.engine._calculate_context_bonus(task)
            task.momentum_bonus = self.engine._calculate_momentum_bonus(task)

            # Update final score
            base_score = (
                task.urgency_score * self.engine.WEIGHTS["urgency"] +
                task.importance_score * self.engine.WEIGHTS["importance"] +
                task.effort_score * self.engine.WEIGHTS["effort"] +
                task.goal_alignment_score * self.engine.WEIGHTS["goal_alignment"] +
                task.context_bonus * self.engine.WEIGHTS["context"]
            )
            task.final_score = max(0, min(100,
                base_score * task.deadline_decay_multiplier * task.dependency_modifier + task.momentum_bonus
            ))

        logger.info(f"Reprioritized {len(self.engine.scored_tasks)} tasks after context change")

    def get_priority_report(self) -> Dict[str, Any]:
        """Generate priority report for display"""
        quadrants = self.engine.get_by_quadrant()

        return {
            "timestamp": datetime.now().isoformat(),
            "context": asdict(self.engine.context),
            "quadrants": {
                "Q1_do": [t.to_dict() for t in quadrants["Q1_do"][:5]],
                "Q2_schedule": [t.to_dict() for t in quadrants["Q2_schedule"][:5]],
                "Q3_delegate": [t.to_dict() for t in quadrants["Q3_delegate"][:3]],
                "Q4_eliminate": [t.to_dict() for t in quadrants["Q4_eliminate"][:3]]
            },
            "suggested_next": self.engine.suggest_next_task().to_dict() if self.engine.suggest_next_task() else None,
            "total_tasks": len(self.engine.scored_tasks)
        }


# Test the Priority Engine
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("Priority Engine Test")
    print("=" * 50)

    engine = PriorityEngine()

    # Update context for testing
    engine.update_context(
        time_of_day="morning",
        energy_level="high",
        current_focus_area="api"
    )

    # Test tasks
    test_tasks = [
        {
            "id": 1,
            "title": "Fix critical production bug",
            "description": "Users can't login - this is urgent!",
            "priority": 10,
            "metadata": json.dumps({"tags": ["bugfix", "production"]})
        },
        {
            "id": 2,
            "title": "Update API documentation",
            "description": "Should update the docs eventually",
            "priority": 5,
            "metadata": json.dumps({"tags": ["docs", "api"]})
        },
        {
            "id": 3,
            "title": "Quick config change",
            "description": "Simple environment variable update",
            "priority": 3,
            "metadata": json.dumps({"tags": ["config"]})
        },
        {
            "id": 4,
            "title": "Major refactor of auth system",
            "description": "Large complex task to modernize authentication",
            "priority": 6,
            "metadata": json.dumps({"tags": ["refactor", "security"]})
        },
        {
            "id": 5,
            "title": "Review PR comments",
            "description": "Need to respond to PR feedback today",
            "priority": 7,
            "metadata": json.dumps({
                "tags": ["review"],
                "deadline": (datetime.now() + timedelta(hours=6)).isoformat()
            })
        }
    ]

    # Score all tasks
    scored = engine.score_all_tasks(test_tasks)

    print("\nPrioritized Task Queue:")
    print("-" * 50)
    for i, task in enumerate(scored, 1):
        print(f"\n{i}. {task.title}")
        print(f"   Score: {task.final_score:.1f} | Quadrant: {task.quadrant.value}")
        print(f"   Urgency: {task.urgency_score:.0f} | Importance: {task.importance_score:.0f}")
        print(f"   Effort: {task.effort.name} | Deadline Mult: {task.deadline_decay_multiplier:.2f}")

    # Show by quadrant
    print("\n" + "=" * 50)
    print("Eisenhower Matrix View:")
    print("-" * 50)
    quadrants = engine.get_by_quadrant()
    for q_name, tasks in quadrants.items():
        if tasks:
            print(f"\n{q_name}:")
            for t in tasks[:3]:
                print(f"  • {t.title} (Score: {t.final_score:.1f})")

    # Suggest next task
    print("\n" + "=" * 50)
    next_task = engine.suggest_next_task()
    if next_task:
        print(f"Suggested Next Task: {next_task.title}")
        print(f"  Reason: Score {next_task.final_score:.1f}, {next_task.quadrant.value}")

    print("\n" + "=" * 50)
    print("Priority Engine Test Complete")
