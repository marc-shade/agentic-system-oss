#!/usr/bin/env python3
"""
TPU Session Context Classifier - Edge TPU Accelerated Session Analysis

Classifies session context and work patterns using semantic embeddings.
Enables intelligent context restoration, session summarization, and
workflow optimization.

Integration with enhanced-memory session tracking.

Usage:
    from tpu_session_classifier import TPUSessionClassifier

    classifier = TPUSessionClassifier()
    context = await classifier.classify_session(
        messages=conversation_history,
        files_modified=["src/cache.py", "tests/test_cache.py"],
        tools_used=["Read", "Edit", "Bash"]
    )
    print(f"Session type: {context.session_type}")
"""
import platform

import os
import sys
import json
import time
import logging
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import Counter

# Add hooks path
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
HOOKS_PATH = os.path.join(AGENTIC_SYSTEM_PATH, "scripts/hooks")
if HOOKS_PATH not in sys.path:
    sys.path.insert(0, HOOKS_PATH)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_session_classifier")

# TPU imports
TPU_AVAILABLE = False
_embed_text = None

try:
    from tpu_importance import embed_text, is_tpu_available
    if is_tpu_available():
        _embed_text = embed_text
        TPU_AVAILABLE = True
except ImportError:
    pass

try:
    from tpu_monitor import record_tpu_usage
    HAS_TPU_MONITOR = True
except ImportError:
    HAS_TPU_MONITOR = False


class SessionType(Enum):
    """Types of work sessions"""
    FEATURE_DEVELOPMENT = "feature_development"
    BUG_FIXING = "bug_fixing"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    RESEARCH = "research"
    EXPLORATION = "exploration"
    CONFIGURATION = "configuration"
    REVIEW = "review"
    DEPLOYMENT = "deployment"
    LEARNING = "learning"
    PLANNING = "planning"
    MIXED = "mixed"


class SessionPhase(Enum):
    """Phase within a session"""
    STARTING = "starting"
    EXPLORING = "exploring"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    REFINING = "refining"
    COMPLETING = "completing"
    STUCK = "stuck"


@dataclass
class SessionContext:
    """Analyzed session context"""
    session_type: SessionType
    session_phase: SessionPhase
    type_confidence: float
    phase_confidence: float
    topics: List[str]  # Main topics discussed/worked on
    key_files: List[str]  # Most important files
    tool_profile: Dict[str, int]  # Tool usage counts
    estimated_progress: float  # 0.0-1.0
    complexity_score: float  # 0.0-1.0
    momentum: str  # accelerating, steady, slowing, stalled
    summary: str
    continuation_hints: List[str]  # Hints for continuing work
    latency_ms: float


# Session type templates
SESSION_TEMPLATES = {
    SessionType.FEATURE_DEVELOPMENT: (
        "Implementing new features, adding functionality, creating new modules. "
        "Building new capabilities, extending the system, adding user-facing features."
    ),
    SessionType.BUG_FIXING: (
        "Fixing bugs, resolving errors, patching issues. "
        "Correcting unexpected behavior, fixing crashes, resolving defects."
    ),
    SessionType.REFACTORING: (
        "Refactoring code, restructuring without changing behavior. "
        "Improving code quality, cleaning up, reorganizing modules."
    ),
    SessionType.DEBUGGING: (
        "Investigating issues, tracing problems, analyzing errors. "
        "Understanding unexpected behavior, finding root causes, diagnostics."
    ),
    SessionType.TESTING: (
        "Writing tests, running test suites, verifying functionality. "
        "Test-driven development, coverage improvement, validation."
    ),
    SessionType.DOCUMENTATION: (
        "Writing documentation, updating README, explaining code. "
        "Creating guides, adding comments, documenting APIs."
    ),
    SessionType.RESEARCH: (
        "Researching solutions, reading documentation, exploring options. "
        "Learning about technologies, investigating approaches."
    ),
    SessionType.EXPLORATION: (
        "Exploring codebase, understanding structure, reading code. "
        "Familiarizing with the system, code review, discovery."
    ),
    SessionType.CONFIGURATION: (
        "Configuring settings, updating configuration files, environment setup. "
        "DevOps work, infrastructure configuration, system settings."
    ),
    SessionType.REVIEW: (
        "Reviewing code changes, pull request review, quality assessment. "
        "Evaluating implementations, providing feedback."
    ),
    SessionType.DEPLOYMENT: (
        "Deploying to production, releasing versions, CI/CD work. "
        "Release management, deployment pipelines, production updates."
    ),
    SessionType.LEARNING: (
        "Learning new concepts, understanding documentation, tutorials. "
        "Skill development, knowledge acquisition, studying."
    ),
    SessionType.PLANNING: (
        "Planning implementation, designing architecture, making decisions. "
        "Project planning, technical design, roadmap discussion."
    )
}

# Phase templates
PHASE_TEMPLATES = {
    SessionPhase.STARTING: "Just beginning, initial exploration, getting started, opening files",
    SessionPhase.EXPLORING: "Exploring options, reading code, understanding the problem",
    SessionPhase.IMPLEMENTING: "Actively writing code, making changes, implementing solution",
    SessionPhase.TESTING: "Running tests, verifying changes, checking functionality",
    SessionPhase.REFINING: "Polishing, fixing small issues, improving implementation",
    SessionPhase.COMPLETING: "Wrapping up, final commits, completion tasks",
    SessionPhase.STUCK: "Blocked, waiting, unclear path forward, confused"
}


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class TPUSessionClassifier:
    """
    Classify session context using TPU embeddings.

    Analyzes conversation, file patterns, and tool usage to
    understand what type of work is being done.
    """

    def __init__(self):
        self.use_tpu = TPU_AVAILABLE
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # Precompute template embeddings
        self._type_embeddings = self._precompute_templates(SESSION_TEMPLATES)
        self._phase_embeddings = self._precompute_templates(PHASE_TEMPLATES)

        if self.use_tpu:
            logger.info("TPU session classification enabled")
        else:
            logger.info("Using fallback session classification")

    def _precompute_templates(self, templates: Dict) -> Dict:
        """Precompute embeddings for templates."""
        embeddings = {}
        if not self.use_tpu or not _embed_text:
            return embeddings

        for key, template in templates.items():
            try:
                embedding = _embed_text(template)
                if embedding is not None:
                    embeddings[key] = np.array(embedding, dtype=np.float32)
            except Exception as e:
                logger.warning(f"Failed to embed template {key}: {e}")

        return embeddings

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding with caching."""
        cache_key = str(hash(text[:500]))  # Limit key length
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        if not self.use_tpu or not _embed_text:
            return None

        try:
            start = time.perf_counter()
            embedding = _embed_text(text[:1000])  # Limit text length
            latency = (time.perf_counter() - start) * 1000

            if embedding is not None:
                emb_array = np.array(embedding, dtype=np.float32)
                self._embedding_cache[cache_key] = emb_array

                if HAS_TPU_MONITOR:
                    record_tpu_usage(
                        "session_embedding",
                        latency_ms=latency,
                        source="session_classifier"
                    )
                return emb_array
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")

        return None

    def _extract_topics(self, messages: List[str], files: List[str]) -> List[str]:
        """Extract main topics from messages and files."""
        # Combine text for analysis
        all_text = " ".join(messages[:20])  # Last 20 messages

        # Common topic keywords
        topic_patterns = {
            "caching": ["cache", "caching", "cached", "lru", "ttl"],
            "authentication": ["auth", "login", "password", "token", "jwt"],
            "database": ["database", "db", "sql", "query", "migration"],
            "api": ["api", "endpoint", "rest", "graphql", "route"],
            "testing": ["test", "unittest", "pytest", "mock", "coverage"],
            "performance": ["performance", "optimize", "latency", "speed"],
            "memory": ["memory", "leak", "allocation", "gc"],
            "error_handling": ["error", "exception", "try", "catch", "handle"],
            "logging": ["log", "logging", "debug", "trace"],
            "configuration": ["config", "settings", "env", "environment"]
        }

        text_lower = all_text.lower()
        topics = []

        for topic, keywords in topic_patterns.items():
            if any(kw in text_lower for kw in keywords):
                topics.append(topic)

        # Add topics from file paths
        for file_path in files[:10]:
            parts = Path(file_path).parts
            for part in parts:
                if part not in ["src", "lib", "tests", "test", "."]:
                    if part not in topics and len(part) > 2:
                        topics.append(part.replace("_", " ").replace("-", " "))

        return topics[:5]  # Top 5 topics

    def _analyze_tool_usage(self, tools: List[str]) -> Dict[str, Any]:
        """Analyze tool usage patterns."""
        counts = Counter(tools)

        total = sum(counts.values())
        profile = {
            "read_heavy": counts.get("Read", 0) / max(total, 1) > 0.4,
            "edit_heavy": counts.get("Edit", 0) / max(total, 1) > 0.3,
            "bash_heavy": counts.get("Bash", 0) / max(total, 1) > 0.3,
            "write_heavy": counts.get("Write", 0) / max(total, 1) > 0.2
        }

        # Infer activity
        if profile["read_heavy"] and not profile["edit_heavy"]:
            activity = "exploration"
        elif profile["edit_heavy"]:
            activity = "implementation"
        elif profile["bash_heavy"]:
            activity = "testing_or_debugging"
        else:
            activity = "mixed"

        return {
            "counts": dict(counts),
            "profile": profile,
            "primary_activity": activity
        }

    def _estimate_progress(
        self,
        messages: List[str],
        tools: List[str],
        files_modified: List[str]
    ) -> float:
        """Estimate session progress (0.0-1.0)."""
        # Indicators of progress
        progress_indicators = 0

        # Files modified = progress
        if len(files_modified) > 0:
            progress_indicators += min(0.3, len(files_modified) * 0.1)

        # Edit operations = progress
        edit_count = sum(1 for t in tools if t in ["Edit", "Write"])
        progress_indicators += min(0.3, edit_count * 0.05)

        # Completion words in recent messages
        completion_words = ["done", "complete", "finished", "works", "fixed", "implemented"]
        recent_text = " ".join(messages[-5:]).lower()
        if any(word in recent_text for word in completion_words):
            progress_indicators += 0.2

        # Tests passing
        if "test" in recent_text and ("pass" in recent_text or "success" in recent_text):
            progress_indicators += 0.2

        return min(1.0, progress_indicators)

    def _assess_momentum(
        self,
        tools: List[str],
        messages: List[str]
    ) -> str:
        """Assess session momentum."""
        if len(tools) < 5:
            return "starting"

        # Look at recent tool activity rate
        recent_tools = tools[-10:]
        earlier_tools = tools[-20:-10] if len(tools) > 10 else []

        recent_rate = len(recent_tools) / 10
        earlier_rate = len(earlier_tools) / 10 if earlier_tools else recent_rate

        if recent_rate > earlier_rate * 1.2:
            return "accelerating"
        elif recent_rate < earlier_rate * 0.5:
            return "slowing"
        elif recent_rate < 0.3:
            return "stalled"
        else:
            return "steady"

    async def classify_session(
        self,
        messages: List[str],
        files_modified: Optional[List[str]] = None,
        tools_used: Optional[List[str]] = None,
        session_duration_minutes: Optional[int] = None
    ) -> SessionContext:
        """
        Classify session context.

        Args:
            messages: Conversation messages
            files_modified: List of modified file paths
            tools_used: List of tools used in order
            session_duration_minutes: How long session has been active

        Returns:
            SessionContext with classification and analysis
        """
        start_time = time.perf_counter()

        files_modified = files_modified or []
        tools_used = tools_used or []

        # Build session summary text
        summary_text = " ".join(messages[-10:])  # Recent messages
        if files_modified:
            summary_text += f" Files: {', '.join(files_modified[:5])}"

        session_embedding = self._get_embedding(summary_text)

        # Classify session type
        if session_embedding is not None and self._type_embeddings:
            type_scores = {}
            for session_type, type_emb in self._type_embeddings.items():
                similarity = cosine_similarity(session_embedding, type_emb)
                type_scores[session_type] = similarity

            best_type = max(type_scores, key=type_scores.get)
            type_confidence = type_scores[best_type]
        else:
            best_type, type_confidence = self._keyword_classify_type(messages, files_modified)

        # Classify session phase
        recent_embedding = self._get_embedding(" ".join(messages[-3:]))
        if recent_embedding is not None and self._phase_embeddings:
            phase_scores = {}
            for phase, phase_emb in self._phase_embeddings.items():
                similarity = cosine_similarity(recent_embedding, phase_emb)
                phase_scores[phase] = similarity

            best_phase = max(phase_scores, key=phase_scores.get)
            phase_confidence = phase_scores[best_phase]
        else:
            best_phase = SessionPhase.IMPLEMENTING
            phase_confidence = 0.5

        # Extract topics
        topics = self._extract_topics(messages, files_modified)

        # Analyze tools
        tool_analysis = self._analyze_tool_usage(tools_used)

        # Estimate progress
        progress = self._estimate_progress(messages, tools_used, files_modified)

        # Assess momentum
        momentum = self._assess_momentum(tools_used, messages)

        # Complexity score
        complexity = min(1.0, (
            len(files_modified) * 0.1 +
            len(set(tools_used)) * 0.1 +
            len(topics) * 0.15
        ))

        # Generate summary
        summary = self._generate_summary(best_type, topics, files_modified, progress)

        # Continuation hints
        hints = self._generate_continuation_hints(best_type, best_phase, progress, momentum)

        # Key files (most frequently modified)
        file_counts = Counter(files_modified)
        key_files = [f for f, _ in file_counts.most_common(5)]

        latency_ms = (time.perf_counter() - start_time) * 1000

        if HAS_TPU_MONITOR:
            record_tpu_usage(
                "session_classification",
                latency_ms=latency_ms,
                source="session_classifier",
                metadata={
                    "session_type": best_type.value,
                    "phase": best_phase.value
                }
            )

        return SessionContext(
            session_type=best_type,
            session_phase=best_phase,
            type_confidence=type_confidence,
            phase_confidence=phase_confidence,
            topics=topics,
            key_files=key_files,
            tool_profile=tool_analysis["counts"],
            estimated_progress=progress,
            complexity_score=complexity,
            momentum=momentum,
            summary=summary,
            continuation_hints=hints,
            latency_ms=latency_ms
        )

    def _keyword_classify_type(
        self,
        messages: List[str],
        files: List[str]
    ) -> Tuple[SessionType, float]:
        """Fallback keyword-based type classification."""
        text = " ".join(messages).lower()

        keywords = {
            SessionType.FEATURE_DEVELOPMENT: ["implement", "add", "create", "new feature"],
            SessionType.BUG_FIXING: ["fix", "bug", "issue", "patch"],
            SessionType.REFACTORING: ["refactor", "cleanup", "reorganize"],
            SessionType.DEBUGGING: ["debug", "investigate", "trace", "why"],
            SessionType.TESTING: ["test", "pytest", "unittest", "coverage"],
            SessionType.DOCUMENTATION: ["document", "readme", "docstring"],
            SessionType.RESEARCH: ["research", "find", "look up", "how to"],
            SessionType.EXPLORATION: ["explore", "understand", "read"],
        }

        best_type = SessionType.MIXED
        best_score = 0

        for session_type, kws in keywords.items():
            score = sum(1 for kw in kws if kw in text)
            if score > best_score:
                best_score = score
                best_type = session_type

        confidence = min(0.8, best_score * 0.2) if best_score > 0 else 0.3
        return best_type, confidence

    def _generate_summary(
        self,
        session_type: SessionType,
        topics: List[str],
        files: List[str],
        progress: float
    ) -> str:
        """Generate human-readable session summary."""
        type_desc = session_type.value.replace("_", " ")

        if topics:
            topic_str = ", ".join(topics[:3])
        else:
            topic_str = "general work"

        if files:
            file_count = len(set(files))
            file_str = f"across {file_count} file(s)"
        else:
            file_str = ""

        progress_desc = (
            "just started" if progress < 0.2 else
            "in progress" if progress < 0.6 else
            "nearly complete" if progress < 0.9 else
            "complete"
        )

        return f"{type_desc.title()} session on {topic_str} {file_str} - {progress_desc}"

    def _generate_continuation_hints(
        self,
        session_type: SessionType,
        phase: SessionPhase,
        progress: float,
        momentum: str
    ) -> List[str]:
        """Generate hints for continuing work."""
        hints = []

        if phase == SessionPhase.STUCK:
            hints.append("Consider breaking down the problem into smaller steps")
            hints.append("Try a different approach or seek more information")

        if momentum == "slowing":
            hints.append("Session appears to be winding down")

        if session_type == SessionType.FEATURE_DEVELOPMENT and progress > 0.7:
            hints.append("Consider adding tests for new functionality")

        if session_type == SessionType.BUG_FIXING and progress < 0.3:
            hints.append("Focus on reproducing the issue first")

        if session_type == SessionType.TESTING:
            hints.append("Aim for edge cases and error conditions")

        if not hints:
            hints.append("Continue with current approach")

        return hints

    def get_statistics(self) -> Dict[str, Any]:
        """Get classifier statistics."""
        return {
            "tpu_available": self.use_tpu,
            "type_templates": len(self._type_embeddings),
            "phase_templates": len(self._phase_embeddings),
            "cache_size": len(self._embedding_cache)
        }


# CLI
if __name__ == "__main__":
    import asyncio

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


    classifier = TPUSessionClassifier()
    print(json.dumps(classifier.get_statistics(), indent=2))

    # Test classification
    test_messages = [
        "Let me fix this bug in the cache module",
        "I see the issue - the TTL is not being checked correctly",
        "Let me update the cache.py file",
        "Fixed the TTL check, now running tests",
        "Tests are passing now"
    ]

    context = asyncio.run(classifier.classify_session(
        messages=test_messages,
        files_modified=["src/cache.py", "tests/test_cache.py"],
        tools_used=["Read", "Read", "Edit", "Bash", "Bash"]
    ))

    print(f"\nSession Analysis:")
    print(f"  Type: {context.session_type.value} ({context.type_confidence:.2f})")
    print(f"  Phase: {context.session_phase.value} ({context.phase_confidence:.2f})")
    print(f"  Topics: {context.topics}")
    print(f"  Progress: {context.estimated_progress:.0%}")
    print(f"  Momentum: {context.momentum}")
    print(f"  Summary: {context.summary}")
