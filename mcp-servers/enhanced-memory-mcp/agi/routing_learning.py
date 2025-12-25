"""
Routing Learning Module - Phase 4 Holographic Memory

Learns from historical success patterns to influence model routing.
Integrates with:
- Procedural Evolution (Phase 3): Which skill variants work best
- ReasoningBank: What strategies succeeded
- Execution History: What model tiers performed well

The routing learner observes outcomes and adjusts routing bias to
automatically prefer models that have historically succeeded in similar contexts.
"""

import sqlite3
import logging
import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger("routing-learning")

# Database path - same as other AGI modules
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Model tier definitions
MODEL_TIERS = {
    "simple": ["haiku", "gpt-4o-mini", "claude-3-haiku"],
    "balanced": ["sonnet", "gpt-4o", "claude-3-5-sonnet"],
    "complex": ["opus", "gpt-4-turbo", "claude-3-opus", "o1"],
    "local": ["llama", "mistral", "codellama", "ollama"]
}

# Task type categories for learning
TASK_CATEGORIES = [
    "code_review", "code_generation", "debugging", "architecture",
    "documentation", "quick_question", "analysis", "creative",
    "security", "optimization", "refactoring", "testing"
]


@dataclass
class RoutingOutcome:
    """Records a model routing decision and its outcome."""
    outcome_id: int = 0
    task_type: str = ""
    query_hash: str = ""
    model_tier: str = ""
    model_name: str = ""
    success_score: float = 0.0
    execution_time_ms: int = 0
    context_key: str = ""
    activated_count: int = 0
    emotional_valence: float = 0.0
    emotional_arousal: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "task_type": self.task_type,
            "query_hash": self.query_hash,
            "model_tier": self.model_tier,
            "model_name": self.model_name,
            "success_score": self.success_score,
            "execution_time_ms": self.execution_time_ms,
            "context_key": self.context_key,
            "activated_count": self.activated_count,
            "emotional_valence": self.emotional_valence,
            "emotional_arousal": self.emotional_arousal,
            "timestamp": self.timestamp
        }


@dataclass
class TierPerformance:
    """Aggregated performance for a model tier."""
    tier: str
    total_executions: int = 0
    total_success: float = 0.0
    avg_success: float = 0.0
    avg_execution_time_ms: float = 0.0
    confidence: float = 0.0  # Wilson score lower bound

    def fitness_score(self) -> float:
        """
        Compute fitness score with confidence adjustment.

        Same formula as procedural evolution:
        fitness = mean_score * confidence + prior * (1 - confidence)
        """
        if self.total_executions == 0:
            return 0.5  # Prior for unknown

        # Confidence based on execution count (reaches 0.95 at 20 executions)
        self.confidence = min(0.95, self.total_executions / 20)

        prior = 0.5
        return self.avg_success * self.confidence + prior * (1 - self.confidence)


class RoutingLearner:
    """
    Learns optimal model routing from historical outcomes.

    Phase 4 of holographic memory - memory automatically influences
    which model tier is selected based on what worked before.

    Key Features:
    - Records routing outcomes with context
    - Computes tier performance by task type
    - Integrates with procedural evolution skill outcomes
    - Provides learned routing bias adjustments
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._init_database()
        self._initialized = True
        logger.info("RoutingLearner initialized (singleton)")

    def _init_database(self):
        """Initialize routing learning tables."""
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Routing outcomes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS routing_outcomes (
                outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                query_hash TEXT,
                model_tier TEXT NOT NULL,
                model_name TEXT,
                success_score REAL NOT NULL,
                execution_time_ms INTEGER,
                context_key TEXT,
                activated_count INTEGER DEFAULT 0,
                emotional_valence REAL DEFAULT 0.0,
                emotional_arousal REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Tier performance cache (computed aggregates)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tier_performance_cache (
                cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                context_key TEXT,
                tier TEXT NOT NULL,
                total_executions INTEGER DEFAULT 0,
                total_success REAL DEFAULT 0.0,
                avg_execution_time_ms REAL DEFAULT 0.0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_type, context_key, tier)
            )
        ''')

        # Routing bias adjustments learned over time
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learned_routing_bias (
                bias_id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                context_key TEXT,
                simple_bias REAL DEFAULT 0.0,
                balanced_bias REAL DEFAULT 0.0,
                complex_bias REAL DEFAULT 0.0,
                local_bias REAL DEFAULT 0.0,
                sample_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_type, context_key)
            )
        ''')

        # Index for fast lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_routing_outcomes_task
            ON routing_outcomes(task_type, model_tier)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_routing_outcomes_context
            ON routing_outcomes(context_key, created_at)
        ''')

        conn.commit()
        conn.close()

        logger.info("Routing learning tables initialized")

    def record_outcome(
        self,
        task_type: str,
        model_tier: str,
        success_score: float,
        query_hash: str = "",
        model_name: str = "",
        execution_time_ms: int = 0,
        context_key: str = "",
        activated_count: int = 0,
        emotional_valence: float = 0.0,
        emotional_arousal: float = 0.0
    ) -> int:
        """
        Record a routing outcome for learning.

        Args:
            task_type: Category of task (code_review, debugging, etc.)
            model_tier: Which tier was used (simple, balanced, complex, local)
            success_score: 0.0 to 1.0 success score
            query_hash: Hash of query for dedup
            model_name: Specific model used
            execution_time_ms: Execution time
            context_key: Optional context identifier
            activated_count: Number of activated entities from activation field
            emotional_valence: Emotional valence from activation field
            emotional_arousal: Emotional arousal from activation field

        Returns:
            outcome_id
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            INSERT INTO routing_outcomes (
                task_type, query_hash, model_tier, model_name,
                success_score, execution_time_ms, context_key,
                activated_count, emotional_valence, emotional_arousal
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                task_type, query_hash, model_tier, model_name,
                success_score, execution_time_ms, context_key,
                activated_count, emotional_valence, emotional_arousal
            )
        )

        outcome_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Update caches
        self._update_tier_cache(task_type, context_key, model_tier, success_score, execution_time_ms)
        self._update_learned_bias(task_type, context_key)

        logger.info(f"Recorded routing outcome: {task_type}/{model_tier} = {success_score:.2f}")

        return outcome_id

    def _normalize_context(self, context_key: Optional[str]) -> str:
        """
        Normalize context_key to a non-NULL value for reliable UNIQUE constraints.

        SQLite treats NULL as unique from other NULLs, so we use a sentinel value
        for the global/default context instead of NULL.
        """
        if not context_key:
            return "__GLOBAL__"
        return context_key

    def _update_tier_cache(
        self,
        task_type: str,
        context_key: str,
        tier: str,
        success_score: float,
        execution_time_ms: int
    ):
        """Update cached tier performance."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Normalize to sentinel value for reliable UNIQUE handling
        normalized_context = self._normalize_context(context_key)

        # Get current values
        cursor.execute(
            '''
            SELECT total_executions, total_success, avg_execution_time_ms
            FROM tier_performance_cache
            WHERE task_type = ? AND context_key = ? AND tier = ?
            ''',
            (task_type, normalized_context, tier)
        )
        row = cursor.fetchone()

        if row:
            # Update existing
            total_exec = row[0] + 1
            total_success = row[1] + success_score
            # Running average for execution time
            new_avg_time = (row[2] * row[0] + execution_time_ms) / total_exec

            cursor.execute(
                '''
                UPDATE tier_performance_cache
                SET total_executions = ?, total_success = ?,
                    avg_execution_time_ms = ?, last_updated = CURRENT_TIMESTAMP
                WHERE task_type = ? AND context_key = ? AND tier = ?
                ''',
                (total_exec, total_success, new_avg_time, task_type, normalized_context, tier)
            )
        else:
            # Insert new
            cursor.execute(
                '''
                INSERT INTO tier_performance_cache (
                    task_type, context_key, tier, total_executions,
                    total_success, avg_execution_time_ms
                ) VALUES (?, ?, ?, 1, ?, ?)
                ''',
                (task_type, normalized_context, tier, success_score, float(execution_time_ms))
            )

        conn.commit()
        conn.close()

    def _update_learned_bias(self, task_type: str, context_key: str):
        """
        Recompute learned routing bias from tier performance.

        The bias is computed by comparing tier fitness scores:
        - If complex tier has higher fitness, bias toward complex
        - If simple tier is just as good, bias toward simple (efficiency)
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Normalize to sentinel value for reliable queries
        normalized_context = self._normalize_context(context_key)

        # Get tier performance for this task type/context
        cursor.execute(
            '''
            SELECT tier, total_executions, total_success, avg_execution_time_ms
            FROM tier_performance_cache
            WHERE task_type = ? AND context_key = ?
            ''',
            (task_type, normalized_context)
        )
        rows = cursor.fetchall()

        if not rows:
            conn.close()
            return

        # Compute fitness for each tier
        tier_fitness = {}
        total_samples = 0

        for row in rows:
            perf = TierPerformance(
                tier=row['tier'],
                total_executions=row['total_executions'],
                total_success=row['total_success'],
                avg_success=row['total_success'] / row['total_executions'] if row['total_executions'] > 0 else 0.5,
                avg_execution_time_ms=row['avg_execution_time_ms']
            )
            tier_fitness[row['tier']] = perf.fitness_score()
            total_samples += row['total_executions']

        # Compute bias based on relative fitness
        # Higher fitness = positive bias, normalized so they sum to ~0
        avg_fitness = sum(tier_fitness.values()) / len(tier_fitness) if tier_fitness else 0.5

        biases = {
            "simple": (tier_fitness.get("simple", 0.5) - avg_fitness) * 0.5,
            "balanced": (tier_fitness.get("balanced", 0.5) - avg_fitness) * 0.5,
            "complex": (tier_fitness.get("complex", 0.5) - avg_fitness) * 0.5,
            "local": (tier_fitness.get("local", 0.5) - avg_fitness) * 0.5
        }

        # Efficiency bonus: If simple performs nearly as well, prefer it
        if "simple" in tier_fitness and "complex" in tier_fitness:
            if tier_fitness["simple"] > tier_fitness["complex"] * 0.9:
                biases["simple"] += 0.1  # Efficiency bonus

        # Store learned bias - using sentinel value for context allows INSERT OR REPLACE to work
        cursor.execute(
            '''
            INSERT OR REPLACE INTO learned_routing_bias (
                task_type, context_key, simple_bias, balanced_bias,
                complex_bias, local_bias, sample_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                task_type, normalized_context,
                biases["simple"], biases["balanced"],
                biases["complex"], biases["local"],
                total_samples
            )
        )

        conn.commit()
        conn.close()

    def get_learned_bias(
        self,
        task_type: str,
        context_key: Optional[str] = None
    ) -> Dict[str, float]:
        """
        Get learned routing bias for a task type.

        Returns:
            Dict with simple/balanced/complex/local bias values
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Normalize context for lookup
        normalized_context = self._normalize_context(context_key)

        # First try exact context match
        cursor.execute(
            '''
            SELECT simple_bias, balanced_bias, complex_bias, local_bias, sample_count
            FROM learned_routing_bias
            WHERE task_type = ? AND context_key = ?
            ''',
            (task_type, normalized_context)
        )
        row = cursor.fetchone()

        if not row and normalized_context != "__GLOBAL__":
            # Fall back to global context
            cursor.execute(
                '''
                SELECT simple_bias, balanced_bias, complex_bias, local_bias, sample_count
                FROM learned_routing_bias
                WHERE task_type = ? AND context_key = '__GLOBAL__'
                ''',
                (task_type,)
            )
            row = cursor.fetchone()

        conn.close()

        if row:
            return {
                "simple": row['simple_bias'],
                "balanced": row['balanced_bias'],
                "complex": row['complex_bias'],
                "local": row['local_bias'],
                "_sample_count": row['sample_count']
            }

        # No learned data - return neutral
        return {
            "simple": 0.0,
            "balanced": 0.0,
            "complex": 0.0,
            "local": 0.0,
            "_sample_count": 0
        }

    def get_tier_performance(
        self,
        task_type: str,
        context_key: Optional[str] = None
    ) -> List[TierPerformance]:
        """
        Get performance statistics for each tier.

        Returns:
            List of TierPerformance for each tier with data
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Normalize context for lookup
        normalized_context = self._normalize_context(context_key)

        cursor.execute(
            '''
            SELECT tier, total_executions, total_success, avg_execution_time_ms
            FROM tier_performance_cache
            WHERE task_type = ? AND context_key = ?
            ORDER BY total_executions DESC
            ''',
            (task_type, normalized_context)
        )
        rows = cursor.fetchall()
        conn.close()

        performances = []
        for row in rows:
            perf = TierPerformance(
                tier=row['tier'],
                total_executions=row['total_executions'],
                total_success=row['total_success'],
                avg_success=row['total_success'] / row['total_executions'] if row['total_executions'] > 0 else 0.0,
                avg_execution_time_ms=row['avg_execution_time_ms']
            )
            perf.fitness_score()  # Compute confidence
            performances.append(perf)

        return performances

    def get_recommended_tier(
        self,
        task_type: str,
        context_key: Optional[str] = None,
        emotional_arousal: float = 0.5
    ) -> Tuple[str, float]:
        """
        Get recommended tier based on learned patterns.

        Args:
            task_type: Type of task
            context_key: Optional context
            emotional_arousal: Arousal level (higher = prefer complex)

        Returns:
            (tier_name, confidence) tuple
        """
        bias = self.get_learned_bias(task_type, context_key)
        sample_count = bias.pop("_sample_count", 0)

        # Apply emotional modulation
        if emotional_arousal > 0.7:
            bias["complex"] += 0.1

        # Find tier with highest bias
        if sample_count < 3:
            # Not enough data - return balanced with low confidence
            return ("balanced", 0.3)

        best_tier = max(bias.keys(), key=lambda k: bias[k])
        confidence = min(0.9, 0.3 + sample_count / 50)  # Confidence grows with samples

        return (best_tier, confidence)

    def integrate_procedural_outcome(
        self,
        skill_name: str,
        variant_tag: str,
        success_score: float,
        model_tier: str,
        context_key: Optional[str] = None
    ):
        """
        Integrate procedural evolution outcomes into routing learning.

        When a skill variant succeeds/fails, we learn about the model tier
        that was used during execution.
        """
        # Infer task type from skill name
        task_type = self._infer_task_type(skill_name)

        self.record_outcome(
            task_type=task_type,
            model_tier=model_tier,
            success_score=success_score,
            context_key=context_key or skill_name,
            model_name=f"procedural:{variant_tag}"
        )

        logger.info(f"Integrated procedural outcome: {skill_name}/{variant_tag} -> {task_type}/{model_tier}")

    def integrate_reasoning_bank_outcome(
        self,
        task_id: str,
        query: str,
        verdict: str,
        model_tier: str,
        domain: str = "general",
        memories_created: int = 0,
        execution_time_ms: int = 0
    ):
        """
        Integrate ReasoningBank learning outcomes into routing learning.

        When ReasoningBank distills memories from task execution, we also
        learn about which model tier performed well for that type of task.

        Args:
            task_id: Task identifier from ReasoningBank
            query: Original task query
            verdict: Task verdict (success, failure, partial)
            model_tier: Which tier was used
            domain: ReasoningBank domain (maps to task type)
            memories_created: Number of memories distilled
            execution_time_ms: Task execution time
        """
        # Map verdict to success score
        verdict_scores = {
            "success": 0.95,
            "partial": 0.60,
            "failure": 0.20,
            "unknown": 0.50
        }
        success_score = verdict_scores.get(verdict.lower(), 0.50)

        # Use domain as task type, or infer from query
        task_type = domain if domain != "general" else self._infer_task_type_from_query(query)

        self.record_outcome(
            task_type=task_type,
            model_tier=model_tier,
            success_score=success_score,
            query_hash=task_id,
            execution_time_ms=execution_time_ms,
            context_key=domain,
            model_name=f"rb:{memories_created}_memories"
        )

        logger.info(f"Integrated ReasoningBank outcome: {task_id}/{verdict} -> {task_type}/{model_tier} = {success_score:.2f}")

    def _infer_task_type_from_query(self, query: str) -> str:
        """Infer task type from query text."""
        query_lower = query.lower()

        patterns = [
            ("review", "code_review"),
            ("analyze", "analysis"),
            ("debug", "debugging"),
            ("fix", "debugging"),
            ("test", "testing"),
            ("document", "documentation"),
            ("architect", "architecture"),
            ("design", "architecture"),
            ("security", "security"),
            ("optim", "optimization"),
            ("refactor", "refactoring"),
            ("generat", "code_generation"),
            ("create", "code_generation"),
            ("build", "code_generation"),
            ("question", "quick_question"),
            ("what", "quick_question"),
            ("how", "quick_question"),
            ("why", "analysis"),
        ]

        for pattern, task_type in patterns:
            if pattern in query_lower:
                return task_type

        return "general"

    def _infer_task_type(self, skill_name: str) -> str:
        """Infer task type from skill name."""
        skill_lower = skill_name.lower()

        if "review" in skill_lower:
            return "code_review"
        elif "debug" in skill_lower:
            return "debugging"
        elif "test" in skill_lower:
            return "testing"
        elif "doc" in skill_lower:
            return "documentation"
        elif "arch" in skill_lower:
            return "architecture"
        elif "secur" in skill_lower:
            return "security"
        elif "optim" in skill_lower:
            return "optimization"
        elif "refactor" in skill_lower:
            return "refactoring"
        elif "generat" in skill_lower:
            return "code_generation"
        else:
            return "general"

    def get_stats(self) -> Dict[str, Any]:
        """Get routing learning statistics."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Total outcomes
        cursor.execute('SELECT COUNT(*) FROM routing_outcomes')
        total_outcomes = cursor.fetchone()[0]

        # Outcomes by tier
        cursor.execute('''
            SELECT model_tier, COUNT(*), AVG(success_score)
            FROM routing_outcomes
            GROUP BY model_tier
        ''')
        tier_stats = {row[0]: {"count": row[1], "avg_success": row[2]} for row in cursor.fetchall()}

        # Task types with data
        cursor.execute('SELECT DISTINCT task_type FROM routing_outcomes')
        task_types = [row[0] for row in cursor.fetchall()]

        # Learned biases count
        cursor.execute('SELECT COUNT(*) FROM learned_routing_bias WHERE sample_count >= 3')
        reliable_biases = cursor.fetchone()[0]

        conn.close()

        return {
            "total_outcomes": total_outcomes,
            "tier_stats": tier_stats,
            "task_types_learned": len(task_types),
            "task_types": task_types,
            "reliable_bias_patterns": reliable_biases
        }

    def get_recent_outcomes(self, limit: int = 20) -> List[RoutingOutcome]:
        """Get recent routing outcomes."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM routing_outcomes
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))

        outcomes = []
        for row in cursor.fetchall():
            outcomes.append(RoutingOutcome(
                outcome_id=row['outcome_id'],
                task_type=row['task_type'],
                query_hash=row['query_hash'] or "",
                model_tier=row['model_tier'],
                model_name=row['model_name'] or "",
                success_score=row['success_score'],
                execution_time_ms=row['execution_time_ms'] or 0,
                context_key=row['context_key'] or "",
                activated_count=row['activated_count'] or 0,
                emotional_valence=row['emotional_valence'] or 0.0,
                emotional_arousal=row['emotional_arousal'] or 0.0,
                timestamp=row['created_at']
            ))

        conn.close()
        return outcomes


# Singleton accessor
_routing_learner: Optional[RoutingLearner] = None


def get_routing_learner() -> RoutingLearner:
    """Get or create the routing learner singleton."""
    global _routing_learner
    if _routing_learner is None:
        _routing_learner = RoutingLearner()
    return _routing_learner


# Convenience functions for direct use
def record_routing_outcome(
    task_type: str,
    model_tier: str,
    success_score: float,
    **kwargs
) -> int:
    """Record a routing outcome."""
    return get_routing_learner().record_outcome(
        task_type=task_type,
        model_tier=model_tier,
        success_score=success_score,
        **kwargs
    )


def get_learned_routing_bias(
    task_type: str,
    context_key: Optional[str] = None
) -> Dict[str, float]:
    """Get learned routing bias."""
    return get_routing_learner().get_learned_bias(task_type, context_key)
