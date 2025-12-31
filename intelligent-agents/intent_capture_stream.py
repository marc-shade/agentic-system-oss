#!/usr/bin/env python3
"""
Intent Capture Stream - Translation Layer for Always-On Orchestration

Implements Nate B Jones' "Translation Layer" concept:
- Captures user intent continuously (voice, text, signals)
- Translates "ramblings, shower thoughts, half-formed ideas" into prioritized tasks
- Routes tasks to agent-runtime-mcp for execution
- Learns patterns to improve intent understanding over time

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                    INTENT CAPTURE STREAM                        │
├─────────────────────────────────────────────────────────────────┤
│  User Input          Intent Parser        Task Router           │
│  ───────────         ─────────────        ───────────           │
│  • Voice Mode  ───►  • Category           • agent-runtime       │
│  • Text input  ───►  • Priority     ───►  • Goal linking        │
│  • Signals     ───►  • Context            • Sub-agent routing   │
└─────────────────────────────────────────────────────────────────┘

Integration Points:
- voice-mode MCP: TTS/STT for proactive prompts and listening
- agent-runtime-mcp: Persistent task/goal management
- enhanced-memory-mcp: Pattern storage and context recall

Status: Phase 2 (Active Intent Capture)
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import aiohttp

# Configure logging
logger = logging.getLogger("intent-capture")

# Import Priority Engine
try:
    from priority_engine import PriorityEngine, PriorityEngineIntegration, ScoredTask
    PRIORITY_ENGINE_AVAILABLE = True
except ImportError:
    PRIORITY_ENGINE_AVAILABLE = False
    logger.warning("Priority Engine not available - basic prioritization only")

# Import Intent Task Translator
try:
    from intent_task_translator import IntentTaskTranslator, IntentDecomposer, TaskGraph
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False
    logger.warning("Intent Task Translator not available - simple task creation only")

# Import Proactive Surface
try:
    from proactive_surface import ProactiveSurface, SurfaceTrigger, SurfaceMode
    PROACTIVE_SURFACE_AVAILABLE = True
except ImportError:
    PROACTIVE_SURFACE_AVAILABLE = False
    logger.warning("Proactive Surface not available - no ambient surfacing")

# Configuration
VOICE_MODE_URL = os.environ.get("VOICE_MODE_URL", "http://localhost:8880")
AGENT_RUNTIME_DB = Path.home() / ".claude" / "agent_runtime.db"
ENHANCED_MEMORY_DB = Path.home() / ".claude" / "enhanced_memories" / "memory.db"
INTENT_STATE_FILE = Path("/tmp/intent_capture_state.json")

# Prompt intervals (adaptive based on context)
PROACTIVE_PROMPT_INTERVAL_IDLE = 1800  # 30 min when idle
PROACTIVE_PROMPT_INTERVAL_ACTIVE = 3600  # 60 min when active (don't interrupt flow)
PROACTIVE_PROMPT_INTERVAL_MIN = 900  # 15 min minimum between prompts


class IntentCategory(Enum):
    """Categories for parsed user intent"""
    TASK = "task"           # Specific actionable item
    IDEA = "idea"           # Half-formed thought to capture
    QUESTION = "question"   # Needs research/answer
    PRIORITY = "priority"   # Reprioritization request
    STATUS = "status"       # Status check request
    FEEDBACK = "feedback"   # Feedback on recent work
    BREAK = "break"         # Taking a break
    UNKNOWN = "unknown"     # Couldn't categorize


class PriorityLevel(Enum):
    """Task priority levels"""
    URGENT = 10      # Do immediately
    HIGH = 8         # Do today
    MEDIUM = 5       # Do this week
    LOW = 3          # Do eventually
    SOMEDAY = 1      # Maybe someday


@dataclass
class ParsedIntent:
    """Structured representation of parsed user intent"""
    raw_input: str
    category: IntentCategory
    priority: PriorityLevel
    title: str
    description: str
    tags: List[str] = field(default_factory=list)
    deadline: Optional[str] = None
    related_goal_id: Optional[int] = None
    confidence: float = 0.5
    context: Dict[str, Any] = field(default_factory=dict)

    def to_task_dict(self) -> Dict[str, Any]:
        """Convert to agent-runtime task format"""
        return {
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "metadata": json.dumps({
                "source": "intent_capture_stream",
                "category": self.category.value,
                "tags": self.tags,
                "deadline": self.deadline,
                "confidence": self.confidence,
                "raw_input": self.raw_input,
                "captured_at": datetime.now().isoformat()
            }),
            "goal_id": self.related_goal_id
        }


class IntentParser:
    """
    Parses natural language input into structured intent.

    Uses pattern matching and keyword detection for fast local parsing.
    Falls back to LLM for complex/ambiguous inputs.
    """

    # Priority keywords
    URGENT_KEYWORDS = ["urgent", "asap", "immediately", "now", "critical", "emergency", "today"]
    HIGH_KEYWORDS = ["important", "soon", "need to", "should", "priority"]
    LOW_KEYWORDS = ["eventually", "someday", "maybe", "when I have time", "no rush"]

    # Category patterns
    TASK_PATTERNS = [
        r"^(need to|have to|must|should|gotta|gonna|will|want to)\s+",
        r"^(do|make|create|build|fix|update|add|remove|change|implement)\s+",
        r"^(remind me to|don't forget to|remember to)\s+",
        r"(urgent|critical|emergency|asap|immediately)",  # Urgency implies task
        r"(is down|broken|not working|crashed|failed)",  # Problem implies task
        r"^(maybe|eventually|we should|let's)\s+.*(refactor|clean|improve|update|fix)",
    ]

    QUESTION_PATTERNS = [
        r"^(what|how|why|when|where|who|which|can|could|would|is|are|do|does)\s+.*\??$",
        r"^(find out|research|look into|investigate|check)\s+",
        r"\?$",  # Ends with question mark
    ]

    IDEA_PATTERNS = [
        r"^(idea:|thought:|what if|maybe we could|wouldn't it be cool if)",
        r"^(i was thinking|just occurred to me|random thought)",
        r"^(could we|we could|might be nice to)\s+",
    ]

    PRIORITY_PATTERNS = [
        r"^(prioritize|reprioritize|focus on|main priority|top priority)",
        r"^(most important|first thing|before anything)",
        r"(focus on|concentrate on|priority is)\s+",
    ]

    STATUS_PATTERNS = [
        r"(status|what's happening|what are you working on|progress)",
        r"^(show me|list|what tasks|what's pending)",
        r"(what's the status|how's it going|where are we)",
    ]

    BREAK_PATTERNS = [
        r"^(taking a break|stepping away|be back|brb|going to|heading out)",
        r"(need a break|grabbing coffee|lunch break|stepping out)",
    ]

    def __init__(self):
        self.compiled_patterns = {
            IntentCategory.TASK: [re.compile(p, re.IGNORECASE) for p in self.TASK_PATTERNS],
            IntentCategory.QUESTION: [re.compile(p, re.IGNORECASE) for p in self.QUESTION_PATTERNS],
            IntentCategory.IDEA: [re.compile(p, re.IGNORECASE) for p in self.IDEA_PATTERNS],
            IntentCategory.PRIORITY: [re.compile(p, re.IGNORECASE) for p in self.PRIORITY_PATTERNS],
            IntentCategory.STATUS: [re.compile(p, re.IGNORECASE) for p in self.STATUS_PATTERNS],
            IntentCategory.BREAK: [re.compile(p, re.IGNORECASE) for p in self.BREAK_PATTERNS],
        }

    def parse(self, raw_input: str, context: Dict[str, Any] = None) -> ParsedIntent:
        """Parse raw input into structured intent"""
        context = context or {}
        text = raw_input.strip()

        # Detect category
        category = self._detect_category(text)

        # Detect priority
        priority = self._detect_priority(text, context)

        # Extract title and description
        title, description = self._extract_title_description(text, category)

        # Extract tags
        tags = self._extract_tags(text)

        # Calculate confidence
        confidence = self._calculate_confidence(text, category)

        return ParsedIntent(
            raw_input=raw_input,
            category=category,
            priority=priority,
            title=title,
            description=description,
            tags=tags,
            confidence=confidence,
            context=context
        )

    def _detect_category(self, text: str) -> IntentCategory:
        """Detect intent category from text.

        Priority order (most specific first):
        1. BREAK - Clear intent signals
        2. STATUS - Specific status queries
        3. PRIORITY - Reprioritization requests
        4. IDEA - Explicitly marked ideas
        5. TASK - Action-oriented statements
        6. QUESTION - Generic questions (catch-all)
        """
        # Check in priority order (most specific to least)
        check_order = [
            IntentCategory.BREAK,
            IntentCategory.STATUS,
            IntentCategory.PRIORITY,
            IntentCategory.IDEA,
            IntentCategory.TASK,
            IntentCategory.QUESTION,  # Most generic, check last
        ]

        for category in check_order:
            patterns = self.compiled_patterns.get(category, [])
            for pattern in patterns:
                if pattern.search(text):
                    return category
        return IntentCategory.UNKNOWN

    def _detect_priority(self, text: str, context: Dict[str, Any]) -> PriorityLevel:
        """Detect priority level from text and context"""
        text_lower = text.lower()

        # Check keywords
        if any(kw in text_lower for kw in self.URGENT_KEYWORDS):
            return PriorityLevel.URGENT
        if any(kw in text_lower for kw in self.HIGH_KEYWORDS):
            return PriorityLevel.HIGH
        if any(kw in text_lower for kw in self.LOW_KEYWORDS):
            return PriorityLevel.LOW

        # Context-based priority
        hour = datetime.now().hour
        if 9 <= hour <= 12:  # Morning = higher default priority
            return PriorityLevel.HIGH
        elif 13 <= hour <= 17:  # Afternoon = medium
            return PriorityLevel.MEDIUM
        else:  # Evening/night = lower (probably less urgent)
            return PriorityLevel.LOW

        return PriorityLevel.MEDIUM

    def _extract_title_description(self, text: str, category: IntentCategory) -> Tuple[str, str]:
        """Extract title and description from text"""
        # Clean up common prefixes
        clean_text = text
        prefixes_to_remove = [
            "need to ", "have to ", "must ", "should ", "gotta ", "gonna ",
            "remind me to ", "don't forget to ", "remember to ",
            "idea: ", "thought: ", "what if ", "maybe we could ",
        ]
        for prefix in prefixes_to_remove:
            if clean_text.lower().startswith(prefix):
                clean_text = clean_text[len(prefix):]
                break

        # Title is first sentence or first 50 chars
        sentences = clean_text.split(". ")
        if len(sentences) > 1:
            title = sentences[0][:80]
            description = clean_text
        else:
            title = clean_text[:80]
            description = clean_text

        # Capitalize title
        title = title.strip().capitalize()

        return title, description

    def _extract_tags(self, text: str) -> List[str]:
        """Extract hashtags and inferred tags from text"""
        tags = []

        # Explicit hashtags
        hashtags = re.findall(r"#(\w+)", text)
        tags.extend(hashtags)

        # Inferred tags based on keywords
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["bug", "fix", "error", "broken"]):
            tags.append("bugfix")
        if any(kw in text_lower for kw in ["feature", "add", "new", "implement"]):
            tags.append("feature")
        if any(kw in text_lower for kw in ["refactor", "clean", "improve"]):
            tags.append("refactor")
        if any(kw in text_lower for kw in ["doc", "readme", "documentation"]):
            tags.append("docs")
        if any(kw in text_lower for kw in ["test", "testing"]):
            tags.append("testing")

        return list(set(tags))

    def _calculate_confidence(self, text: str, category: IntentCategory) -> float:
        """Calculate confidence in the parsing"""
        base_confidence = 0.5

        # Higher confidence for clear category matches
        if category != IntentCategory.UNKNOWN:
            base_confidence += 0.2

        # Higher confidence for longer, clearer input
        word_count = len(text.split())
        if word_count >= 5:
            base_confidence += 0.1
        if word_count >= 10:
            base_confidence += 0.1

        # Lower confidence for very short or ambiguous input
        if word_count < 3:
            base_confidence -= 0.2

        return min(1.0, max(0.1, base_confidence))


class IntentCaptureStream:
    """
    Main intent capture stream - the translation layer.

    Responsibilities:
    1. Proactive prompting at appropriate intervals
    2. Voice/text input capture
    3. Intent parsing and structuring
    4. Task creation in agent-runtime
    5. Pattern learning for improvement
    """

    def __init__(self):
        self.parser = IntentParser()
        self.state = self._load_state()
        self.running = False

        # Session tracking
        self.session_intents: List[ParsedIntent] = []
        self.last_prompt_time: Optional[datetime] = None
        self.prompt_count = 0

        # Priority Engine integration
        self.priority_engine = None
        if PRIORITY_ENGINE_AVAILABLE:
            try:
                self.priority_engine = PriorityEngine()
                logger.info("Priority Engine initialized")
            except Exception as e:
                logger.warning(f"Priority Engine init failed: {e}")

        # Intent Task Translator integration
        self.translator = None
        if TRANSLATOR_AVAILABLE:
            try:
                self.translator = IntentTaskTranslator()
                logger.info("Intent Task Translator initialized")
            except Exception as e:
                logger.warning(f"Translator init failed: {e}")

        # Proactive Surface integration
        self.proactive_surface = None
        if PROACTIVE_SURFACE_AVAILABLE:
            try:
                self.proactive_surface = ProactiveSurface()
                logger.info("Proactive Surface initialized")
            except Exception as e:
                logger.warning(f"Proactive Surface init failed: {e}")

    def _load_state(self) -> Dict[str, Any]:
        """Load persistent state"""
        if INTENT_STATE_FILE.exists():
            try:
                with open(INTENT_STATE_FILE) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
        return {
            "total_intents_captured": 0,
            "total_tasks_created": 0,
            "patterns_learned": [],
            "last_active": None
        }

    def _save_state(self):
        """Save persistent state"""
        try:
            self.state["last_active"] = datetime.now().isoformat()
            with open(INTENT_STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save state: {e}")

    async def voice_prompt(self, message: str, wait_for_response: bool = True) -> Optional[str]:
        """
        Send voice prompt via voice-mode MCP and optionally wait for response.

        Uses the converse tool for natural back-and-forth.
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Use voice-mode MCP's converse endpoint
                payload = {
                    "message": message,
                    "wait_for_response": wait_for_response,
                    "listen_duration": 30.0,  # 30 seconds to respond
                    "min_listen_duration": 2.0,
                }

                async with session.post(
                    f"{VOICE_MODE_URL}/converse",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("response") or result.get("transcript")
                    else:
                        logger.warning(f"Voice prompt failed: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Voice prompt error: {e}")
            return None

    async def proactive_prompt(self, context: Dict[str, Any] = None) -> Optional[ParsedIntent]:
        """
        Send a proactive "What's on your mind?" prompt.

        Returns parsed intent if user responds, None if no response.
        """
        context = context or {}

        # Select appropriate prompt based on context
        prompt = self._select_proactive_prompt(context)

        logger.info(f"Sending proactive prompt: {prompt}")
        response = await self.voice_prompt(prompt, wait_for_response=True)

        self.last_prompt_time = datetime.now()
        self.prompt_count += 1

        if response and response.strip():
            # Check for dismissal
            dismissals = ["nothing", "never mind", "not now", "no", "nope", "all good", "i'm good"]
            if response.strip().lower() in dismissals:
                logger.info("User dismissed prompt")
                return None

            # Parse the response
            intent = self.parser.parse(response, context)
            self.session_intents.append(intent)
            self.state["total_intents_captured"] += 1
            self._save_state()

            return intent

        return None

    def _select_proactive_prompt(self, context: Dict[str, Any]) -> str:
        """Select appropriate prompt based on context"""
        hour = datetime.now().hour

        # Morning prompts
        if 6 <= hour < 10:
            prompts = [
                "Good morning! What's the main thing you want to accomplish today?",
                "Morning! Any thoughts or tasks on your mind?",
                "Starting the day - what should we focus on first?",
            ]
        # Midday prompts
        elif 10 <= hour < 14:
            prompts = [
                "How's it going? Anything you need to capture?",
                "Quick check-in - any new priorities or thoughts?",
                "Anything on your mind I should know about?",
            ]
        # Afternoon prompts
        elif 14 <= hour < 18:
            prompts = [
                "Afternoon check - any tasks or ideas to add?",
                "What's on your mind right now?",
                "Any thoughts to capture before they slip away?",
            ]
        # Evening prompts
        elif 18 <= hour < 22:
            prompts = [
                "Evening wrap-up - anything to note for tomorrow?",
                "Any last thoughts to capture today?",
                "Anything we should tackle tomorrow?",
            ]
        # Late night prompts
        else:
            prompts = [
                "Burning the midnight oil - anything to capture?",
                "Late night thought dump - what's on your mind?",
            ]

        # Rotate through prompts based on count
        return prompts[self.prompt_count % len(prompts)]

    async def capture_intent(self, raw_input: str, source: str = "voice",
                            context: Dict[str, Any] = None) -> ParsedIntent:
        """
        Capture and parse a user intent from any source.

        Args:
            raw_input: The raw user input (text or transcribed speech)
            source: Where the input came from (voice, text, email, etc.)
            context: Additional context (time, location, recent activity)

        Returns:
            ParsedIntent object
        """
        context = context or {}
        context["source"] = source
        context["captured_at"] = datetime.now().isoformat()

        intent = self.parser.parse(raw_input, context)

        self.session_intents.append(intent)
        self.state["total_intents_captured"] += 1
        self._save_state()

        logger.info(f"Captured intent: [{intent.category.value}] {intent.title} (confidence: {intent.confidence:.2f})")

        return intent

    async def create_task_from_intent(self, intent: ParsedIntent) -> Optional[int]:
        """
        Create a task in agent-runtime-mcp from parsed intent.

        Returns task ID if created, None if failed.
        """
        if intent.category not in [IntentCategory.TASK, IntentCategory.IDEA]:
            logger.info(f"Skipping task creation for {intent.category.value} intent")
            return None

        if intent.confidence < 0.4:
            logger.info(f"Skipping low-confidence intent ({intent.confidence:.2f})")
            return None

        try:
            if not AGENT_RUNTIME_DB.exists():
                logger.warning("Agent runtime database not found")
                return None

            conn = sqlite3.connect(AGENT_RUNTIME_DB)
            cursor = conn.cursor()

            task_data = intent.to_task_dict()

            cursor.execute("""
                INSERT INTO tasks (title, description, status, priority, goal_id, metadata, created_at)
                VALUES (?, ?, 'pending', ?, ?, ?, ?)
            """, (
                task_data["title"],
                task_data["description"],
                task_data["priority"],
                task_data.get("goal_id"),
                task_data["metadata"],
                datetime.now().isoformat()
            ))

            task_id = cursor.lastrowid
            conn.commit()
            conn.close()

            self.state["total_tasks_created"] += 1
            self._save_state()

            logger.info(f"Created task {task_id}: {task_data['title']}")

            # Score task with Priority Engine
            priority_info = ""
            if self.priority_engine:
                task_for_scoring = {
                    "id": task_id,
                    "title": task_data["title"],
                    "description": task_data["description"],
                    "priority": task_data["priority"],
                    "metadata": task_data["metadata"]
                }
                scored = self.priority_engine.score_task(task_for_scoring)
                priority_info = f" Score: {scored.final_score:.0f}, {scored.quadrant.value}."
                logger.info(f"Task {task_id} scored: {scored.final_score:.1f} ({scored.quadrant.value})")

            # Voice confirmation
            await self.voice_prompt(
                f"Got it. Added '{task_data['title']}' with {intent.priority.name.lower()} priority.{priority_info}",
                wait_for_response=False
            )

            return task_id

        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return None

    async def handle_status_request(self) -> str:
        """Handle a status check request with Priority Engine intelligence"""
        try:
            if not AGENT_RUNTIME_DB.exists():
                return "No tasks in the queue."

            # Use Priority Engine if available
            if self.priority_engine:
                prioritized = self.priority_engine.get_prioritized_queue(limit=5)
                suggested = self.priority_engine.suggest_next_task()

                if not prioritized:
                    return "All clear! No pending tasks."

                # Get in-progress from database
                conn = sqlite3.connect(AGENT_RUNTIME_DB)
                cursor = conn.cursor()
                cursor.execute("SELECT title FROM tasks WHERE status = 'in_progress' LIMIT 3")
                in_progress = cursor.fetchall()
                conn.close()

                status_parts = []

                if in_progress:
                    tasks = ", ".join(t[0] for t in in_progress)
                    status_parts.append(f"Working on: {tasks}.")

                # Group by quadrant
                q1 = [t for t in prioritized if t.quadrant.value == "Q1_do"]
                q2 = [t for t in prioritized if t.quadrant.value == "Q2_schedule"]

                if q1:
                    status_parts.append(f"{len(q1)} urgent tasks need attention.")
                if q2:
                    status_parts.append(f"{len(q2)} important tasks to schedule.")

                if suggested:
                    status_parts.append(f"Suggested next: {suggested.title}")

                return " ".join(status_parts) if status_parts else "All clear!"

            # Fallback to basic status
            conn = sqlite3.connect(AGENT_RUNTIME_DB)
            cursor = conn.cursor()

            # Get pending tasks
            cursor.execute("""
                SELECT title, priority FROM tasks
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT 5
            """)

            pending = cursor.fetchall()

            # Get in-progress tasks
            cursor.execute("""
                SELECT title FROM tasks
                WHERE status = 'in_progress'
                LIMIT 3
            """)

            in_progress = cursor.fetchall()

            conn.close()

            # Build status message
            if not pending and not in_progress:
                return "All clear! No pending tasks."

            status_parts = []

            if in_progress:
                tasks = ", ".join(t[0] for t in in_progress)
                status_parts.append(f"Currently working on: {tasks}")

            if pending:
                count = len(pending)
                top_task = pending[0][0] if pending else None
                status_parts.append(f"{count} pending tasks. Top priority: {top_task}")

            return " ".join(status_parts)

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return "Sorry, couldn't check status right now."

    async def process_intent(self, intent: ParsedIntent) -> str:
        """
        Process a parsed intent and take appropriate action.

        Returns a response message.
        """
        if intent.category == IntentCategory.TASK or intent.category == IntentCategory.IDEA:
            # Check if this is a complex intent that should be decomposed
            if self.translator and self._is_complex_intent(intent.raw_input):
                graph = await self.translator.translate(intent)
                if len(graph.tasks) > 1:
                    # Complex intent - persist as goal with tasks
                    try:
                        await self.translator._persist_graph(graph)
                        template_info = f" (template: {graph.template_used})" if graph.template_used else ""
                        return f"Created goal '{graph.goal_title}' with {len(graph.tasks)} tasks{template_info}"
                    except Exception as e:
                        logger.error(f"Failed to persist task graph: {e}")
                        # Fall back to simple task creation

            # Simple intent - create single task
            task_id = await self.create_task_from_intent(intent)
            if task_id:
                return f"Created task: {intent.title}"
            else:
                return f"Captured: {intent.title} (not added to task queue)"

        elif intent.category == IntentCategory.STATUS:
            return await self.handle_status_request()

        elif intent.category == IntentCategory.QUESTION:
            return f"Good question. I'll look into: {intent.title}"

        elif intent.category == IntentCategory.PRIORITY:
            return f"Noted priority change: {intent.title}"

        elif intent.category == IntentCategory.BREAK:
            return "Enjoy your break! I'll be here when you get back."

        elif intent.category == IntentCategory.FEEDBACK:
            return f"Thanks for the feedback: {intent.title}"

        else:
            return f"Captured: {intent.raw_input}"

    def _is_complex_intent(self, text: str) -> bool:
        """Check if intent should be decomposed into multiple tasks"""
        import re

        # Check for compound indicators
        compound_patterns = [
            r'\s+and\s+(then\s+)?',
            r'\s+then\s+',
            r',\s*',
            r';\s*',
            r'first\s+.*\s+then',
            r'after\s+that'
        ]

        for pattern in compound_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True

        # Check for workflow template matches
        if TRANSLATOR_AVAILABLE:
            from intent_task_translator import WorkflowTemplates
            if WorkflowTemplates.match_template(text):
                return True

        return False

    def should_prompt(self, human_present: bool, last_activity_minutes: float) -> bool:
        """
        Determine if we should send a proactive prompt.

        Considers:
        - Human presence
        - Time since last prompt
        - Activity level
        """
        if not human_present:
            return False

        if self.last_prompt_time is None:
            return True

        minutes_since_prompt = (datetime.now() - self.last_prompt_time).total_seconds() / 60

        # Adaptive interval based on activity
        if last_activity_minutes < 5:
            # Very active - longer interval (don't interrupt)
            min_interval = PROACTIVE_PROMPT_INTERVAL_ACTIVE / 60
        elif last_activity_minutes < 30:
            # Moderately active
            min_interval = PROACTIVE_PROMPT_INTERVAL_IDLE / 60 / 2
        else:
            # Idle - shorter interval (engage)
            min_interval = PROACTIVE_PROMPT_INTERVAL_MIN / 60

        return minutes_since_prompt >= min_interval

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session's captured intents"""
        return {
            "intents_captured": len(self.session_intents),
            "by_category": {
                cat.value: len([i for i in self.session_intents if i.category == cat])
                for cat in IntentCategory
            },
            "prompts_sent": self.prompt_count,
            "total_historical": self.state["total_intents_captured"],
            "total_tasks_created": self.state["total_tasks_created"]
        }

    async def check_proactive_surface(self) -> List[Dict]:
        """
        Check for proactive surfacing opportunities.

        This integrates with the Proactive Surface component to
        intelligently surface tasks and context at the right time.

        Returns:
            List of surfaced items with their presentation results
        """
        if not self.proactive_surface:
            return []

        try:
            # Surface items based on triggers
            results = await self.proactive_surface.surface()

            # Update activity tracking
            if results:
                self.proactive_surface.update_activity()

            return results
        except Exception as e:
            logger.warning(f"Error in proactive surfacing: {e}")
            return []

    def update_surface_context(self, focus: Optional[str] = None):
        """
        Update the proactive surface with current context.

        Call this when the user's focus or activity changes.

        Args:
            focus: Current focus/task the user is working on
        """
        if self.proactive_surface:
            self.proactive_surface.update_activity(focus=focus)

    def record_surface_response(self, item_id: str, response: str):
        """
        Record user response to a surfaced item.

        This helps the system learn and improve surfacing decisions.

        Args:
            item_id: ID of the surfaced item
            response: User response (engaged, dismissed, snoozed)
        """
        if self.proactive_surface:
            self.proactive_surface.record_response(item_id, response)

    def get_surface_stats(self) -> Dict[str, Any]:
        """
        Get proactive surfacing statistics.

        Returns engagement rates and patterns.
        """
        if self.proactive_surface:
            return self.proactive_surface.get_engagement_stats()
        return {}


# Integration with ConsciousnessDaemon
class IntentCaptureIntegration:
    """
    Integration layer to connect IntentCaptureStream with ConsciousnessDaemon.

    Adds intent capture to the OODA loop:
    - OBSERVE: Check for human presence, activity level
    - ORIENT: Determine if proactive prompt is appropriate
    - DECIDE: Include intent capture in decisions
    - ACT: Execute proactive prompts
    """

    def __init__(self, consciousness_daemon):
        self.daemon = consciousness_daemon
        self.intent_stream = IntentCaptureStream()

    async def integrate_with_decide(self, orientation: Dict[str, Any], decisions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Integrate intent capture with the DECIDE phase.

        Adds proactive prompting to decisions when appropriate.
        """
        attention_items = orientation.get("attention_items", [])

        # Check human presence
        human_present = any(i["item"] == "human_present" for i in attention_items)

        # Calculate time since last activity
        last_activity = self.daemon.state["working_memory"].get("last_activity")
        if last_activity:
            last_activity_dt = datetime.fromisoformat(last_activity)
            minutes_since_activity = (datetime.now() - last_activity_dt).total_seconds() / 60
        else:
            minutes_since_activity = 999  # No recorded activity

        # Determine if we should prompt
        if self.intent_stream.should_prompt(human_present, minutes_since_activity):
            decisions["actions"].append({
                "type": "proactive_prompt",
                "context": {
                    "human_present": human_present,
                    "minutes_since_activity": minutes_since_activity
                }
            })

        return decisions

    async def execute_prompt_action(self, action: Dict[str, Any]) -> Optional[ParsedIntent]:
        """Execute a proactive prompt action"""
        if action.get("type") != "proactive_prompt":
            return None

        context = action.get("context", {})
        intent = await self.intent_stream.proactive_prompt(context)

        if intent:
            # Process the intent
            response = await self.intent_stream.process_intent(intent)
            logger.info(f"Intent processed: {response}")
            return intent

        return None


# CLI for testing
async def test_intent_capture():
    """Test the intent capture stream"""
    stream = IntentCaptureStream()

    print("Intent Capture Stream Test")
    print("=" * 50)

    # Test parsing
    test_inputs = [
        "Need to fix the bug in the login page",
        "Idea: what if we added voice commands to the dashboard?",
        "What's the status of the project?",
        "This is urgent - the server is down!",
        "Maybe eventually we should refactor the database layer",
        "Taking a break, be back in 20",
    ]

    for input_text in test_inputs:
        intent = await stream.capture_intent(input_text, source="test")
        print(f"\nInput: {input_text}")
        print(f"  Category: {intent.category.value}")
        print(f"  Priority: {intent.priority.name}")
        print(f"  Title: {intent.title}")
        print(f"  Tags: {intent.tags}")
        print(f"  Confidence: {intent.confidence:.2f}")

    print("\n" + "=" * 50)
    print("Session Summary:")
    print(json.dumps(stream.get_session_summary(), indent=2))


if __name__ == "__main__":
    asyncio.run(test_intent_capture())
