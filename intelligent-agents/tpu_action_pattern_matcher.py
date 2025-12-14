#!/usr/bin/env python3
"""
TPU Action Pattern Matcher - Edge TPU Accelerated Action Outcome Analysis

Matches new actions against historical patterns to predict outcomes
and suggest optimal strategies. Uses semantic similarity for fast
pattern matching without API calls.

Integration with enhanced-memory action_outcome tracking.

Usage:
    from tpu_action_pattern_matcher import TPUActionPatternMatcher

    matcher = TPUActionPatternMatcher()
    prediction = await matcher.predict_outcome(
        action_type="code_change",
        action_description="Add caching to database queries"
    )
    print(f"Predicted success: {prediction.success_probability:.2f}")
"""
import platform

import os
import sys
import json
import time
import logging
import sqlite3
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

# Add hooks path
AGENTIC_SYSTEM_PATH = os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE))
HOOKS_PATH = os.path.join(AGENTIC_SYSTEM_PATH, "scripts/hooks")
if HOOKS_PATH not in sys.path:
    sys.path.insert(0, HOOKS_PATH)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tpu_action_pattern_matcher")

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


# Database for action outcomes
DB_PATH = Path(AGENTIC_SYSTEM_PATH) / "databases" / "action_patterns.db"


@dataclass
class ActionOutcome:
    """Recorded action and its outcome"""
    action_id: str
    action_type: str
    description: str
    context: str
    expected_result: str
    actual_result: str
    success_score: float  # 0.0-1.0
    timestamp: datetime
    duration_ms: Optional[int] = None
    embedding: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionPattern:
    """A recognized pattern in actions"""
    pattern_id: str
    pattern_type: str  # success, failure, improvement, regression
    description: str
    action_types: List[str]
    avg_success_rate: float
    occurrence_count: int
    example_actions: List[ActionOutcome]
    centroid: Optional[np.ndarray] = None


@dataclass
class OutcomePrediction:
    """Predicted outcome for a proposed action"""
    success_probability: float
    confidence: float
    similar_successes: List[Tuple[ActionOutcome, float]]
    similar_failures: List[Tuple[ActionOutcome, float]]
    recommended_strategy: str
    risk_factors: List[str]
    latency_ms: float


def _ensure_db():
    """Ensure database exists with proper schema."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS action_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_id TEXT UNIQUE NOT NULL,
            action_type TEXT NOT NULL,
            description TEXT NOT NULL,
            context TEXT,
            expected_result TEXT,
            actual_result TEXT,
            success_score REAL NOT NULL,
            timestamp TEXT NOT NULL,
            duration_ms INTEGER,
            embedding BLOB,
            metadata TEXT
        )
    ''')

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_action_type ON action_outcomes(action_type)
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_success_score ON action_outcomes(success_score)
    ''')

    conn.commit()
    conn.close()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class TPUActionPatternMatcher:
    """
    Match actions to patterns and predict outcomes.

    Uses TPU embeddings to find similar past actions and
    predict success/failure based on historical patterns.
    """

    def __init__(self):
        _ensure_db()
        self.use_tpu = TPU_AVAILABLE
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # Action type templates for pattern matching
        self.action_templates = {
            "code_change": "Modify source code to add features or fix bugs",
            "refactoring": "Restructure code without changing behavior",
            "optimization": "Improve performance, reduce latency or memory",
            "debugging": "Investigate and fix bugs or errors",
            "testing": "Write or run tests to verify functionality",
            "configuration": "Modify settings or configuration files",
            "documentation": "Update documentation or comments",
            "deployment": "Deploy code to production or staging",
            "research": "Investigate solutions or gather information",
            "planning": "Plan architecture or implementation approach"
        }

        # Precompute template embeddings
        self._template_embeddings = self._precompute_templates()

        if self.use_tpu:
            logger.info("TPU action pattern matching enabled")
        else:
            logger.info("Using fallback pattern matching")

    def _precompute_templates(self) -> Dict[str, np.ndarray]:
        """Precompute embeddings for action templates."""
        templates = {}
        if not self.use_tpu or not _embed_text:
            return templates

        for name, description in self.action_templates.items():
            try:
                embedding = _embed_text(description)
                if embedding is not None:
                    templates[name] = np.array(embedding, dtype=np.float32)
            except Exception as e:
                logger.warning(f"Failed to embed template {name}: {e}")

        return templates

    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get text embedding with caching."""
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
                        "action_embedding",
                        latency_ms=latency,
                        source="action_pattern_matcher"
                    )
                return emb_array
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")

        return None

    def _get_past_actions(
        self,
        action_type: Optional[str] = None,
        success_filter: Optional[bool] = None,
        limit: int = 100
    ) -> List[ActionOutcome]:
        """Get past actions from database."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        query = "SELECT * FROM action_outcomes WHERE embedding IS NOT NULL"
        params = []

        if action_type:
            query += " AND action_type = ?"
            params.append(action_type)

        if success_filter is not None:
            if success_filter:
                query += " AND success_score >= 0.7"
            else:
                query += " AND success_score < 0.5"

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)

        results = []
        for row in cursor.fetchall():
            try:
                embedding = np.frombuffer(row[10], dtype=np.float32) if row[10] else None
                metadata = json.loads(row[11]) if row[11] else {}

                results.append(ActionOutcome(
                    action_id=row[1],
                    action_type=row[2],
                    description=row[3],
                    context=row[4] or "",
                    expected_result=row[5] or "",
                    actual_result=row[6] or "",
                    success_score=row[7],
                    timestamp=datetime.fromisoformat(row[8]),
                    duration_ms=row[9],
                    embedding=embedding,
                    metadata=metadata
                ))
            except Exception:
                continue

        conn.close()
        return results

    async def predict_outcome(
        self,
        action_type: str,
        action_description: str,
        context: Optional[str] = None,
        expected_result: Optional[str] = None
    ) -> OutcomePrediction:
        """
        Predict the outcome of a proposed action.

        Args:
            action_type: Type of action
            action_description: What the action does
            context: Additional context
            expected_result: What we expect to happen

        Returns:
            OutcomePrediction with success probability and analysis
        """
        start_time = time.perf_counter()

        # Build full text for embedding
        full_text = f"{action_type}: {action_description}"
        if context:
            full_text += f" | Context: {context}"
        if expected_result:
            full_text += f" | Expected: {expected_result}"

        action_embedding = self._get_embedding(full_text)

        if action_embedding is None:
            # Fallback prediction
            return self._fallback_prediction(action_type, action_description)

        # Get similar past actions
        successful_actions = self._get_past_actions(success_filter=True)
        failed_actions = self._get_past_actions(success_filter=False)

        # Calculate similarities
        success_similarities = []
        for action in successful_actions:
            if action.embedding is not None:
                sim = cosine_similarity(action_embedding, action.embedding)
                success_similarities.append((action, sim))

        failure_similarities = []
        for action in failed_actions:
            if action.embedding is not None:
                sim = cosine_similarity(action_embedding, action.embedding)
                failure_similarities.append((action, sim))

        # Sort by similarity
        success_similarities.sort(key=lambda x: x[1], reverse=True)
        failure_similarities.sort(key=lambda x: x[1], reverse=True)

        # Calculate success probability
        top_success_sim = success_similarities[0][1] if success_similarities else 0.0
        top_failure_sim = failure_similarities[0][1] if failure_similarities else 0.0

        # Weighted average based on similarity
        total_weight = top_success_sim + top_failure_sim
        if total_weight > 0:
            success_prob = top_success_sim / total_weight
        else:
            success_prob = 0.5  # No data

        # Adjust based on action type historical success rate
        type_success_rate = self._get_type_success_rate(action_type)
        if type_success_rate is not None:
            success_prob = 0.7 * success_prob + 0.3 * type_success_rate

        # Confidence based on sample size and similarity strength
        sample_size = len(success_similarities) + len(failure_similarities)
        similarity_strength = max(top_success_sim, top_failure_sim)
        confidence = min(1.0, (sample_size / 50) * similarity_strength)

        # Identify risk factors
        risk_factors = []
        if top_failure_sim > 0.7:
            risk_factors.append(f"Very similar to past failure: {failure_similarities[0][0].description[:50]}...")
        if type_success_rate is not None and type_success_rate < 0.5:
            risk_factors.append(f"Action type {action_type} has low historical success rate")
        if success_prob < 0.4:
            risk_factors.append("Low predicted success probability")

        # Recommend strategy
        if success_prob > 0.7 and len(risk_factors) == 0:
            strategy = "Proceed with confidence - similar actions have succeeded"
        elif success_prob > 0.5:
            strategy = "Proceed with caution - consider incremental approach"
        elif top_success_sim > 0.6:
            strategy = f"Review similar success: {success_similarities[0][0].description[:50]}..."
        else:
            strategy = "Consider alternative approach - similar actions have often failed"

        latency_ms = (time.perf_counter() - start_time) * 1000

        if HAS_TPU_MONITOR:
            record_tpu_usage(
                "outcome_prediction",
                latency_ms=latency_ms,
                source="action_pattern_matcher",
                metadata={
                    "action_type": action_type,
                    "success_prob": success_prob
                }
            )

        return OutcomePrediction(
            success_probability=success_prob,
            confidence=confidence,
            similar_successes=success_similarities[:3],
            similar_failures=failure_similarities[:3],
            recommended_strategy=strategy,
            risk_factors=risk_factors,
            latency_ms=latency_ms
        )

    def _get_type_success_rate(self, action_type: str) -> Optional[float]:
        """Get historical success rate for an action type."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute('''
            SELECT AVG(success_score), COUNT(*)
            FROM action_outcomes
            WHERE action_type = ?
        ''', (action_type,))

        row = cursor.fetchone()
        conn.close()

        if row and row[1] > 5:  # Need at least 5 samples
            return row[0]
        return None

    def _fallback_prediction(
        self,
        action_type: str,
        description: str
    ) -> OutcomePrediction:
        """Fallback prediction when TPU unavailable."""
        # Use keyword heuristics
        positive_keywords = ["fix", "improve", "optimize", "add", "implement"]
        negative_keywords = ["hack", "workaround", "temporary", "quick"]

        desc_lower = description.lower()

        score = 0.5
        for kw in positive_keywords:
            if kw in desc_lower:
                score += 0.05
        for kw in negative_keywords:
            if kw in desc_lower:
                score -= 0.05

        return OutcomePrediction(
            success_probability=max(0.1, min(0.9, score)),
            confidence=0.3,
            similar_successes=[],
            similar_failures=[],
            recommended_strategy="Limited prediction - TPU unavailable",
            risk_factors=["Prediction based on keywords only"],
            latency_ms=0.0
        )

    def record_action_outcome(
        self,
        action_type: str,
        description: str,
        expected_result: str,
        actual_result: str,
        success_score: float,
        context: str = "",
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Record an action outcome for learning.

        Args:
            action_type: Type of action
            description: What was done
            expected_result: What was expected
            actual_result: What actually happened
            success_score: 0.0-1.0
            context: Additional context
            duration_ms: How long it took
            metadata: Additional data

        Returns:
            action_id
        """
        import uuid

        action_id = str(uuid.uuid4())[:8]

        # Get embedding
        full_text = f"{action_type}: {description}"
        if context:
            full_text += f" | {context}"

        embedding = self._get_embedding(full_text)
        embedding_bytes = embedding.tobytes() if embedding is not None else None

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO action_outcomes
            (action_id, action_type, description, context, expected_result,
             actual_result, success_score, timestamp, duration_ms, embedding, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            action_id,
            action_type,
            description,
            context,
            expected_result,
            actual_result,
            success_score,
            datetime.now().isoformat(),
            duration_ms,
            embedding_bytes,
            json.dumps(metadata or {})
        ))

        conn.commit()
        conn.close()

        logger.info(f"Recorded action outcome: {action_id} ({action_type}) success={success_score:.2f}")
        return action_id

    async def find_action_patterns(
        self,
        min_occurrences: int = 3,
        n_patterns: int = 10
    ) -> List[ActionPattern]:
        """
        Discover patterns in action outcomes.

        Args:
            min_occurrences: Minimum times a pattern must occur
            n_patterns: Maximum patterns to return

        Returns:
            List of discovered patterns
        """
        # Get all actions with embeddings
        all_actions = self._get_past_actions(limit=500)

        if len(all_actions) < min_occurrences:
            return []

        # Separate by success/failure
        successes = [a for a in all_actions if a.success_score >= 0.7]
        failures = [a for a in all_actions if a.success_score < 0.5]

        patterns = []

        # Find success patterns
        if successes:
            success_pattern = ActionPattern(
                pattern_id="success_cluster",
                pattern_type="success",
                description="Actions that typically succeed",
                action_types=list(set(a.action_type for a in successes)),
                avg_success_rate=np.mean([a.success_score for a in successes]),
                occurrence_count=len(successes),
                example_actions=successes[:5]
            )
            patterns.append(success_pattern)

        # Find failure patterns
        if failures:
            failure_pattern = ActionPattern(
                pattern_id="failure_cluster",
                pattern_type="failure",
                description="Actions that typically fail",
                action_types=list(set(a.action_type for a in failures)),
                avg_success_rate=np.mean([a.success_score for a in failures]),
                occurrence_count=len(failures),
                example_actions=failures[:5]
            )
            patterns.append(failure_pattern)

        # Group by action type
        by_type = defaultdict(list)
        for action in all_actions:
            by_type[action.action_type].append(action)

        for action_type, actions in by_type.items():
            if len(actions) >= min_occurrences:
                avg_success = np.mean([a.success_score for a in actions])
                pattern_type = "success" if avg_success >= 0.7 else "failure" if avg_success < 0.5 else "mixed"

                patterns.append(ActionPattern(
                    pattern_id=f"type_{action_type}",
                    pattern_type=pattern_type,
                    description=f"Pattern for {action_type} actions",
                    action_types=[action_type],
                    avg_success_rate=avg_success,
                    occurrence_count=len(actions),
                    example_actions=actions[:3]
                ))

        return patterns[:n_patterns]

    def get_statistics(self) -> Dict[str, Any]:
        """Get pattern matcher statistics."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM action_outcomes')
        total = cursor.fetchone()[0]

        cursor.execute('SELECT AVG(success_score) FROM action_outcomes')
        avg_success = cursor.fetchone()[0] or 0.0

        cursor.execute('SELECT action_type, COUNT(*) FROM action_outcomes GROUP BY action_type')
        type_counts = dict(cursor.fetchall())

        conn.close()

        return {
            "tpu_available": self.use_tpu,
            "total_actions": total,
            "avg_success_rate": avg_success,
            "action_type_counts": type_counts,
            "template_count": len(self._template_embeddings),
            "cache_size": len(self._embedding_cache)
        }


# CLI
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


    parser = argparse.ArgumentParser(description="TPU Action Pattern Matcher")
    parser.add_argument("command", choices=["predict", "record", "patterns", "stats"],
                       help="Command to run")
    parser.add_argument("--type", "-t", type=str, help="Action type")
    parser.add_argument("--description", "-d", type=str, help="Action description")
    parser.add_argument("--success", type=float, help="Success score (0.0-1.0)")

    args = parser.parse_args()

    matcher = TPUActionPatternMatcher()

    if args.command == "predict":
        if not args.type or not args.description:
            print("Error: --type and --description required")
            sys.exit(1)

        prediction = asyncio.run(matcher.predict_outcome(args.type, args.description))
        print(json.dumps({
            "success_probability": prediction.success_probability,
            "confidence": prediction.confidence,
            "strategy": prediction.recommended_strategy,
            "risk_factors": prediction.risk_factors,
            "latency_ms": prediction.latency_ms
        }, indent=2))

    elif args.command == "record":
        if not args.type or not args.description or args.success is None:
            print("Error: --type, --description, and --success required")
            sys.exit(1)

        action_id = matcher.record_action_outcome(
            action_type=args.type,
            description=args.description,
            expected_result="",
            actual_result="",
            success_score=args.success
        )
        print(f"Recorded: {action_id}")

    elif args.command == "patterns":
        patterns = asyncio.run(matcher.find_action_patterns())
        print(f"Found {len(patterns)} patterns:")
        for p in patterns:
            print(f"  {p.pattern_id}: {p.pattern_type} ({p.occurrence_count} occurrences, {p.avg_success_rate:.2f} avg)")

    elif args.command == "stats":
        stats = matcher.get_statistics()
        print(json.dumps(stats, indent=2))
