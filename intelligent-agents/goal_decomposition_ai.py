#!/usr/bin/env python3
"""
Goal Decomposition AI for AGI System
====================================

Parses natural language goals into hierarchical executable tasks with
dependencies, priorities, and success criteria. Enables autonomous goal
achievement through intelligent task planning.

Key Capabilities:
- Natural language goal parsing
- Hierarchical task decomposition
- Dependency graph generation
- Success criteria definition
- Task prioritization
- Adaptive replanning

Integration:
- Agent Runtime MCP for persistent task storage
- Multi-Agent Coordinator for task execution
- Meta-Learning Engine for optimization
"""

import asyncio
import json
import logging
import os
import platform
import re
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        macos_primary = Path("/Volumes/SSDRAID0/agentic-system")
        macos_fallback = Path("/Volumes/FILES/agentic-system")
        if macos_primary.exists():
            return macos_primary
        elif macos_fallback.exists():
            return macos_fallback
    elif system == "Linux":
        linux_primary = Path("/home/marc/agentic-system")
        linux_fallback = Path("/mnt/agentic-system")
        if linux_primary.exists():
            return linux_primary
        elif linux_fallback.exists():
            return linux_fallback
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

# Database path
DB_PATH = _STORAGE_BASE / "databases/goal_decomposition.db"


class TaskType(Enum):
    """Task type classification"""
    RESEARCH = "research"
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    DOCUMENTATION = "documentation"
    VALIDATION = "validation"


class Priority(Enum):
    """Task priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    OPTIONAL = 5


@dataclass
class Task:
    """Executable task definition"""
    task_id: str
    goal_id: str
    parent_task_id: Optional[str]
    title: str
    description: str
    task_type: TaskType
    priority: Priority
    dependencies: List[str]
    success_criteria: List[str]
    estimated_duration_minutes: int
    assigned_agent: Optional[str]
    status: str
    created_at: datetime


@dataclass
class Goal:
    """High-level goal definition"""
    goal_id: str
    description: str
    context: Dict
    success_metrics: List[str]
    constraints: List[str]
    deadline: Optional[datetime]
    created_at: datetime
    completed_at: Optional[datetime]


class GoalDecompositionAI:
    """
    AI system for decomposing natural language goals into executable
    task hierarchies with dependencies and success criteria.
    """

    def __init__(self, db_path: Path = DB_PATH):
        """Initialize goal decomposition AI"""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

        # Pattern library for task identification
        self._init_patterns()

    def _init_database(self):
        """Initialize goal decomposition database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Goals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                goal_id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                context TEXT NOT NULL,
                success_metrics TEXT NOT NULL,
                constraints TEXT NOT NULL,
                deadline TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)

        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                parent_task_id TEXT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                task_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                dependencies TEXT NOT NULL,
                success_criteria TEXT NOT NULL,
                estimated_duration_minutes INTEGER NOT NULL,
                assigned_agent TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (goal_id) REFERENCES goals(goal_id)
            )
        """)

        # Decomposition patterns table (learned patterns)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decomposition_patterns (
                pattern_id TEXT PRIMARY KEY,
                goal_pattern TEXT NOT NULL,
                task_template TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                confidence REAL DEFAULT 0.5,
                created_at TEXT NOT NULL,
                last_used TEXT
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_goal_id ON tasks(goal_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_parent_task ON tasks(parent_task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")

        conn.commit()
        conn.close()

    def _init_patterns(self):
        """Initialize task decomposition patterns"""
        self.patterns = {
            # Implementation patterns
            r"implement|build|create|develop": [
                ("Research requirements and constraints", TaskType.RESEARCH, Priority.HIGH),
                ("Design architecture and components", TaskType.DESIGN, Priority.HIGH),
                ("Implement core functionality", TaskType.IMPLEMENTATION, Priority.CRITICAL),
                ("Write unit tests", TaskType.TESTING, Priority.HIGH),
                ("Integration testing", TaskType.TESTING, Priority.MEDIUM),
                ("Documentation", TaskType.DOCUMENTATION, Priority.MEDIUM),
                ("Deploy to production", TaskType.DEPLOYMENT, Priority.LOW)
            ],

            # Research patterns
            r"research|investigate|analyze": [
                ("Define research questions", TaskType.RESEARCH, Priority.HIGH),
                ("Gather relevant information", TaskType.RESEARCH, Priority.HIGH),
                ("Analyze findings", TaskType.RESEARCH, Priority.MEDIUM),
                ("Document conclusions", TaskType.DOCUMENTATION, Priority.MEDIUM),
                ("Present recommendations", TaskType.VALIDATION, Priority.LOW)
            ],

            # Refactoring patterns
            r"refactor|improve|optimize": [
                ("Identify problem areas", TaskType.RESEARCH, Priority.HIGH),
                ("Design improvements", TaskType.DESIGN, Priority.HIGH),
                ("Implement changes", TaskType.IMPLEMENTATION, Priority.CRITICAL),
                ("Run regression tests", TaskType.TESTING, Priority.CRITICAL),
                ("Measure performance improvement", TaskType.VALIDATION, Priority.MEDIUM),
                ("Update documentation", TaskType.DOCUMENTATION, Priority.LOW)
            ],

            # Debugging patterns
            r"fix|debug|resolve": [
                ("Reproduce the issue", TaskType.RESEARCH, Priority.CRITICAL),
                ("Identify root cause", TaskType.RESEARCH, Priority.CRITICAL),
                ("Design fix", TaskType.DESIGN, Priority.HIGH),
                ("Implement fix", TaskType.IMPLEMENTATION, Priority.CRITICAL),
                ("Test fix thoroughly", TaskType.TESTING, Priority.CRITICAL),
                ("Deploy fix", TaskType.DEPLOYMENT, Priority.HIGH)
            ],

            # Documentation patterns
            r"document|write docs": [
                ("Gather information to document", TaskType.RESEARCH, Priority.HIGH),
                ("Structure documentation", TaskType.DESIGN, Priority.MEDIUM),
                ("Write content", TaskType.DOCUMENTATION, Priority.HIGH),
                ("Review and edit", TaskType.VALIDATION, Priority.MEDIUM),
                ("Publish documentation", TaskType.DEPLOYMENT, Priority.LOW)
            ]
        }

    def parse_goal(self, goal_description: str, context: Optional[Dict] = None) -> Goal:
        """Parse a natural language goal into structured format"""
        goal = Goal(
            goal_id=str(uuid.uuid4()),
            description=goal_description,
            context=context or {},
            success_metrics=self._extract_success_metrics(goal_description),
            constraints=self._extract_constraints(goal_description),
            deadline=self._extract_deadline(goal_description),
            created_at=datetime.now(),
            completed_at=None
        )

        # Save goal
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO goals
            (goal_id, description, context, success_metrics, constraints,
             deadline, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            goal.goal_id,
            goal.description,
            json.dumps(goal.context),
            json.dumps(goal.success_metrics),
            json.dumps(goal.constraints),
            goal.deadline.isoformat() if goal.deadline else None,
            goal.created_at.isoformat(),
            None
        ))

        conn.commit()
        conn.close()

        logger.info(f"Parsed goal: {goal.goal_id} - {goal.description}")

        return goal

    def _extract_success_metrics(self, goal_description: str) -> List[str]:
        """Extract success criteria from goal description"""
        metrics = []

        # Look for explicit success criteria
        if "success when" in goal_description.lower():
            parts = goal_description.lower().split("success when")[1]
            metrics.append(parts.strip())
        elif "until" in goal_description.lower():
            parts = goal_description.lower().split("until")[1]
            metrics.append(f"Complete when {parts.strip()}")

        # Default metric
        if not metrics:
            metrics.append("Task completed successfully with no errors")

        return metrics

    def _extract_constraints(self, goal_description: str) -> List[str]:
        """Extract constraints from goal description"""
        constraints = []

        # Look for constraint keywords
        constraint_patterns = [
            (r"without (\w+)", "Must not use: {}"),
            (r"using (\w+)", "Must use: {}"),
            (r"within (\d+\s+\w+)", "Time constraint: {}"),
            (r"budget[:\s]+\$?([\d,]+)", "Budget constraint: ${}"),
        ]

        for pattern, template in constraint_patterns:
            matches = re.findall(pattern, goal_description, re.IGNORECASE)
            for match in matches:
                constraints.append(template.format(match))

        return constraints

    def _extract_deadline(self, goal_description: str) -> Optional[datetime]:
        """Extract deadline from goal description"""
        # Simplified - would use NLP for proper date extraction
        deadline_patterns = [
            r"by (\w+ \d+)",
            r"deadline[:\s]+(\w+ \d+)",
            r"due (\w+ \d+)",
        ]

        for pattern in deadline_patterns:
            match = re.search(pattern, goal_description, re.IGNORECASE)
            if match:
                # Would parse date properly here
                logger.info(f"Found deadline: {match.group(1)}")

        return None

    def decompose_goal(self, goal: Goal) -> List[Task]:
        """
        Decompose a goal into executable tasks.

        Uses pattern matching and learned decomposition strategies.
        """
        # Match goal to patterns
        matched_pattern = None
        for pattern_regex, task_templates in self.patterns.items():
            if re.search(pattern_regex, goal.description, re.IGNORECASE):
                matched_pattern = task_templates
                break

        if not matched_pattern:
            # Default: single task
            matched_pattern = [
                (goal.description, TaskType.IMPLEMENTATION, Priority.HIGH)
            ]

        # Generate tasks from template
        tasks = []
        prev_task_id = None

        for i, (title, task_type, priority) in enumerate(matched_pattern):
            task = Task(
                task_id=str(uuid.uuid4()),
                goal_id=goal.goal_id,
                parent_task_id=None,
                title=title,
                description=f"{title} for: {goal.description}",
                task_type=task_type,
                priority=priority,
                dependencies=[prev_task_id] if prev_task_id else [],
                success_criteria=self._generate_success_criteria(title, task_type),
                estimated_duration_minutes=self._estimate_duration(task_type),
                assigned_agent=None,
                status="pending",
                created_at=datetime.now()
            )

            tasks.append(task)
            prev_task_id = task.task_id

        # Save tasks
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for task in tasks:
            cursor.execute("""
                INSERT INTO tasks
                (task_id, goal_id, parent_task_id, title, description,
                 task_type, priority, dependencies, success_criteria,
                 estimated_duration_minutes, assigned_agent, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id,
                task.goal_id,
                task.parent_task_id,
                task.title,
                task.description,
                task.task_type.value,
                task.priority.value,
                json.dumps(task.dependencies),
                json.dumps(task.success_criteria),
                task.estimated_duration_minutes,
                task.assigned_agent,
                task.status,
                task.created_at.isoformat()
            ))

        conn.commit()
        conn.close()

        logger.info(f"Decomposed goal {goal.goal_id} into {len(tasks)} tasks")

        return tasks

    def _generate_success_criteria(self, title: str, task_type: TaskType) -> List[str]:
        """Generate success criteria for a task"""
        criteria = [f"'{title}' completed successfully"]

        if task_type == TaskType.IMPLEMENTATION:
            criteria.extend([
                "Code passes all linting checks",
                "No critical security vulnerabilities"
            ])
        elif task_type == TaskType.TESTING:
            criteria.extend([
                "All tests pass",
                "Code coverage >= 80%"
            ])
        elif task_type == TaskType.DOCUMENTATION:
            criteria.extend([
                "Documentation is clear and comprehensive",
                "All code examples are tested"
            ])

        return criteria

    def _estimate_duration(self, task_type: TaskType) -> int:
        """Estimate task duration in minutes"""
        duration_map = {
            TaskType.RESEARCH: 60,
            TaskType.DESIGN: 90,
            TaskType.IMPLEMENTATION: 120,
            TaskType.TESTING: 60,
            TaskType.DEPLOYMENT: 30,
            TaskType.DOCUMENTATION: 45,
            TaskType.VALIDATION: 30
        }

        return duration_map.get(task_type, 60)

    def get_goal_progress(self, goal_id: str) -> Dict:
        """Get progress for a goal"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get tasks for goal
        cursor.execute("""
            SELECT COUNT(*), status
            FROM tasks
            WHERE goal_id = ?
            GROUP BY status
        """, (goal_id,))

        status_counts = {}
        total_tasks = 0

        for count, status in cursor.fetchall():
            status_counts[status] = count
            total_tasks = total_tasks + count

        completed = status_counts.get("completed", 0)
        progress = (completed / total_tasks * 100) if total_tasks > 0 else 0

        conn.close()

        return {
            "goal_id": goal_id,
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "progress_percentage": progress,
            "status_breakdown": status_counts
        }

    async def execute_goal(self, goal_description: str, context: Optional[Dict] = None) -> Dict:
        """
        Full pipeline: parse goal, decompose into tasks, and prepare for execution.
        """
        # Parse goal
        goal = self.parse_goal(goal_description, context)

        # Decompose into tasks
        tasks = self.decompose_goal(goal)

        # Get execution plan
        execution_order = self._determine_execution_order(tasks)

        return {
            "goal_id": goal.goal_id,
            "goal_description": goal.description,
            "total_tasks": len(tasks),
            "execution_order": [t.task_id for t in execution_order],
            "task_details": [asdict(t) for t in tasks],
            "estimated_total_duration_minutes": sum(t.estimated_duration_minutes for t in tasks)
        }

    def _determine_execution_order(self, tasks: List[Task]) -> List[Task]:
        """Determine optimal execution order respecting dependencies"""
        # Topological sort based on dependencies
        in_degree = {task.task_id: len(task.dependencies) for task in tasks}
        task_map = {task.task_id: task for task in tasks}
        result = []

        # Find tasks with no dependencies
        queue = [task for task in tasks if len(task.dependencies) == 0]

        while queue:
            # Sort by priority
            queue.sort(key=lambda t: t.priority.value)
            current = queue.pop(0)
            result.append(current)

            # Find dependent tasks
            for task in tasks:
                if current.task_id in task.dependencies:
                    in_degree[task.task_id] = in_degree[task.task_id] - 1
                    if in_degree[task.task_id] == 0:
                        queue.append(task)

        return result


async def main():
    """Demo of goal decomposition AI"""
    ai = GoalDecompositionAI()

    # Test goal decomposition
    goal_description = "Implement user authentication system with JWT tokens using Python and FastAPI"

    result = await ai.execute_goal(goal_description, context={"language": "Python"})

    print("\nGoal Decomposition Result:")
    print(json.dumps(result, indent=2, default=str))

    # Progress
    progress = ai.get_goal_progress(result["goal_id"])
    print("\nGoal Progress:")
    print(json.dumps(progress, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
