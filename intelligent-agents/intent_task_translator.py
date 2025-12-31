#!/usr/bin/env python3
"""
Intent→Task Translator - Complex Intent Decomposition for Always-On Orchestration

Part of the Translation Layer (Nate B Jones framework):
- Intent Capture Stream → Priority Engine → **Intent→Task Translator** → Execution

Responsibilities:
┌─────────────────────────────────────────────────────────────────┐
│                    INTENT→TASK TRANSLATOR                        │
├─────────────────────────────────────────────────────────────────┤
│  Complex Intent        Decomposition         Task Graph          │
│  ─────────────         ─────────────         ──────────          │
│  • Multi-step    ───►  • Break down    ───►  • Dependencies      │
│  • Compound      ───►  • Identify deps ───►  • Hierarchy         │
│  • Vague         ───►  • Match templates     • Priorities        │
└─────────────────────────────────────────────────────────────────┘

Features:
1. Complex intent decomposition into atomic tasks
2. Dependency detection and ordering
3. Workflow template matching for common patterns
4. Goal/task hierarchy creation
5. Priority Engine integration for scoring

Status: Phase 2 (Active Translation)
"""

import asyncio
import json
import logging
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum

# Configure logging
logger = logging.getLogger("intent-translator")

# Import dependencies
try:
    from intent_capture_stream import ParsedIntent, IntentCategory, PriorityLevel
    INTENT_CAPTURE_AVAILABLE = True
except ImportError:
    INTENT_CAPTURE_AVAILABLE = False

try:
    from priority_engine import PriorityEngine, ScoredTask
    PRIORITY_ENGINE_AVAILABLE = True
except ImportError:
    PRIORITY_ENGINE_AVAILABLE = False

# Configuration
AGENT_RUNTIME_DB = Path.home() / ".claude" / "agent_runtime.db"
TRANSLATOR_STATE_FILE = Path("/tmp/intent_translator_state.json")


class TaskRelation(Enum):
    """Relationship types between tasks"""
    BLOCKS = "blocks"           # This task blocks another
    BLOCKED_BY = "blocked_by"   # This task is blocked by another
    PARENT = "parent"           # This is a parent task
    CHILD = "child"             # This is a subtask
    RELATED = "related"         # Loosely related tasks


class DecompositionStrategy(Enum):
    """Strategies for breaking down intents"""
    SEQUENTIAL = "sequential"   # Tasks in order, each depends on previous
    PARALLEL = "parallel"       # Tasks can run simultaneously
    HIERARCHICAL = "hierarchical"  # Parent goal with child tasks
    TEMPLATE = "template"       # Match to known workflow template


@dataclass
class TaskNode:
    """A single task in the task graph"""
    id: Optional[int] = None
    title: str = ""
    description: str = ""
    priority: int = 5
    effort_estimate: str = "medium"  # trivial, small, medium, large, epic

    # Relationships
    depends_on: List[int] = field(default_factory=list)
    blocks: List[int] = field(default_factory=list)
    parent_id: Optional[int] = None
    children: List[int] = field(default_factory=list)

    # Metadata
    tags: List[str] = field(default_factory=list)
    deadline: Optional[str] = None
    goal_id: Optional[int] = None
    order: int = 0  # Execution order within group

    # Scoring (from Priority Engine)
    priority_score: float = 0.0
    quadrant: str = "Q2_schedule"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "effort": self.effort_estimate,
            "depends_on": self.depends_on,
            "blocks": self.blocks,
            "parent_id": self.parent_id,
            "tags": self.tags,
            "deadline": self.deadline,
            "order": self.order,
            "priority_score": self.priority_score,
            "quadrant": self.quadrant
        }


@dataclass
class TaskGraph:
    """A graph of related tasks with dependencies"""
    goal_title: str
    goal_description: str
    tasks: List[TaskNode] = field(default_factory=list)
    strategy: DecompositionStrategy = DecompositionStrategy.SEQUENTIAL
    template_used: Optional[str] = None

    # Created IDs after persistence
    goal_id: Optional[int] = None
    task_ids: List[int] = field(default_factory=list)

    def get_execution_order(self) -> List[TaskNode]:
        """Return tasks in valid execution order (respecting dependencies)"""
        # Topological sort
        result = []
        visited = set()
        temp_visited = set()

        def visit(task: TaskNode):
            if task.id in temp_visited:
                raise ValueError(f"Circular dependency detected for task: {task.title}")
            if task.id in visited:
                return
            temp_visited.add(task.id)
            for dep_id in task.depends_on:
                dep_task = next((t for t in self.tasks if t.id == dep_id), None)
                if dep_task:
                    visit(dep_task)
            temp_visited.remove(task.id)
            visited.add(task.id)
            result.append(task)

        for task in self.tasks:
            if task.id not in visited:
                visit(task)

        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_title": self.goal_title,
            "goal_description": self.goal_description,
            "goal_id": self.goal_id,
            "strategy": self.strategy.value,
            "template_used": self.template_used,
            "task_count": len(self.tasks),
            "tasks": [t.to_dict() for t in self.tasks],
            "task_ids": self.task_ids
        }


class WorkflowTemplates:
    """
    Common workflow templates for quick decomposition.

    Templates define the standard steps for common intents,
    allowing fast translation without complex analysis.
    """

    TEMPLATES = {
        "deploy_to_production": {
            "trigger_patterns": [
                r"deploy\s+.*\s*to\s+prod(uction)?",
                r"deploy\s+to\s+prod(uction)?",
                r"release\s+.*\s*to\s+prod(uction)?",
                r"ship\s+(it|this|the\s+feature)",
                r"go\s+live",
                r"push\s+to\s+prod(uction)?"
            ],
            "strategy": DecompositionStrategy.SEQUENTIAL,
            "tasks": [
                {"title": "Run full test suite", "effort": "medium", "tags": ["testing"]},
                {"title": "Review pending changes", "effort": "small", "tags": ["review"]},
                {"title": "Create release notes", "effort": "small", "tags": ["docs"]},
                {"title": "Deploy to staging", "effort": "medium", "tags": ["deploy"]},
                {"title": "Smoke test staging", "effort": "small", "tags": ["testing"]},
                {"title": "Deploy to production", "effort": "medium", "tags": ["deploy", "production"]},
                {"title": "Verify production deployment", "effort": "small", "tags": ["verification"]},
                {"title": "Notify stakeholders", "effort": "trivial", "tags": ["communication"]}
            ]
        },
        "implement_feature": {
            "trigger_patterns": [
                r"implement\s+.+\s*feature",
                r"implement\s+(a\s+)?feature",
                r"build\s+.+\s*feature",
                r"build\s+(a\s+)?(new\s+)?feature",
                r"add\s+.+\s*feature",
                r"add\s+(a\s+)?(new\s+)?feature",
                r"create\s+.+\s*feature",
                r"create\s+(a\s+)?(new\s+)?feature"
            ],
            "strategy": DecompositionStrategy.SEQUENTIAL,
            "tasks": [
                {"title": "Define requirements", "effort": "small", "tags": ["planning"]},
                {"title": "Design solution approach", "effort": "medium", "tags": ["design"]},
                {"title": "Implement core functionality", "effort": "large", "tags": ["implementation"]},
                {"title": "Write unit tests", "effort": "medium", "tags": ["testing"]},
                {"title": "Add integration tests", "effort": "medium", "tags": ["testing"]},
                {"title": "Update documentation", "effort": "small", "tags": ["docs"]},
                {"title": "Code review", "effort": "small", "tags": ["review"]},
                {"title": "Deploy and verify", "effort": "medium", "tags": ["deploy"]}
            ]
        },
        "fix_bug": {
            "trigger_patterns": [
                r"fix\s+(the\s+)?.*\s*bug",
                r"fix\s+(the\s+)?bug",
                r"debug\s+(the\s+)?.*\s*(issue|problem)",
                r"resolve\s+(the\s+)?.*\s*(issue|bug|problem)",
                r"troubleshoot",
                r"bug\s+fix"
            ],
            "strategy": DecompositionStrategy.SEQUENTIAL,
            "tasks": [
                {"title": "Reproduce the issue", "effort": "small", "tags": ["investigation"]},
                {"title": "Identify root cause", "effort": "medium", "tags": ["investigation"]},
                {"title": "Implement fix", "effort": "medium", "tags": ["bugfix"]},
                {"title": "Add regression test", "effort": "small", "tags": ["testing"]},
                {"title": "Verify fix works", "effort": "small", "tags": ["verification"]},
                {"title": "Deploy fix", "effort": "small", "tags": ["deploy"]}
            ]
        },
        "refactor_code": {
            "trigger_patterns": [
                r"refactor\s+(the\s+)?",
                r"clean\s+up\s+(the\s+)?code",
                r"improve\s+(the\s+)?code\s+quality",
                r"restructure\s+(the\s+)?"
            ],
            "strategy": DecompositionStrategy.SEQUENTIAL,
            "tasks": [
                {"title": "Analyze current implementation", "effort": "small", "tags": ["analysis"]},
                {"title": "Plan refactoring approach", "effort": "small", "tags": ["planning"]},
                {"title": "Ensure test coverage exists", "effort": "medium", "tags": ["testing"]},
                {"title": "Refactor incrementally", "effort": "large", "tags": ["refactor"]},
                {"title": "Run tests after each change", "effort": "small", "tags": ["testing"]},
                {"title": "Update documentation", "effort": "small", "tags": ["docs"]}
            ]
        },
        "setup_project": {
            "trigger_patterns": [
                r"set\s*up\s+(a\s+)?(new\s+)?.*\s*project",
                r"set\s*up\s+(a\s+)?(new\s+)?project",
                r"create\s+(a\s+)?(new\s+)?.*\s*project",
                r"create\s+(a\s+)?(new\s+)?project",
                r"initialize\s+(a\s+)?(new\s+)?.*\s*project",
                r"bootstrap\s+(a\s+)?(new\s+)?.*\s*project"
            ],
            "strategy": DecompositionStrategy.SEQUENTIAL,
            "tasks": [
                {"title": "Create project structure", "effort": "small", "tags": ["setup"]},
                {"title": "Initialize version control", "effort": "trivial", "tags": ["setup", "git"]},
                {"title": "Set up dependencies", "effort": "medium", "tags": ["setup"]},
                {"title": "Configure development environment", "effort": "medium", "tags": ["setup"]},
                {"title": "Add basic CI/CD", "effort": "medium", "tags": ["setup", "ci"]},
                {"title": "Create initial documentation", "effort": "small", "tags": ["docs"]}
            ]
        },
        "api_endpoint": {
            "trigger_patterns": [
                r"create\s+(an?\s+)?api\s+endpoint",
                r"add\s+(an?\s+)?api\s+endpoint",
                r"implement\s+(an?\s+)?api",
                r"build\s+(an?\s+)?rest\s+api"
            ],
            "strategy": DecompositionStrategy.SEQUENTIAL,
            "tasks": [
                {"title": "Define API contract/schema", "effort": "small", "tags": ["api", "design"]},
                {"title": "Implement endpoint handler", "effort": "medium", "tags": ["api", "implementation"]},
                {"title": "Add input validation", "effort": "small", "tags": ["api", "validation"]},
                {"title": "Implement business logic", "effort": "medium", "tags": ["implementation"]},
                {"title": "Add error handling", "effort": "small", "tags": ["api"]},
                {"title": "Write API tests", "effort": "medium", "tags": ["testing", "api"]},
                {"title": "Document endpoint", "effort": "small", "tags": ["docs", "api"]}
            ]
        },
        "research_topic": {
            "trigger_patterns": [
                r"research\s+",
                r"investigate\s+",
                r"look\s+into\s+",
                r"explore\s+(options|ways|how)"
            ],
            "strategy": DecompositionStrategy.PARALLEL,
            "tasks": [
                {"title": "Define research questions", "effort": "small", "tags": ["research"]},
                {"title": "Gather existing documentation", "effort": "medium", "tags": ["research"]},
                {"title": "Search for prior solutions", "effort": "medium", "tags": ["research"]},
                {"title": "Evaluate options", "effort": "medium", "tags": ["analysis"]},
                {"title": "Summarize findings", "effort": "small", "tags": ["docs"]},
                {"title": "Make recommendation", "effort": "small", "tags": ["decision"]}
            ]
        }
    }

    @classmethod
    def match_template(cls, text: str) -> Optional[Tuple[str, Dict]]:
        """Find matching template for the given text"""
        text_lower = text.lower()

        for template_name, template in cls.TEMPLATES.items():
            for pattern in template["trigger_patterns"]:
                if re.search(pattern, text_lower):
                    return template_name, template

        return None


class IntentDecomposer:
    """
    Decomposes complex intents into atomic tasks.

    Uses multiple strategies:
    1. Template matching for common patterns
    2. Keyword-based decomposition for compound intents
    3. Fallback to single task for simple intents
    """

    # Compound intent indicators
    COMPOUND_INDICATORS = [
        r"\s+and\s+(then\s+)?",
        r"\s+then\s+",
        r"\s+after\s+(that\s+)?",
        r"\s+before\s+",
        r"\s+also\s+",
        r",\s*",
        r";\s*",
        r"\s+plus\s+"
    ]

    # Step indicators
    STEP_PATTERNS = [
        r"^first\s+",
        r"^then\s+",
        r"^next\s+",
        r"^finally\s+",
        r"^after\s+that\s+",
        r"^lastly\s+",
        r"^\d+[\.\)]\s*"
    ]

    # Effort estimation keywords
    EFFORT_KEYWORDS = {
        "trivial": ["quick", "simple", "easy", "just", "minor", "small change"],
        "small": ["small", "little", "brief", "short"],
        "medium": ["moderate", "regular", "standard"],
        "large": ["large", "big", "significant", "major", "complex"],
        "epic": ["huge", "massive", "epic", "complete rewrite", "overhaul"]
    }

    def __init__(self):
        self.priority_engine = None
        if PRIORITY_ENGINE_AVAILABLE:
            self.priority_engine = PriorityEngine()

    def decompose(self, intent_text: str, context: Dict[str, Any] = None) -> TaskGraph:
        """
        Decompose an intent into a task graph.

        Args:
            intent_text: The raw intent text
            context: Additional context (deadline, goal, etc.)

        Returns:
            TaskGraph with all tasks and dependencies
        """
        context = context or {}

        # Try template matching first
        template_match = WorkflowTemplates.match_template(intent_text)
        if template_match:
            template_name, template = template_match
            return self._apply_template(intent_text, template_name, template, context)

        # Check if compound intent
        if self._is_compound(intent_text):
            return self._decompose_compound(intent_text, context)

        # Check for step-based structure
        if self._has_steps(intent_text):
            return self._decompose_steps(intent_text, context)

        # Simple intent - create single task
        return self._create_simple_task(intent_text, context)

    def _is_compound(self, text: str) -> bool:
        """Check if intent is compound (contains multiple tasks)"""
        for pattern in self.COMPOUND_INDICATORS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _has_steps(self, text: str) -> bool:
        """Check if intent contains step-by-step structure"""
        for pattern in self.STEP_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE | re.MULTILINE):
                return True
        return False

    def _estimate_effort(self, text: str) -> str:
        """Estimate effort level from text"""
        text_lower = text.lower()
        for effort, keywords in self.EFFORT_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return effort
        return "medium"

    def _extract_priority(self, text: str) -> int:
        """Extract priority from text"""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ["urgent", "asap", "critical", "immediately"]):
            return 10
        elif any(kw in text_lower for kw in ["important", "high priority", "soon"]):
            return 8
        elif any(kw in text_lower for kw in ["low priority", "eventually", "someday"]):
            return 3
        return 5  # Default medium

    def _apply_template(self, intent_text: str, template_name: str,
                       template: Dict, context: Dict[str, Any]) -> TaskGraph:
        """Apply a workflow template to create task graph"""
        graph = TaskGraph(
            goal_title=self._extract_goal_title(intent_text),
            goal_description=intent_text,
            strategy=template["strategy"],
            template_used=template_name
        )

        # Create tasks from template
        for i, task_def in enumerate(template["tasks"]):
            task = TaskNode(
                id=i + 1,  # Temporary IDs
                title=task_def["title"],
                description=f"Part of: {intent_text}",
                priority=self._extract_priority(intent_text),
                effort_estimate=task_def.get("effort", "medium"),
                tags=task_def.get("tags", []),
                order=i
            )

            # Set up sequential dependencies
            if template["strategy"] == DecompositionStrategy.SEQUENTIAL and i > 0:
                task.depends_on = [i]  # Depends on previous task
                graph.tasks[i-1].blocks = [i + 1]

            # Apply deadline if provided
            if context.get("deadline"):
                task.deadline = context["deadline"]

            # Score with Priority Engine
            if self.priority_engine:
                scored = self.priority_engine.score_task(task.to_dict())
                task.priority_score = scored.final_score
                task.quadrant = scored.quadrant.value

            graph.tasks.append(task)

        logger.info(f"Applied template '{template_name}' - {len(graph.tasks)} tasks")
        return graph

    def _decompose_compound(self, intent_text: str, context: Dict[str, Any]) -> TaskGraph:
        """Decompose compound intent into separate tasks"""
        # Split on compound indicators
        parts = re.split(r'\s+and\s+(?:then\s+)?|\s+then\s+|,\s*|\s+also\s+',
                        intent_text, flags=re.IGNORECASE)
        parts = [p.strip() for p in parts if p.strip()]

        graph = TaskGraph(
            goal_title=self._extract_goal_title(intent_text),
            goal_description=intent_text,
            strategy=DecompositionStrategy.SEQUENTIAL
        )

        for i, part in enumerate(parts):
            task = TaskNode(
                id=i + 1,
                title=self._clean_task_title(part),
                description=part,
                priority=self._extract_priority(part),
                effort_estimate=self._estimate_effort(part),
                order=i
            )

            # Sequential dependencies
            if i > 0:
                task.depends_on = [i]
                graph.tasks[i-1].blocks = [i + 1]

            # Score with Priority Engine
            if self.priority_engine:
                scored = self.priority_engine.score_task(task.to_dict())
                task.priority_score = scored.final_score
                task.quadrant = scored.quadrant.value

            graph.tasks.append(task)

        logger.info(f"Decomposed compound intent into {len(graph.tasks)} tasks")
        return graph

    def _decompose_steps(self, intent_text: str, context: Dict[str, Any]) -> TaskGraph:
        """Decompose step-by-step intent"""
        # Split on step indicators
        lines = intent_text.split('\n')
        steps = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Remove step prefixes
            cleaned = re.sub(r'^(first|then|next|finally|after that|lastly|\d+[\.\)])\s*',
                           '', line, flags=re.IGNORECASE)
            if cleaned:
                steps.append(cleaned)

        if not steps:
            return self._create_simple_task(intent_text, context)

        graph = TaskGraph(
            goal_title=self._extract_goal_title(intent_text),
            goal_description=intent_text,
            strategy=DecompositionStrategy.SEQUENTIAL
        )

        for i, step in enumerate(steps):
            task = TaskNode(
                id=i + 1,
                title=self._clean_task_title(step),
                description=step,
                priority=self._extract_priority(step),
                effort_estimate=self._estimate_effort(step),
                order=i
            )

            if i > 0:
                task.depends_on = [i]
                graph.tasks[i-1].blocks = [i + 1]

            if self.priority_engine:
                scored = self.priority_engine.score_task(task.to_dict())
                task.priority_score = scored.final_score
                task.quadrant = scored.quadrant.value

            graph.tasks.append(task)

        logger.info(f"Decomposed steps into {len(graph.tasks)} tasks")
        return graph

    def _create_simple_task(self, intent_text: str, context: Dict[str, Any]) -> TaskGraph:
        """Create a simple single-task graph"""
        task = TaskNode(
            id=1,
            title=self._clean_task_title(intent_text),
            description=intent_text,
            priority=self._extract_priority(intent_text),
            effort_estimate=self._estimate_effort(intent_text),
            deadline=context.get("deadline"),
            order=0
        )

        if self.priority_engine:
            scored = self.priority_engine.score_task(task.to_dict())
            task.priority_score = scored.final_score
            task.quadrant = scored.quadrant.value

        graph = TaskGraph(
            goal_title=task.title,
            goal_description=intent_text,
            strategy=DecompositionStrategy.SEQUENTIAL
        )
        graph.tasks.append(task)

        return graph

    def _extract_goal_title(self, text: str) -> str:
        """Extract a concise goal title from intent text"""
        # Take first sentence or first 60 chars
        sentences = text.split('. ')
        title = sentences[0][:60]
        return title.strip().capitalize()

    def _clean_task_title(self, text: str) -> str:
        """Clean and format task title"""
        # Remove common prefixes
        cleaned = re.sub(r'^(need to|have to|should|must|want to|going to)\s+',
                        '', text, flags=re.IGNORECASE)
        # Capitalize and limit length
        cleaned = cleaned.strip().capitalize()
        if len(cleaned) > 80:
            cleaned = cleaned[:77] + "..."
        return cleaned


class IntentTaskTranslator:
    """
    Main translator class - converts ParsedIntents to TaskGraphs
    and persists them to agent-runtime-mcp.
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or AGENT_RUNTIME_DB
        self.decomposer = IntentDecomposer()
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Load persistent state"""
        if TRANSLATOR_STATE_FILE.exists():
            try:
                return json.loads(TRANSLATOR_STATE_FILE.read_text())
            except:
                pass
        return {
            "goals_created": 0,
            "tasks_created": 0,
            "templates_used": {},
            "last_active": None
        }

    def _save_state(self):
        """Save persistent state"""
        self.state["last_active"] = datetime.now().isoformat()
        TRANSLATOR_STATE_FILE.write_text(json.dumps(self.state, indent=2))

    async def translate(self, intent: "ParsedIntent") -> TaskGraph:
        """
        Translate a ParsedIntent into a TaskGraph.

        Args:
            intent: ParsedIntent from Intent Capture Stream

        Returns:
            TaskGraph with decomposed tasks
        """
        context = {
            "deadline": intent.deadline,
            "tags": intent.tags,
            "goal_id": intent.related_goal_id
        }

        graph = self.decomposer.decompose(intent.raw_input, context)

        logger.info(f"Translated intent to {len(graph.tasks)} tasks using {graph.strategy.value}")

        return graph

    async def translate_and_persist(self, intent: "ParsedIntent") -> TaskGraph:
        """
        Translate intent and persist to agent-runtime database.

        Args:
            intent: ParsedIntent to translate

        Returns:
            TaskGraph with assigned IDs
        """
        graph = await self.translate(intent)

        # Persist to database
        await self._persist_graph(graph)

        return graph

    async def _persist_graph(self, graph: TaskGraph) -> None:
        """Persist task graph to agent-runtime database"""
        if not self.db_path.exists():
            logger.warning(f"Database not found: {self.db_path}")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create goal first
            cursor.execute("""
                INSERT INTO goals (name, description, status, created_at, metadata)
                VALUES (?, ?, 'active', ?, ?)
            """, (
                graph.goal_title,
                graph.goal_description,
                datetime.now().isoformat(),
                json.dumps({
                    "source": "intent_translator",
                    "strategy": graph.strategy.value,
                    "template": graph.template_used,
                    "task_count": len(graph.tasks)
                })
            ))

            graph.goal_id = cursor.lastrowid
            self.state["goals_created"] += 1

            # Create tasks with proper IDs
            id_mapping = {}  # temp_id -> real_id

            for task in graph.tasks:
                cursor.execute("""
                    INSERT INTO tasks (title, description, status, priority, goal_id, metadata, created_at)
                    VALUES (?, ?, 'pending', ?, ?, ?, ?)
                """, (
                    task.title,
                    task.description,
                    task.priority,
                    graph.goal_id,
                    json.dumps({
                        "source": "intent_translator",
                        "effort": task.effort_estimate,
                        "tags": task.tags,
                        "order": task.order,
                        "priority_score": task.priority_score,
                        "quadrant": task.quadrant,
                        "temp_depends_on": task.depends_on,
                        "deadline": task.deadline
                    }),
                    datetime.now().isoformat()
                ))

                real_id = cursor.lastrowid
                id_mapping[task.id] = real_id
                task.id = real_id
                graph.task_ids.append(real_id)
                self.state["tasks_created"] += 1

            # Update dependencies with real IDs (stored in metadata)
            for task in graph.tasks:
                if task.depends_on:
                    real_deps = [id_mapping.get(d, d) for d in task.depends_on]
                    cursor.execute("""
                        UPDATE tasks SET metadata = json_set(metadata, '$.depends_on', ?)
                        WHERE id = ?
                    """, (json.dumps(real_deps), task.id))
                    task.depends_on = real_deps

            conn.commit()
            conn.close()

            # Track template usage
            if graph.template_used:
                self.state["templates_used"][graph.template_used] = \
                    self.state["templates_used"].get(graph.template_used, 0) + 1

            self._save_state()

            logger.info(f"Persisted goal {graph.goal_id} with {len(graph.tasks)} tasks")

        except Exception as e:
            logger.error(f"Failed to persist graph: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """Get translator statistics"""
        return {
            "goals_created": self.state["goals_created"],
            "tasks_created": self.state["tasks_created"],
            "templates_used": self.state["templates_used"],
            "last_active": self.state["last_active"]
        }


# Test the translator
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    print("Intent→Task Translator Test")
    print("=" * 60)

    decomposer = IntentDecomposer()

    # Test cases
    test_intents = [
        "Deploy the new feature to production",
        "Fix the login bug and then update the documentation",
        "Research GraphQL options for our API",
        "First set up the project, then add authentication, finally deploy it",
        "Implement a new user dashboard feature",
        "Quick typo fix in the README"
    ]

    for intent_text in test_intents:
        print(f"\n{'─' * 60}")
        print(f"Intent: {intent_text}")
        print(f"{'─' * 60}")

        graph = decomposer.decompose(intent_text)

        print(f"Strategy: {graph.strategy.value}")
        if graph.template_used:
            print(f"Template: {graph.template_used}")
        print(f"Tasks ({len(graph.tasks)}):")

        for task in graph.tasks:
            deps = f" [depends on: {task.depends_on}]" if task.depends_on else ""
            score = f" (Score: {task.priority_score:.0f})" if task.priority_score else ""
            print(f"  {task.order + 1}. {task.title}{deps}{score}")
            print(f"     Effort: {task.effort_estimate} | Priority: {task.priority}")

    print("\n" + "=" * 60)
    print("Translator Test Complete")
