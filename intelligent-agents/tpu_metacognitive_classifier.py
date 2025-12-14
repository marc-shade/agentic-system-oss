#!/usr/bin/env python3
"""
TPU Metacognitive State Classifier - Self-Aware Cognitive State Detection

Uses Edge TPU text embeddings to classify the current cognitive state
by comparing context against known state templates.

Cognitive States:
- FOCUSED: Working efficiently on a clear task with high confidence
- EXPLORING: Researching options and gathering information
- CONFUSED: Uncertain about requirements or approach
- STUCK: Blocked by error or missing information
- COMPLETING: Finishing up and verifying work
- REASONING: Deep analytical thinking and problem solving
- DEBUGGING: Investigating errors and troubleshooting
- PLANNING: Designing approach and breaking down tasks

Integration with consciousness daemon and session management.

Usage:
    from tpu_metacognitive_classifier import TPUMetacognitiveClassifier

    classifier = TPUMetacognitiveClassifier()
    state = await classifier.classify_state(
        context="Trying to understand why the test is failing...",
        recent_actions=["read error log", "search for similar issues"]
    )
    print(f"Cognitive State: {state.state} ({state.confidence:.2f})")
"""
import platform

import os
import sys
import json
import time
import logging
import numpy as np
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Add hooks path for tpu_importance
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
HOOKS_PATH = os.path.join(AGENTIC_SYSTEM_PATH, "scripts/hooks")
if HOOKS_PATH not in sys.path:
    sys.path.insert(0, HOOKS_PATH)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_metacognitive_classifier")

# Try to import TPU capabilities
TPU_AVAILABLE = False
_embed_text = None

try:
    from tpu_importance import embed_text, is_tpu_available
    if is_tpu_available():
        _embed_text = embed_text
        TPU_AVAILABLE = True
        logger.info("TPU metacognitive classification enabled")
except ImportError:
    logger.info("TPU not available, using fallback classification")

# Try to import tpu_monitor
try:
    from tpu_monitor import record_tpu_usage
    HAS_TPU_MONITOR = True
except ImportError:
    HAS_TPU_MONITOR = False


class CognitiveState(Enum):
    """Possible cognitive states"""
    FOCUSED = "focused"
    EXPLORING = "exploring"
    CONFUSED = "confused"
    STUCK = "stuck"
    COMPLETING = "completing"
    REASONING = "reasoning"
    DEBUGGING = "debugging"
    PLANNING = "planning"
    IDLE = "idle"


@dataclass
class MetacognitiveResult:
    """Result of metacognitive state classification"""
    state: CognitiveState
    confidence: float  # 0.0-1.0
    all_scores: Dict[str, float]  # Scores for all states
    indicators: List[str]  # Evidence supporting classification
    cognitive_load: float  # 0.0-1.0, estimated mental load
    attention_level: float  # 0.0-1.0, how focused
    latency_ms: float


# State templates - descriptions that characterize each state
STATE_TEMPLATES = {
    CognitiveState.FOCUSED: (
        "Working efficiently on a clear task with high confidence. "
        "Making steady progress, writing code, implementing features. "
        "Clear understanding of what needs to be done."
    ),
    CognitiveState.EXPLORING: (
        "Researching options and gathering information. "
        "Reading documentation, searching for solutions, comparing approaches. "
        "Open-minded investigation without commitment."
    ),
    CognitiveState.CONFUSED: (
        "Uncertain about requirements or approach. "
        "Requirements are unclear, multiple interpretations possible. "
        "Need clarification before proceeding."
    ),
    CognitiveState.STUCK: (
        "Blocked by error or missing information. "
        "Tried multiple approaches without success. "
        "Cannot proceed without resolving blocker."
    ),
    CognitiveState.COMPLETING: (
        "Finishing up and verifying work. "
        "Running tests, checking results, polishing output. "
        "Task nearly done, final verification phase."
    ),
    CognitiveState.REASONING: (
        "Deep analytical thinking and problem solving. "
        "Working through complex logic, mathematical reasoning. "
        "Careful step-by-step deduction."
    ),
    CognitiveState.DEBUGGING: (
        "Investigating errors and troubleshooting. "
        "Analyzing stack traces, checking logs, isolating issues. "
        "Systematic error diagnosis."
    ),
    CognitiveState.PLANNING: (
        "Designing approach and breaking down tasks. "
        "Creating implementation plan, identifying steps. "
        "Strategic thinking about how to proceed."
    ),
    CognitiveState.IDLE: (
        "Waiting for input or between tasks. "
        "No active work in progress. "
        "Ready to start new task."
    )
}

# Action patterns that suggest certain states
ACTION_INDICATORS = {
    CognitiveState.FOCUSED: [
        "writing", "implementing", "coding", "creating", "building",
        "edit", "write", "add", "modify"
    ],
    CognitiveState.EXPLORING: [
        "searching", "reading", "looking", "researching", "investigating",
        "search", "read", "glob", "grep", "find"
    ],
    CognitiveState.CONFUSED: [
        "unclear", "don't understand", "not sure", "confused", "ambiguous",
        "what do you mean", "clarify", "which"
    ],
    CognitiveState.STUCK: [
        "error", "failed", "doesn't work", "can't", "blocked",
        "tried", "still failing", "same error"
    ],
    CognitiveState.COMPLETING: [
        "testing", "verifying", "checking", "done", "finished",
        "test", "verify", "complete", "final"
    ],
    CognitiveState.REASONING: [
        "thinking", "analyzing", "considering", "therefore", "because",
        "if then", "logical", "implies", "deduce"
    ],
    CognitiveState.DEBUGGING: [
        "debug", "trace", "error", "exception", "stack",
        "log", "investigate", "diagnose", "why"
    ],
    CognitiveState.PLANNING: [
        "plan", "steps", "approach", "design", "architecture",
        "todo", "first", "then", "strategy"
    ]
}


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class TPUMetacognitiveClassifier:
    """
    Classify cognitive state using TPU embeddings.

    Compares current context to known state templates using
    semantic similarity for accurate state detection.
    """

    def __init__(self):
        """Initialize the metacognitive classifier."""
        self.use_tpu = TPU_AVAILABLE
        self._template_embeddings: Dict[CognitiveState, np.ndarray] = {}
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # State history for temporal analysis
        self.state_history: List[Tuple[datetime, CognitiveState, float]] = []
        self.max_history = 100

        # Precompute template embeddings
        if self.use_tpu:
            self._precompute_templates()
            logger.info("TPU metacognitive classifier ready")
        else:
            logger.info("Using fallback keyword-based classification")

    def _precompute_templates(self):
        """Precompute embeddings for all state templates."""
        if not self.use_tpu or not _embed_text:
            return

        for state, template in STATE_TEMPLATES.items():
            try:
                start = time.perf_counter()
                embedding = _embed_text(template)
                latency = (time.perf_counter() - start) * 1000

                if embedding is not None:
                    self._template_embeddings[state] = np.array(embedding, dtype=np.float32)

                    if HAS_TPU_MONITOR:
                        record_tpu_usage(
                            "template_embedding",
                            latency_ms=latency,
                            source="metacognitive_classifier",
                            metadata={"state": state.value}
                        )
            except Exception as e:
                logger.warning(f"Failed to embed template for {state}: {e}")

        logger.info(f"Precomputed {len(self._template_embeddings)} state templates")

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding with caching."""
        # Use cache key based on text hash
        cache_key = str(hash(text))
        if cache_key in self._embedding_cache:
            return self._embedding_cache[cache_key]

        if not self.use_tpu or not _embed_text:
            return None

        try:
            start = time.perf_counter()
            embedding = _embed_text(text)
            latency = (time.perf_counter() - start) * 1000

            if embedding is not None:
                emb_array = np.array(embedding, dtype=np.float32)
                self._embedding_cache[cache_key] = emb_array

                if HAS_TPU_MONITOR:
                    record_tpu_usage(
                        "context_embedding",
                        latency_ms=latency,
                        source="metacognitive_classifier"
                    )

                return emb_array
        except Exception as e:
            logger.warning(f"Failed to embed context: {e}")

        return None

    def _keyword_score(self, text: str, state: CognitiveState) -> float:
        """Calculate keyword-based score for a state."""
        text_lower = text.lower()
        indicators = ACTION_INDICATORS.get(state, [])

        matches = sum(1 for ind in indicators if ind in text_lower)
        return min(1.0, matches / max(len(indicators) / 2, 1))

    async def classify_state(
        self,
        context: str,
        recent_actions: Optional[List[str]] = None,
        recent_errors: Optional[List[str]] = None,
        task_progress: float = 0.5
    ) -> MetacognitiveResult:
        """
        Classify current cognitive state.

        Args:
            context: Current context/situation description
            recent_actions: Recent actions taken (optional)
            recent_errors: Recent errors encountered (optional)
            task_progress: Estimated progress on current task (0.0-1.0)

        Returns:
            MetacognitiveResult with classified state
        """
        start_time = time.perf_counter()

        # Build full context
        full_context = context
        if recent_actions:
            full_context += f" | Recent actions: {', '.join(recent_actions[-5:])}"
        if recent_errors:
            full_context += f" | Recent errors: {', '.join(recent_errors[-3:])}"

        # Get context embedding
        context_embedding = self._get_embedding(full_context)

        if context_embedding is not None and self._template_embeddings:
            # TPU-based classification
            scores = {}
            for state, template_emb in self._template_embeddings.items():
                similarity = cosine_similarity(context_embedding, template_emb)
                # Boost with keyword matching
                keyword_boost = self._keyword_score(full_context, state) * 0.2
                scores[state] = similarity + keyword_boost

        else:
            # Fallback to keyword-only classification
            scores = {
                state: self._keyword_score(full_context, state)
                for state in CognitiveState
            }

        # Normalize scores
        max_score = max(scores.values()) if scores else 1.0
        if max_score > 0:
            scores = {k: v / max_score for k, v in scores.items()}

        # Find best state
        best_state = max(scores, key=scores.get)
        confidence = scores[best_state]

        # Apply task progress heuristics
        if task_progress > 0.9:
            scores[CognitiveState.COMPLETING] += 0.2
        if recent_errors and len(recent_errors) > 0:
            scores[CognitiveState.DEBUGGING] += 0.15
            scores[CognitiveState.STUCK] += 0.1

        # Recalculate best state after adjustments
        best_state = max(scores, key=scores.get)
        confidence = min(1.0, scores[best_state])

        # Collect indicators
        indicators = []
        for state, state_indicators in ACTION_INDICATORS.items():
            for indicator in state_indicators:
                if indicator in full_context.lower():
                    indicators.append(f"{indicator} -> {state.value}")
                    break

        # Estimate cognitive load
        cognitive_load = self._estimate_cognitive_load(
            context, recent_errors, len(recent_actions or [])
        )

        # Estimate attention level
        attention_level = self._estimate_attention(context, confidence)

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Record to history
        self.state_history.append((datetime.now(), best_state, confidence))
        while len(self.state_history) > self.max_history:
            self.state_history.pop(0)

        if HAS_TPU_MONITOR:
            record_tpu_usage(
                "state_classification",
                latency_ms=latency_ms,
                source="metacognitive_classifier",
                metadata={
                    "state": best_state.value,
                    "confidence": confidence
                }
            )

        return MetacognitiveResult(
            state=best_state,
            confidence=confidence,
            all_scores={s.value: v for s, v in scores.items()},
            indicators=indicators[:5],  # Top 5
            cognitive_load=cognitive_load,
            attention_level=attention_level,
            latency_ms=latency_ms
        )

    def _estimate_cognitive_load(
        self,
        context: str,
        errors: Optional[List[str]],
        action_count: int
    ) -> float:
        """Estimate current cognitive load (0.0-1.0)."""
        load = 0.3  # Base load

        # More errors = higher load
        if errors:
            load += min(0.3, len(errors) * 0.1)

        # More recent actions = higher load
        load += min(0.2, action_count * 0.04)

        # Complexity indicators
        complexity_words = ["complex", "multiple", "several", "many", "various"]
        for word in complexity_words:
            if word in context.lower():
                load += 0.05

        return min(1.0, load)

    def _estimate_attention(self, context: str, confidence: float) -> float:
        """Estimate attention level (0.0-1.0)."""
        # Higher confidence suggests better focus
        attention = confidence * 0.5

        # Focus indicators
        focus_words = ["specifically", "exactly", "precisely", "focus", "particular"]
        for word in focus_words:
            if word in context.lower():
                attention += 0.1

        # Distraction indicators
        distraction_words = ["also", "maybe", "perhaps", "alternatively", "or"]
        for word in distraction_words:
            if word in context.lower():
                attention -= 0.05

        return max(0.0, min(1.0, attention + 0.3))  # Add base attention

    def get_state_transitions(self, limit: int = 10) -> List[Dict]:
        """Get recent state transitions."""
        if len(self.state_history) < 2:
            return []

        transitions = []
        for i in range(1, min(limit + 1, len(self.state_history))):
            prev = self.state_history[-(i + 1)]
            curr = self.state_history[-i]

            if prev[1] != curr[1]:  # State changed
                transitions.append({
                    "from_state": prev[1].value,
                    "to_state": curr[1].value,
                    "timestamp": curr[0].isoformat(),
                    "confidence": curr[2]
                })

        return transitions

    def get_dominant_state(self, window_seconds: int = 300) -> Optional[CognitiveState]:
        """Get the dominant state in the recent time window."""
        if not self.state_history:
            return None

        cutoff = datetime.now().timestamp() - window_seconds
        recent = [
            h for h in self.state_history
            if h[0].timestamp() >= cutoff
        ]

        if not recent:
            return self.state_history[-1][1] if self.state_history else None

        # Count weighted by confidence
        state_weights: Dict[CognitiveState, float] = {}
        for timestamp, state, confidence in recent:
            state_weights[state] = state_weights.get(state, 0) + confidence

        return max(state_weights, key=state_weights.get)

    def get_statistics(self) -> Dict[str, Any]:
        """Get classifier statistics."""
        state_counts: Dict[str, int] = {}
        for _, state, _ in self.state_history:
            state_counts[state.value] = state_counts.get(state.value, 0) + 1

        return {
            "tpu_available": self.use_tpu,
            "templates_loaded": len(self._template_embeddings),
            "cache_size": len(self._embedding_cache),
            "history_size": len(self.state_history),
            "state_distribution": state_counts,
            "supported_states": [s.value for s in CognitiveState]
        }


# CLI interface
if __name__ == "__main__":
    import asyncio
    import argparse

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


    parser = argparse.ArgumentParser(description="TPU Metacognitive Classifier")
    parser.add_argument("command", choices=["classify", "stats", "test"],
                       help="Command to run")
    parser.add_argument("--context", "-c", type=str, help="Context to classify")

    args = parser.parse_args()

    classifier = TPUMetacognitiveClassifier()

    if args.command == "classify":
        if not args.context:
            print("Error: --context required for classification")
            sys.exit(1)

        result = asyncio.run(classifier.classify_state(args.context))
        print(json.dumps({
            "state": result.state.value,
            "confidence": result.confidence,
            "all_scores": result.all_scores,
            "indicators": result.indicators,
            "cognitive_load": result.cognitive_load,
            "attention_level": result.attention_level,
            "latency_ms": result.latency_ms
        }, indent=2))

    elif args.command == "stats":
        stats = classifier.get_statistics()
        print(json.dumps(stats, indent=2))

    elif args.command == "test":
        # Test various contexts
        test_contexts = [
            "Writing a new function to parse JSON data",
            "Searching for documentation about the API",
            "I'm not sure what the user wants here",
            "Error: connection refused, tried 3 times already",
            "Running final tests, almost done",
            "If A implies B and B implies C, then A implies C",
            "Checking the stack trace to find the bug",
            "First we need to design the architecture, then implement"
        ]

        print("Testing various contexts:\n")
        for ctx in test_contexts:
            result = asyncio.run(classifier.classify_state(ctx))
            print(f"Context: {ctx[:50]}...")
            print(f"  State: {result.state.value} ({result.confidence:.2f})")
            print(f"  Load: {result.cognitive_load:.2f}, Attention: {result.attention_level:.2f}")
            print()
