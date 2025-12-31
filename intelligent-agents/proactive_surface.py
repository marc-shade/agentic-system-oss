"""
Proactive Surface - Ambient Task and Context Surfacing

Part of the Translation Layer architecture:
- Intent Capture Stream → Priority Engine → Intent Task Translator → **Proactive Surface**

This component intelligently surfaces relevant tasks, reminders, and context
to the user at the right time without being intrusive.

Key capabilities:
- Time-based triggers (morning focus, afternoon energy, evening wrap-up)
- Activity-based triggers (returning from break, context switch)
- Context-aware recommendations based on current work
- Deadline and priority-driven surfacing
- Voice and visual presentation modes
- Learning from user engagement patterns
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("proactive-surface")

# Import Priority Engine
try:
    from priority_engine import PriorityEngine, ScoredTask, EisenhowerQuadrant
    PRIORITY_ENGINE_AVAILABLE = True
except ImportError:
    PRIORITY_ENGINE_AVAILABLE = False
    logger.warning("Priority Engine not available")

# Import Intent Capture Stream for context
try:
    from intent_capture_stream import IntentCaptureStream, IntentCategory
    INTENT_STREAM_AVAILABLE = True
except ImportError:
    INTENT_STREAM_AVAILABLE = False
    logger.warning("Intent Capture Stream not available")


class SurfaceTrigger(Enum):
    """Types of triggers that initiate surfacing"""
    TIME_BASED = "time_based"           # Scheduled intervals (morning, afternoon, evening)
    ACTIVITY_BASED = "activity_based"   # User activity patterns (return from break)
    CONTEXT_CHANGE = "context_change"   # Switching projects/topics
    IDLE_DETECTED = "idle_detected"     # User idle for period
    DEADLINE_APPROACHING = "deadline"   # Task deadline imminent
    GOAL_MILESTONE = "milestone"        # Progress toward goal
    ENERGY_OPTIMAL = "energy"           # Optimal focus time detected
    MANUAL_REQUEST = "manual"           # User explicitly requested


class SurfaceMode(Enum):
    """How to present surfaced items"""
    VOICE = "voice"                     # Voice announcement via TTS
    VISUAL = "visual"                   # Visual notification/display
    AMBIENT = "ambient"                 # Subtle ambient indicator
    COMBINED = "combined"               # Voice + visual


class SurfacePriority(Enum):
    """Urgency of surfaced item"""
    CRITICAL = "critical"   # Must surface immediately
    HIGH = "high"           # Surface at next opportunity
    MEDIUM = "medium"       # Surface when convenient
    LOW = "low"             # Surface only if idle


@dataclass
class SurfaceItem:
    """An item to be surfaced to the user"""
    item_id: str
    item_type: str  # task, reminder, recommendation, insight, milestone
    title: str
    description: str
    priority: SurfacePriority
    trigger: SurfaceTrigger
    context_tags: List[str] = field(default_factory=list)
    action_options: List[str] = field(default_factory=list)  # What user can do
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)

    # Engagement tracking
    surfaced_count: int = 0
    last_surfaced: Optional[datetime] = None
    user_response: Optional[str] = None  # engaged, dismissed, snoozed


@dataclass
class SurfaceContext:
    """Current context for surfacing decisions"""
    time_of_day: str  # morning, afternoon, evening, night
    day_of_week: str
    is_work_hours: bool
    user_activity: str  # active, idle, returning, focused
    current_focus: Optional[str]  # What user is working on
    energy_level: str  # high, medium, low (estimated from time/patterns)
    recent_completions: List[str] = field(default_factory=list)
    active_goals: List[str] = field(default_factory=list)
    pending_deadlines: List[Dict] = field(default_factory=list)


@dataclass
class SurfaceConfig:
    """Configuration for surfacing behavior"""
    # Timing
    morning_start: int = 8        # Hour to start morning surfacing
    evening_start: int = 17       # Hour to start evening wrap-up
    night_quiet_start: int = 21   # Hour to reduce surfacing

    # Frequency limits
    max_surfaces_per_hour: int = 3
    min_interval_minutes: int = 15
    idle_threshold_minutes: int = 10

    # Presentation
    default_mode: SurfaceMode = SurfaceMode.VOICE
    critical_mode: SurfaceMode = SurfaceMode.COMBINED

    # Learning
    learn_from_dismissals: bool = True
    snooze_duration_minutes: int = 30

    # Context awareness
    respect_focus_mode: bool = True
    work_days: List[str] = field(default_factory=lambda: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])


class TimePatterns:
    """Time-based patterns for optimal surfacing"""

    ENERGY_PATTERNS = {
        "morning": {
            "hours": range(8, 12),
            "energy": "high",
            "best_for": ["complex_tasks", "creative_work", "planning"],
            "surface_priority": ["Q1_do", "Q2_schedule"]
        },
        "early_afternoon": {
            "hours": range(12, 14),
            "energy": "low",
            "best_for": ["routine_tasks", "meetings", "admin"],
            "surface_priority": ["Q3_delegate", "quick_wins"]
        },
        "afternoon": {
            "hours": range(14, 17),
            "energy": "medium",
            "best_for": ["collaboration", "reviews", "implementation"],
            "surface_priority": ["Q1_do", "Q2_schedule"]
        },
        "evening": {
            "hours": range(17, 21),
            "energy": "declining",
            "best_for": ["wrap_up", "planning_tomorrow", "reflection"],
            "surface_priority": ["review", "planning"]
        },
        "night": {
            "hours": range(21, 24),
            "energy": "low",
            "best_for": ["light_reading", "ideas", "rest"],
            "surface_priority": []  # Minimal surfacing
        }
    }

    @classmethod
    def get_current_pattern(cls) -> Dict[str, Any]:
        """Get pattern for current time"""
        hour = datetime.now().hour
        for name, pattern in cls.ENERGY_PATTERNS.items():
            if hour in pattern["hours"]:
                return {"name": name, **pattern}
        # Early morning fallback
        return {"name": "early_morning", "energy": "waking", "best_for": ["light_tasks"], "surface_priority": []}

    @classmethod
    def get_time_of_day(cls) -> str:
        """Get time of day category"""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"


class SurfaceRecommendations:
    """Generate contextual recommendations"""

    # Recommendation templates based on context
    TEMPLATES = {
        "morning_start": [
            "Good morning! You have {count} high-priority tasks today. Shall I walk you through them?",
            "Starting the day with {top_task}. This aligns with your goal: {goal}.",
            "Your most important task today is {top_task}. Ready to begin?"
        ],
        "afternoon_check": [
            "Afternoon check-in: {completed} tasks done, {remaining} remaining.",
            "You've made good progress! {top_task} is next on your priority list.",
            "Energy dip time - here's a quick win you can tackle: {quick_win}"
        ],
        "evening_wrap": [
            "Day wrap-up: {completed} tasks completed. Tomorrow's top priority: {tomorrow_top}",
            "Nice work today! Before you wrap up, {pending_action}",
            "End of day review: {summary}"
        ],
        "deadline_warning": [
            "Heads up: {task} is due in {time_remaining}.",
            "Deadline approaching: {task} - {time_remaining} left.",
            "Priority alert: {task} due {time_remaining}. Need to focus on this?"
        ],
        "context_switch": [
            "Switching contexts? You were working on {previous}. {current} is queued next.",
            "Context change detected. Quick capture before switching: anything to note about {previous}?",
            "New focus area: {current}. Related tasks: {related_count}"
        ],
        "idle_return": [
            "Welcome back! You were working on {previous}. Ready to continue?",
            "Back at it? Here's where you left off: {previous}",
            "Quick refresh: {summary}. Want to pick up where you left off?"
        ],
        "goal_progress": [
            "Milestone! You're {percent}% toward {goal}.",
            "Progress update: {completed_steps} of {total_steps} steps done for {goal}.",
            "Great momentum on {goal}! Next step: {next_step}"
        ],
        "quick_win": [
            "Quick win available: {task} (estimated {effort})",
            "Got 5 minutes? Here's something you can knock out: {task}",
            "Low-hanging fruit: {task}"
        ]
    }

    @classmethod
    def generate(cls, template_type: str, context: Dict[str, Any]) -> str:
        """Generate a recommendation message"""
        templates = cls.TEMPLATES.get(template_type, [])
        if not templates:
            return f"Recommendation: {context.get('message', 'Check your tasks')}"

        template = random.choice(templates)
        try:
            return template.format(**context)
        except KeyError as e:
            logger.warning(f"Missing context key for template: {e}")
            return template.split("{")[0] + "..."


class ProactiveSurface:
    """
    Main Proactive Surface engine.

    Intelligently surfaces tasks, reminders, and context to the user
    at optimal times without being intrusive.
    """

    def __init__(self, config: Optional[SurfaceConfig] = None):
        self.config = config or SurfaceConfig()
        self.priority_engine = PriorityEngine() if PRIORITY_ENGINE_AVAILABLE else None

        # State tracking
        self.surface_queue: List[SurfaceItem] = []
        self.surface_history: List[Dict] = []
        self.last_surface_time: Optional[datetime] = None
        self.surfaces_this_hour: int = 0
        self.hour_tracker: int = datetime.now().hour

        # Context tracking
        self.current_context: Optional[SurfaceContext] = None
        self.previous_focus: Optional[str] = None
        self.last_activity_time: datetime = datetime.now()

        # Learning data
        self.engagement_stats: Dict[str, Dict] = {}  # item_type -> {engaged, dismissed, snoozed}
        self.optimal_times: Dict[str, List[int]] = {}  # item_type -> [hours with engagement]

        # Database for persistence
        self.db_path = Path.home() / ".claude" / "proactive_surface.db"
        self._init_database()

        logger.info("Proactive Surface initialized")

    def _init_database(self):
        """Initialize SQLite database for persistence"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Surface history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS surface_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                title TEXT NOT NULL,
                trigger TEXT NOT NULL,
                mode TEXT NOT NULL,
                surfaced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_response TEXT,
                response_time_seconds REAL,
                context_json TEXT
            )
        """)

        # Engagement patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS engagement_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                hour_of_day INTEGER,
                day_of_week TEXT,
                engaged_count INTEGER DEFAULT 0,
                dismissed_count INTEGER DEFAULT 0,
                snoozed_count INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Snoozed items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snoozed_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL,
                snooze_until TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def build_context(self) -> SurfaceContext:
        """Build current context for surfacing decisions"""
        now = datetime.now()
        time_pattern = TimePatterns.get_current_pattern()

        # Determine user activity
        idle_minutes = (now - self.last_activity_time).total_seconds() / 60
        if idle_minutes > self.config.idle_threshold_minutes:
            activity = "idle"
        elif idle_minutes > 2 and self.previous_focus:
            activity = "returning"
        else:
            activity = "active"

        context = SurfaceContext(
            time_of_day=TimePatterns.get_time_of_day(),
            day_of_week=now.strftime("%A"),
            is_work_hours=self._is_work_hours(now),
            user_activity=activity,
            current_focus=self.previous_focus,
            energy_level=time_pattern.get("energy", "medium"),
            recent_completions=[],
            active_goals=[],
            pending_deadlines=[]
        )

        # Enrich with task data if available
        if self.priority_engine:
            context = self._enrich_context_with_tasks(context)

        self.current_context = context
        return context

    def _is_work_hours(self, dt: datetime) -> bool:
        """Check if current time is within work hours"""
        day = dt.strftime("%A")
        hour = dt.hour
        return (
            day in self.config.work_days and
            self.config.morning_start <= hour < self.config.evening_start
        )

    def _enrich_context_with_tasks(self, context: SurfaceContext) -> SurfaceContext:
        """Add task information to context"""
        # Load tasks from agent-runtime database
        agent_db = Path.home() / ".claude" / "agent_runtime.db"
        if not agent_db.exists():
            return context

        try:
            conn = sqlite3.connect(agent_db)
            cursor = conn.cursor()

            # Get active goals
            cursor.execute("""
                SELECT name FROM goals
                WHERE status = 'active'
                ORDER BY created_at DESC LIMIT 5
            """)
            context.active_goals = [row[0] for row in cursor.fetchall()]

            # Get pending tasks with deadlines (handle schema variations)
            try:
                cursor.execute("""
                    SELECT title, deadline, priority FROM tasks
                    WHERE status = 'pending' AND deadline IS NOT NULL
                    ORDER BY deadline ASC LIMIT 10
                """)
                for row in cursor.fetchall():
                    context.pending_deadlines.append({
                        "title": row[0],
                        "deadline": row[1],
                        "priority": row[2]
                    })
            except sqlite3.OperationalError:
                # Deadline column may not exist - get high priority tasks instead
                cursor.execute("""
                    SELECT title, priority FROM tasks
                    WHERE status = 'pending'
                    ORDER BY priority DESC LIMIT 10
                """)
                for row in cursor.fetchall():
                    if row[1] >= 7:  # High priority as pseudo-deadline
                        context.pending_deadlines.append({
                            "title": row[0],
                            "deadline": None,
                            "priority": row[1]
                        })

            # Get recent completions
            cursor.execute("""
                SELECT title FROM tasks
                WHERE status = 'completed'
                AND updated_at > datetime('now', '-24 hours')
                ORDER BY updated_at DESC LIMIT 5
            """)
            context.recent_completions = [row[0] for row in cursor.fetchall()]

            conn.close()
        except Exception as e:
            logger.warning(f"Error enriching context: {e}")

        return context

    def evaluate_triggers(self) -> List[Tuple[SurfaceTrigger, Dict[str, Any]]]:
        """Evaluate which triggers should fire"""
        context = self.build_context()
        triggered = []

        # Time-based triggers
        time_trigger = self._evaluate_time_triggers(context)
        if time_trigger:
            triggered.append(time_trigger)

        # Activity-based triggers
        if context.user_activity == "returning":
            triggered.append((
                SurfaceTrigger.ACTIVITY_BASED,
                {"reason": "returning_from_idle", "previous_focus": self.previous_focus}
            ))
        elif context.user_activity == "idle":
            triggered.append((
                SurfaceTrigger.IDLE_DETECTED,
                {"idle_minutes": (datetime.now() - self.last_activity_time).total_seconds() / 60}
            ))

        # Deadline triggers
        deadline_triggers = self._evaluate_deadline_triggers(context)
        triggered.extend(deadline_triggers)

        # Energy-optimal triggers
        if context.energy_level == "high" and context.is_work_hours:
            triggered.append((
                SurfaceTrigger.ENERGY_OPTIMAL,
                {"energy": "high", "time_pattern": TimePatterns.get_current_pattern()["name"]}
            ))

        return triggered

    def _evaluate_time_triggers(self, context: SurfaceContext) -> Optional[Tuple[SurfaceTrigger, Dict]]:
        """Check for time-based triggers"""
        now = datetime.now()
        hour = now.hour

        # Morning start (once per day)
        if hour == self.config.morning_start and now.minute < 30:
            if not self._triggered_today("morning_start"):
                return (SurfaceTrigger.TIME_BASED, {"type": "morning_start"})

        # Afternoon check-in
        if hour == 14 and now.minute < 30:
            if not self._triggered_today("afternoon_check"):
                return (SurfaceTrigger.TIME_BASED, {"type": "afternoon_check"})

        # Evening wrap-up
        if hour == self.config.evening_start and now.minute < 30:
            if not self._triggered_today("evening_wrap"):
                return (SurfaceTrigger.TIME_BASED, {"type": "evening_wrap"})

        return None

    def _triggered_today(self, trigger_type: str) -> bool:
        """Check if a trigger already fired today"""
        today = datetime.now().date()
        for record in self.surface_history[-50:]:  # Check recent history
            if (record.get("trigger_type") == trigger_type and
                record.get("timestamp", "")[:10] == str(today)):
                return True
        return False

    def _evaluate_deadline_triggers(self, context: SurfaceContext) -> List[Tuple[SurfaceTrigger, Dict]]:
        """Check for deadline-based triggers"""
        triggers = []
        now = datetime.now()

        for deadline in context.pending_deadlines:
            try:
                deadline_dt = datetime.fromisoformat(deadline["deadline"])
                hours_until = (deadline_dt - now).total_seconds() / 3600

                # Trigger at various thresholds
                if 0 < hours_until <= 4:
                    triggers.append((
                        SurfaceTrigger.DEADLINE_APPROACHING,
                        {"task": deadline["title"], "hours": hours_until, "urgency": "critical"}
                    ))
                elif 4 < hours_until <= 24:
                    triggers.append((
                        SurfaceTrigger.DEADLINE_APPROACHING,
                        {"task": deadline["title"], "hours": hours_until, "urgency": "high"}
                    ))
            except (ValueError, TypeError):
                continue

        return triggers

    def generate_surface_items(self, triggers: List[Tuple[SurfaceTrigger, Dict]]) -> List[SurfaceItem]:
        """Generate items to surface based on triggers"""
        items = []
        context = self.current_context or self.build_context()

        for trigger, data in triggers:
            if trigger == SurfaceTrigger.TIME_BASED:
                items.extend(self._generate_time_based_items(data, context))
            elif trigger == SurfaceTrigger.DEADLINE_APPROACHING:
                items.append(self._generate_deadline_item(data))
            elif trigger == SurfaceTrigger.ACTIVITY_BASED:
                items.extend(self._generate_activity_items(data, context))
            elif trigger == SurfaceTrigger.IDLE_DETECTED:
                items.extend(self._generate_idle_items(data, context))
            elif trigger == SurfaceTrigger.ENERGY_OPTIMAL:
                items.extend(self._generate_energy_items(data, context))

        # Filter snoozed items
        items = self._filter_snoozed(items)

        # Sort by priority
        priority_order = {
            SurfacePriority.CRITICAL: 0,
            SurfacePriority.HIGH: 1,
            SurfacePriority.MEDIUM: 2,
            SurfacePriority.LOW: 3
        }
        items.sort(key=lambda x: priority_order.get(x.priority, 99))

        return items

    def _generate_time_based_items(self, data: Dict, context: SurfaceContext) -> List[SurfaceItem]:
        """Generate items for time-based triggers"""
        items = []
        trigger_type = data.get("type")

        if trigger_type == "morning_start":
            # Morning briefing
            top_tasks = self._get_top_priority_tasks(3)
            if top_tasks:
                message = SurfaceRecommendations.generate("morning_start", {
                    "count": len(top_tasks),
                    "top_task": top_tasks[0].get("title", "your top task"),
                    "goal": context.active_goals[0] if context.active_goals else "your objectives"
                })
                items.append(SurfaceItem(
                    item_id=f"morning_{datetime.now().strftime('%Y%m%d')}",
                    item_type="briefing",
                    title="Morning Briefing",
                    description=message,
                    priority=SurfacePriority.HIGH,
                    trigger=SurfaceTrigger.TIME_BASED,
                    context_tags=["morning", "planning"],
                    action_options=["Start top task", "Review all tasks", "Adjust priorities"],
                    metadata={"tasks": top_tasks}
                ))

        elif trigger_type == "afternoon_check":
            completed = len(context.recent_completions)
            remaining = self._count_pending_tasks()
            quick_wins = self._get_quick_wins(1)

            message = SurfaceRecommendations.generate("afternoon_check", {
                "completed": completed,
                "remaining": remaining,
                "top_task": self._get_top_priority_tasks(1)[0].get("title", "next task") if self._get_top_priority_tasks(1) else "your next task",
                "quick_win": quick_wins[0].get("title", "a quick task") if quick_wins else "a quick task"
            })
            items.append(SurfaceItem(
                item_id=f"afternoon_{datetime.now().strftime('%Y%m%d')}",
                item_type="check_in",
                title="Afternoon Check-in",
                description=message,
                priority=SurfacePriority.MEDIUM,
                trigger=SurfaceTrigger.TIME_BASED,
                context_tags=["afternoon", "progress"],
                action_options=["Continue current", "Switch task", "Take break"]
            ))

        elif trigger_type == "evening_wrap":
            completed = len(context.recent_completions)
            tomorrow_top = self._get_top_priority_tasks(1)

            message = SurfaceRecommendations.generate("evening_wrap", {
                "completed": completed,
                "tomorrow_top": tomorrow_top[0].get("title", "planning") if tomorrow_top else "planning tomorrow",
                "pending_action": "capture any final thoughts",
                "summary": f"{completed} tasks completed today"
            })
            items.append(SurfaceItem(
                item_id=f"evening_{datetime.now().strftime('%Y%m%d')}",
                item_type="wrap_up",
                title="Day Wrap-up",
                description=message,
                priority=SurfacePriority.MEDIUM,
                trigger=SurfaceTrigger.TIME_BASED,
                context_tags=["evening", "reflection"],
                action_options=["Review day", "Plan tomorrow", "Done for today"]
            ))

        return items

    def _generate_deadline_item(self, data: Dict) -> SurfaceItem:
        """Generate item for approaching deadline"""
        hours = data.get("hours", 24)
        urgency = data.get("urgency", "medium")

        if hours < 1:
            time_str = f"{int(hours * 60)} minutes"
        elif hours < 24:
            time_str = f"{int(hours)} hours"
        else:
            time_str = f"{int(hours / 24)} days"

        message = SurfaceRecommendations.generate("deadline_warning", {
            "task": data.get("task", "A task"),
            "time_remaining": time_str
        })

        priority = SurfacePriority.CRITICAL if urgency == "critical" else SurfacePriority.HIGH

        return SurfaceItem(
            item_id=f"deadline_{data.get('task', 'task')[:20]}_{datetime.now().strftime('%H%M')}",
            item_type="deadline",
            title="Deadline Alert",
            description=message,
            priority=priority,
            trigger=SurfaceTrigger.DEADLINE_APPROACHING,
            context_tags=["deadline", urgency],
            action_options=["Focus on this", "Extend deadline", "Delegate"],
            metadata={"hours_remaining": hours, "task": data.get("task")}
        )

    def _generate_activity_items(self, data: Dict, context: SurfaceContext) -> List[SurfaceItem]:
        """Generate items for activity-based triggers"""
        items = []
        reason = data.get("reason")

        if reason == "returning_from_idle":
            previous = data.get("previous_focus", "your previous task")
            message = SurfaceRecommendations.generate("idle_return", {
                "previous": previous,
                "summary": f"You were working on: {previous}"
            })
            items.append(SurfaceItem(
                item_id=f"return_{datetime.now().strftime('%H%M%S')}",
                item_type="context_restore",
                title="Welcome Back",
                description=message,
                priority=SurfacePriority.MEDIUM,
                trigger=SurfaceTrigger.ACTIVITY_BASED,
                context_tags=["return", "context"],
                action_options=["Continue", "New task", "Review tasks"]
            ))

        return items

    def _generate_idle_items(self, data: Dict, context: SurfaceContext) -> List[SurfaceItem]:
        """Generate items when user is idle"""
        items = []
        idle_minutes = data.get("idle_minutes", 10)

        # Only suggest quick wins during idle
        if idle_minutes > 15:
            quick_wins = self._get_quick_wins(1)
            if quick_wins:
                task = quick_wins[0]
                message = SurfaceRecommendations.generate("quick_win", {
                    "task": task.get("title", "a quick task"),
                    "effort": task.get("effort", "5-10 minutes")
                })
                items.append(SurfaceItem(
                    item_id=f"quickwin_{datetime.now().strftime('%H%M%S')}",
                    item_type="suggestion",
                    title="Quick Win Available",
                    description=message,
                    priority=SurfacePriority.LOW,
                    trigger=SurfaceTrigger.IDLE_DETECTED,
                    context_tags=["quick_win", "suggestion"],
                    action_options=["Do it", "Later", "Different task"],
                    metadata={"task": task}
                ))

        return items

    def _generate_energy_items(self, data: Dict, context: SurfaceContext) -> List[SurfaceItem]:
        """Generate items for optimal energy periods"""
        items = []

        # Surface complex/important tasks during high energy
        if data.get("energy") == "high":
            top_tasks = self._get_top_priority_tasks(1)
            if top_tasks:
                task = top_tasks[0]
                items.append(SurfaceItem(
                    item_id=f"energy_{datetime.now().strftime('%H%M%S')}",
                    item_type="recommendation",
                    title="Optimal Focus Time",
                    description=f"High energy window! Great time for: {task.get('title', 'important work')}",
                    priority=SurfacePriority.MEDIUM,
                    trigger=SurfaceTrigger.ENERGY_OPTIMAL,
                    context_tags=["energy", "focus", "deep_work"],
                    action_options=["Start now", "Different task", "Not now"],
                    metadata={"task": task, "time_pattern": data.get("time_pattern")}
                ))

        return items

    def _get_top_priority_tasks(self, limit: int = 3) -> List[Dict]:
        """Get top priority tasks from agent-runtime database"""
        agent_db = Path.home() / ".claude" / "agent_runtime.db"
        if not agent_db.exists():
            return []

        try:
            conn = sqlite3.connect(agent_db)
            cursor = conn.cursor()

            # Try with deadline column first, fall back to without
            try:
                cursor.execute("""
                    SELECT id, title, description, priority, deadline
                    FROM tasks
                    WHERE status = 'pending'
                    ORDER BY priority DESC, deadline ASC
                    LIMIT ?
                """, (limit,))
                has_deadline = True
            except sqlite3.OperationalError:
                cursor.execute("""
                    SELECT id, title, description, priority
                    FROM tasks
                    WHERE status = 'pending'
                    ORDER BY priority DESC
                    LIMIT ?
                """, (limit,))
                has_deadline = False

            tasks = []
            for row in cursor.fetchall():
                task = {
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "priority": row[3],
                    "deadline": row[4] if has_deadline else None
                }

                # Score with priority engine if available
                if self.priority_engine:
                    scored = self.priority_engine.score_task(task)
                    task["score"] = scored.final_score
                    task["quadrant"] = scored.quadrant.value

                tasks.append(task)

            conn.close()
            return tasks
        except Exception as e:
            logger.warning(f"Error getting priority tasks: {e}")
            return []

    def _get_quick_wins(self, limit: int = 3) -> List[Dict]:
        """Get quick win tasks (low effort, moderate importance)"""
        agent_db = Path.home() / ".claude" / "agent_runtime.db"
        if not agent_db.exists():
            return []

        try:
            conn = sqlite3.connect(agent_db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, description, priority
                FROM tasks
                WHERE status = 'pending'
                AND (priority BETWEEN 3 AND 6)
                ORDER BY priority DESC
                LIMIT ?
            """, (limit,))

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "priority": row[3],
                    "effort": "5-10 minutes"  # Estimated quick
                })

            conn.close()
            return tasks
        except Exception as e:
            logger.warning(f"Error getting quick wins: {e}")
            return []

    def _count_pending_tasks(self) -> int:
        """Count pending tasks"""
        agent_db = Path.home() / ".claude" / "agent_runtime.db"
        if not agent_db.exists():
            return 0

        try:
            conn = sqlite3.connect(agent_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0

    def _filter_snoozed(self, items: List[SurfaceItem]) -> List[SurfaceItem]:
        """Filter out snoozed items"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT item_id FROM snoozed_items
                WHERE snooze_until > datetime('now')
            """)
            snoozed_ids = {row[0] for row in cursor.fetchall()}
            conn.close()

            return [item for item in items if item.item_id not in snoozed_ids]
        except:
            return items

    async def surface(self, mode: Optional[SurfaceMode] = None) -> List[Dict]:
        """Main surfacing method - evaluate and present items"""
        # Check rate limiting
        if not self._can_surface():
            return []

        # Evaluate triggers
        triggers = self.evaluate_triggers()
        if not triggers:
            return []

        # Generate items
        items = self.generate_surface_items(triggers)
        if not items:
            return []

        # Present items
        results = []
        for item in items[:3]:  # Limit to top 3 items
            result = await self._present_item(item, mode or self.config.default_mode)
            results.append(result)

            # Record surfacing
            self._record_surface(item, result)

        return results

    def _can_surface(self) -> bool:
        """Check if we can surface based on rate limiting"""
        now = datetime.now()

        # Reset hourly counter
        if now.hour != self.hour_tracker:
            self.hour_tracker = now.hour
            self.surfaces_this_hour = 0

        # Check hourly limit
        if self.surfaces_this_hour >= self.config.max_surfaces_per_hour:
            return False

        # Check minimum interval
        if self.last_surface_time:
            minutes_since = (now - self.last_surface_time).total_seconds() / 60
            if minutes_since < self.config.min_interval_minutes:
                return False

        return True

    async def _present_item(self, item: SurfaceItem, mode: SurfaceMode) -> Dict:
        """Present a surface item to the user"""
        result = {
            "item_id": item.item_id,
            "title": item.title,
            "description": item.description,
            "mode": mode.value,
            "presented_at": datetime.now().isoformat()
        }

        # Use critical mode for critical priority
        if item.priority == SurfacePriority.CRITICAL:
            mode = self.config.critical_mode

        if mode in (SurfaceMode.VOICE, SurfaceMode.COMBINED):
            result["voice_delivered"] = await self._voice_present(item)

        if mode in (SurfaceMode.VISUAL, SurfaceMode.COMBINED):
            result["visual_delivered"] = self._visual_present(item)

        if mode == SurfaceMode.AMBIENT:
            result["ambient_delivered"] = self._ambient_present(item)

        # Update tracking
        item.surfaced_count += 1
        item.last_surfaced = datetime.now()
        self.last_surface_time = datetime.now()
        self.surfaces_this_hour += 1

        return result

    async def _voice_present(self, item: SurfaceItem) -> bool:
        """Present via voice (TTS)"""
        try:
            # Try to use voice-mode MCP
            import subprocess

            # Format message for voice
            voice_message = f"{item.title}. {item.description}"

            # This would call the voice-mode MCP in practice
            # For now, log it
            logger.info(f"Voice surface: {voice_message}")

            # Could also use direct TTS here
            return True
        except Exception as e:
            logger.warning(f"Voice presentation failed: {e}")
            return False

    def _visual_present(self, item: SurfaceItem) -> bool:
        """Present via visual notification"""
        try:
            # Could use terminal-notifier on macOS, or other notification system
            logger.info(f"Visual surface: {item.title} - {item.description}")
            return True
        except Exception as e:
            logger.warning(f"Visual presentation failed: {e}")
            return False

    def _ambient_present(self, item: SurfaceItem) -> bool:
        """Present via ambient indicator (subtle)"""
        try:
            # Could update status line, LED, or other ambient indicator
            logger.info(f"Ambient surface: {item.title}")
            return True
        except Exception as e:
            logger.warning(f"Ambient presentation failed: {e}")
            return False

    def _record_surface(self, item: SurfaceItem, result: Dict):
        """Record surfacing in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO surface_history
                (item_id, item_type, title, trigger, mode, context_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                item.item_id,
                item.item_type,
                item.title,
                item.trigger.value,
                result.get("mode", "unknown"),
                json.dumps({"context_tags": item.context_tags})
            ))
            conn.commit()
            conn.close()

            # Also track in memory
            self.surface_history.append({
                "item_id": item.item_id,
                "trigger_type": item.trigger.value,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Error recording surface: {e}")

    def record_response(self, item_id: str, response: str):
        """Record user response to a surfaced item"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Update surface history
            cursor.execute("""
                UPDATE surface_history
                SET user_response = ?
                WHERE item_id = ? AND user_response IS NULL
                ORDER BY surfaced_at DESC LIMIT 1
            """, (response, item_id))

            # Update engagement patterns
            cursor.execute("""
                SELECT item_type FROM surface_history
                WHERE item_id = ? ORDER BY surfaced_at DESC LIMIT 1
            """, (item_id,))
            row = cursor.fetchone()
            if row:
                item_type = row[0]
                hour = datetime.now().hour
                day = datetime.now().strftime("%A")

                if response == "engaged":
                    cursor.execute("""
                        INSERT INTO engagement_patterns (item_type, hour_of_day, day_of_week, engaged_count)
                        VALUES (?, ?, ?, 1)
                        ON CONFLICT(item_type, hour_of_day, day_of_week)
                        DO UPDATE SET engaged_count = engaged_count + 1
                    """, (item_type, hour, day))
                elif response == "dismissed":
                    cursor.execute("""
                        INSERT INTO engagement_patterns (item_type, hour_of_day, day_of_week, dismissed_count)
                        VALUES (?, ?, ?, 1)
                        ON CONFLICT(item_type, hour_of_day, day_of_week)
                        DO UPDATE SET dismissed_count = dismissed_count + 1
                    """, (item_type, hour, day))

            conn.commit()
            conn.close()

            # Handle snooze
            if response == "snoozed":
                self.snooze_item(item_id)

        except Exception as e:
            logger.warning(f"Error recording response: {e}")

    def snooze_item(self, item_id: str, minutes: Optional[int] = None):
        """Snooze an item for later"""
        if minutes is None:
            minutes = self.config.snooze_duration_minutes

        snooze_until = datetime.now() + timedelta(minutes=minutes)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO snoozed_items (item_id, snooze_until)
                VALUES (?, ?)
            """, (item_id, snooze_until.isoformat()))
            conn.commit()
            conn.close()
            logger.info(f"Snoozed {item_id} until {snooze_until}")
        except Exception as e:
            logger.warning(f"Error snoozing item: {e}")

    def update_activity(self, focus: Optional[str] = None):
        """Update user activity tracking"""
        self.last_activity_time = datetime.now()
        if focus:
            self.previous_focus = focus

    def get_engagement_stats(self) -> Dict[str, Any]:
        """Get engagement statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Overall stats
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN user_response = 'engaged' THEN 1 ELSE 0 END) as engaged,
                    SUM(CASE WHEN user_response = 'dismissed' THEN 1 ELSE 0 END) as dismissed,
                    SUM(CASE WHEN user_response = 'snoozed' THEN 1 ELSE 0 END) as snoozed
                FROM surface_history
            """)
            row = cursor.fetchone()

            stats = {
                "total_surfaces": row[0] or 0,
                "engaged": row[1] or 0,
                "dismissed": row[2] or 0,
                "snoozed": row[3] or 0
            }

            if stats["total_surfaces"] > 0:
                stats["engagement_rate"] = stats["engaged"] / stats["total_surfaces"]
            else:
                stats["engagement_rate"] = 0

            # By type
            cursor.execute("""
                SELECT item_type, COUNT(*),
                    SUM(CASE WHEN user_response = 'engaged' THEN 1 ELSE 0 END)
                FROM surface_history
                GROUP BY item_type
            """)
            stats["by_type"] = {
                row[0]: {"total": row[1], "engaged": row[2]}
                for row in cursor.fetchall()
            }

            conn.close()
            return stats
        except Exception as e:
            logger.warning(f"Error getting stats: {e}")
            return {}


class ProactiveSurfaceIntegration:
    """Integration helper for using Proactive Surface with other components"""

    def __init__(self, surface: ProactiveSurface):
        self.surface = surface

    async def check_and_surface(self) -> List[Dict]:
        """Convenience method to check triggers and surface if appropriate"""
        return await self.surface.surface()

    def on_task_completed(self, task_title: str):
        """Handle task completion - may trigger milestone surfacing"""
        self.surface.update_activity(focus=None)
        # Could check for goal milestones here

    def on_context_switch(self, new_context: str):
        """Handle context switch"""
        old_context = self.surface.previous_focus
        self.surface.update_activity(focus=new_context)

        if old_context and old_context != new_context:
            # Queue context switch surfacing
            pass

    def on_idle_detected(self):
        """Handle idle detection from external source"""
        # This is handled internally, but external triggers could use this
        pass


# Standalone testing
if __name__ == "__main__":
    import asyncio

    async def test_proactive_surface():
        print("=" * 60)
        print("PROACTIVE SURFACE - TEST")
        print("=" * 60)

        surface = ProactiveSurface()

        # Build context
        print("\n1. Building Context:")
        context = surface.build_context()
        print(f"   Time of day: {context.time_of_day}")
        print(f"   Energy level: {context.energy_level}")
        print(f"   User activity: {context.user_activity}")
        print(f"   Is work hours: {context.is_work_hours}")
        print(f"   Active goals: {len(context.active_goals)}")
        print(f"   Pending deadlines: {len(context.pending_deadlines)}")

        # Evaluate triggers
        print("\n2. Evaluating Triggers:")
        triggers = surface.evaluate_triggers()
        for trigger, data in triggers:
            print(f"   {trigger.value}: {data}")

        if not triggers:
            print("   No triggers fired (normal outside trigger times)")

        # Generate items
        print("\n3. Generating Surface Items:")
        items = surface.generate_surface_items(triggers)
        for item in items:
            print(f"   [{item.priority.value}] {item.title}")
            print(f"      {item.description[:60]}...")
            print(f"      Actions: {item.action_options}")

        if not items:
            print("   No items to surface")

        # Test manual item generation
        print("\n4. Manual Item Generation Test:")

        # Simulate deadline trigger
        deadline_data = {
            "task": "Complete quarterly report",
            "hours": 3,
            "urgency": "critical"
        }
        deadline_item = surface._generate_deadline_item(deadline_data)
        print(f"   Deadline item: {deadline_item.title}")
        print(f"   Description: {deadline_item.description}")

        # Get engagement stats
        print("\n5. Engagement Stats:")
        stats = surface.get_engagement_stats()
        print(f"   Total surfaces: {stats.get('total_surfaces', 0)}")
        print(f"   Engagement rate: {stats.get('engagement_rate', 0):.1%}")

        # Test time patterns
        print("\n6. Time Patterns:")
        pattern = TimePatterns.get_current_pattern()
        print(f"   Current pattern: {pattern['name']}")
        print(f"   Energy: {pattern['energy']}")
        print(f"   Best for: {pattern['best_for']}")

        print("\n" + "=" * 60)
        print("PROACTIVE SURFACE TEST COMPLETE")
        print("=" * 60)

    asyncio.run(test_proactive_surface())
