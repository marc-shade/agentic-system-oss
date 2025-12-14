"""
RL-Based Retrieval Optimization Module

Implements RMM (Retrieval Memory Model) research finding:
Use reinforcement learning to improve memory retrieval over time.

Key Features:
- Track retrieval outcomes (was retrieved memory useful?)
- Learn retrieval value function Q(query, memory)
- Adjust retrieval scores based on learned preferences
- Bandit-style exploration of retrieval strategies

Research Source: RMM Adaptive Retrieval Analysis
"""

import sqlite3
import json
import math
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger("rl_retrieval")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# RL Hyperparameters (tuned from RMM research)
LEARNING_RATE = 0.1        # α: How fast to update Q-values
DISCOUNT_FACTOR = 0.95     # γ: Future reward importance
EXPLORATION_RATE = 0.1     # ε: Probability of exploring vs exploiting
DECAY_RATE = 0.001         # How fast exploration decreases over time
MIN_EXPLORATION = 0.01     # Minimum exploration rate


@dataclass
class RetrievalFeedback:
    """Feedback signal for a retrieval action."""
    entity_id: int
    query: str
    was_useful: bool           # Did user/system use this memory?
    relevance_score: float     # 0-1: How relevant was it?
    led_to_action: bool        # Did it lead to an action?
    context: Optional[str] = None


@dataclass
class RetrievalState:
    """State representation for RL agent."""
    query_type: str            # Semantic category of query
    query_length: int          # Word count
    context_recency: float     # How recent is the context
    session_progress: float    # How far into session (0-1)


class RetrievalQTable:
    """
    Q-table for retrieval value estimates.

    Maps (query_features, entity_features) → Q-value
    Uses function approximation via feature hashing for scalability.
    """

    def __init__(self, num_buckets: int = 1000):
        self.num_buckets = num_buckets
        self.q_values: Dict[int, float] = {}
        self.counts: Dict[int, int] = {}

    def _hash_features(
        self,
        query_type: str,
        entity_tier: str,
        entity_type: str,
        time_bucket: int
    ) -> int:
        """Hash features into bucket index."""
        feature_str = f"{query_type}:{entity_tier}:{entity_type}:{time_bucket}"
        return hash(feature_str) % self.num_buckets

    def get_q_value(
        self,
        query_type: str,
        entity_tier: str,
        entity_type: str,
        time_bucket: int
    ) -> float:
        """Get Q-value for state-action pair."""
        bucket = self._hash_features(query_type, entity_tier, entity_type, time_bucket)
        return self.q_values.get(bucket, 0.5)  # Default: neutral value

    def update(
        self,
        query_type: str,
        entity_tier: str,
        entity_type: str,
        time_bucket: int,
        reward: float,
        learning_rate: float = LEARNING_RATE
    ):
        """Update Q-value with new reward signal."""
        bucket = self._hash_features(query_type, entity_tier, entity_type, time_bucket)

        old_q = self.q_values.get(bucket, 0.5)
        count = self.counts.get(bucket, 0)

        # Incremental update: Q = Q + α(reward - Q)
        # With count-based learning rate decay
        effective_lr = learning_rate / (1 + 0.01 * count)
        new_q = old_q + effective_lr * (reward - old_q)

        self.q_values[bucket] = new_q
        self.counts[bucket] = count + 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage."""
        return {
            'q_values': self.q_values,
            'counts': self.counts,
            'num_buckets': self.num_buckets
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetrievalQTable':
        """Deserialize from storage."""
        table = cls(num_buckets=data.get('num_buckets', 1000))
        table.q_values = {int(k): v for k, v in data.get('q_values', {}).items()}
        table.counts = {int(k): v for k, v in data.get('counts', {}).items()}
        return table


class RLRetrievalOptimizer:
    """
    RL-based retrieval optimizer implementing RMM principles.

    Uses multi-armed bandit approach with learned value function to:
    1. Boost promising retrievals
    2. Suppress consistently unhelpful memories
    3. Adapt to user/task-specific retrieval patterns
    """

    def __init__(self):
        self._ensure_tables()
        self.q_table = self._load_q_table()
        self.episode_count = self._get_episode_count()

    def _ensure_tables(self):
        """Ensure RL tracking tables exist."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Retrieval feedback log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retrieval_feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                query_text TEXT,
                query_type TEXT,
                was_useful INTEGER,
                relevance_score REAL,
                led_to_action INTEGER,
                context TEXT,
                session_id TEXT,
                recorded_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        ''')

        # Q-table storage
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rl_retrieval_state (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Retrieval performance metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retrieval_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT,
                metric_value REAL,
                window_hours INTEGER,
                computed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()

    def _load_q_table(self) -> RetrievalQTable:
        """Load Q-table from database."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT value FROM rl_retrieval_state WHERE key = 'q_table'"
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            try:
                data = json.loads(row[0])
                return RetrievalQTable.from_dict(data)
            except:
                pass

        return RetrievalQTable()

    def _save_q_table(self):
        """Persist Q-table to database."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO rl_retrieval_state (key, value, updated_at)
            VALUES ('q_table', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP
        ''', (json.dumps(self.q_table.to_dict()),))

        conn.commit()
        conn.close()

    def _get_episode_count(self) -> int:
        """Get total feedback episodes for exploration rate."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM retrieval_feedback')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def _classify_query_type(self, query: str) -> str:
        """Classify query into type for state representation."""
        query_lower = query.lower()

        # Pattern-based classification
        if any(kw in query_lower for kw in ['how', 'implement', 'code', 'function']):
            return 'procedural'
        elif any(kw in query_lower for kw in ['what', 'define', 'meaning', 'concept']):
            return 'factual'
        elif any(kw in query_lower for kw in ['why', 'reason', 'because', 'explain']):
            return 'causal'
        elif any(kw in query_lower for kw in ['example', 'instance', 'case', 'scenario']):
            return 'exemplar'
        elif any(kw in query_lower for kw in ['compare', 'difference', 'versus', 'vs']):
            return 'comparative'
        else:
            return 'general'

    def _get_time_bucket(self, entity_id: int) -> int:
        """Get recency time bucket for entity (0-5)."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT created_at FROM entities WHERE id = ?',
            (entity_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return 2  # Default: middle bucket

        created = datetime.fromisoformat(row[0])
        age_hours = (datetime.now() - created).total_seconds() / 3600

        # Buckets: 0=<1h, 1=<24h, 2=<week, 3=<month, 4=<year, 5=>year
        if age_hours < 1:
            return 0
        elif age_hours < 24:
            return 1
        elif age_hours < 168:  # week
            return 2
        elif age_hours < 720:  # month
            return 3
        elif age_hours < 8760:  # year
            return 4
        else:
            return 5

    def compute_exploration_rate(self) -> float:
        """Compute current exploration rate with decay."""
        # ε-greedy with exponential decay
        rate = EXPLORATION_RATE * math.exp(-DECAY_RATE * self.episode_count)
        return max(MIN_EXPLORATION, rate)

    def record_feedback(self, feedback: RetrievalFeedback) -> Dict[str, Any]:
        """
        Record feedback about a retrieval and update Q-values.

        Args:
            feedback: Retrieval feedback signal

        Returns:
            Update summary
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Get entity info
        cursor.execute(
            'SELECT tier, entityType FROM entities WHERE id = ?',
            (feedback.entity_id,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {'error': 'Entity not found'}

        entity_tier, entity_type = row

        # Record feedback
        cursor.execute('''
            INSERT INTO retrieval_feedback (
                entity_id, query_text, query_type,
                was_useful, relevance_score, led_to_action, context
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            feedback.entity_id,
            feedback.query,
            self._classify_query_type(feedback.query),
            int(feedback.was_useful),
            feedback.relevance_score,
            int(feedback.led_to_action),
            feedback.context
        ))

        conn.commit()
        conn.close()

        # Compute reward signal
        # Composite reward: useful (0.5) + relevance (0.3) + led_to_action (0.2)
        reward = (
            (0.5 if feedback.was_useful else 0.0) +
            (0.3 * feedback.relevance_score) +
            (0.2 if feedback.led_to_action else 0.0)
        )

        # Update Q-table
        query_type = self._classify_query_type(feedback.query)
        time_bucket = self._get_time_bucket(feedback.entity_id)

        old_q = self.q_table.get_q_value(query_type, entity_tier, entity_type, time_bucket)

        self.q_table.update(
            query_type, entity_tier, entity_type, time_bucket,
            reward
        )

        new_q = self.q_table.get_q_value(query_type, entity_tier, entity_type, time_bucket)

        # Save periodically (every 10 episodes)
        self.episode_count += 1
        if self.episode_count % 10 == 0:
            self._save_q_table()

        logger.info(f"Recorded feedback for entity {feedback.entity_id}: reward={reward:.2f}, Q: {old_q:.3f} → {new_q:.3f}")

        return {
            'entity_id': feedback.entity_id,
            'reward': reward,
            'old_q': old_q,
            'new_q': new_q,
            'episode': self.episode_count
        }

    def boost_retrieval_scores(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply RL-learned boosts to retrieval candidates.

        Args:
            query: Search query
            candidates: List of retrieval candidates with base scores

        Returns:
            Candidates with boosted scores
        """
        query_type = self._classify_query_type(query)
        exploration_rate = self.compute_exploration_rate()

        boosted = []
        for candidate in candidates:
            entity_id = candidate.get('entity_id') or candidate.get('id')
            base_score = candidate.get('score', candidate.get('relevance_score', 0.5))
            tier = candidate.get('tier', 'working')
            entity_type = candidate.get('type', candidate.get('entityType', 'general'))

            time_bucket = self._get_time_bucket(entity_id)

            # Get learned Q-value
            q_value = self.q_table.get_q_value(query_type, tier, entity_type, time_bucket)

            # ε-greedy exploration
            if random.random() < exploration_rate:
                # Explore: Add random perturbation
                boost = random.uniform(-0.2, 0.2)
            else:
                # Exploit: Use learned Q-value to boost/suppress
                # Q-value of 0.5 is neutral, >0.5 boosts, <0.5 suppresses
                boost = (q_value - 0.5) * 0.4  # Scale to [-0.2, +0.2]

            boosted_score = max(0, min(1, base_score + boost))

            boosted_candidate = candidate.copy()
            boosted_candidate['original_score'] = base_score
            boosted_candidate['rl_boost'] = boost
            boosted_candidate['final_score'] = boosted_score
            boosted_candidate['q_value'] = q_value

            boosted.append(boosted_candidate)

        # Re-sort by boosted score
        boosted.sort(key=lambda x: x['final_score'], reverse=True)

        logger.debug(f"Applied RL boosts to {len(boosted)} candidates (exploration rate: {exploration_rate:.3f})")

        return boosted

    def get_retrieval_statistics(
        self,
        window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get retrieval performance statistics.

        Args:
            window_hours: Time window for statistics

        Returns:
            Performance statistics
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=window_hours)).isoformat()

        # Usefulness rate
        cursor.execute('''
            SELECT
                COUNT(*) as total,
                SUM(was_useful) as useful,
                AVG(relevance_score) as avg_relevance,
                SUM(led_to_action) as led_to_actions
            FROM retrieval_feedback
            WHERE recorded_at > ?
        ''', (cutoff,))

        row = cursor.fetchone()

        total = row[0] or 0
        useful = row[1] or 0
        avg_relevance = row[2] or 0.0
        led_to_actions = row[3] or 0

        # By query type
        cursor.execute('''
            SELECT query_type, COUNT(*), AVG(relevance_score), SUM(was_useful)
            FROM retrieval_feedback
            WHERE recorded_at > ?
            GROUP BY query_type
        ''', (cutoff,))

        by_query_type = [
            {
                'type': row[0],
                'count': row[1],
                'avg_relevance': row[2],
                'useful_count': row[3]
            }
            for row in cursor.fetchall()
        ]

        conn.close()

        return {
            'window_hours': window_hours,
            'total_retrievals': total,
            'usefulness_rate': (useful / total) if total > 0 else 0.0,
            'avg_relevance': avg_relevance,
            'action_conversion_rate': (led_to_actions / total) if total > 0 else 0.0,
            'by_query_type': by_query_type,
            'exploration_rate': self.compute_exploration_rate(),
            'total_episodes': self.episode_count,
            'q_table_size': len(self.q_table.q_values)
        }

    def get_top_performing_memory_types(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get entity types with highest learned Q-values."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Aggregate by entity type
        cursor.execute('''
            SELECT
                e.entityType,
                COUNT(rf.feedback_id) as feedback_count,
                AVG(rf.relevance_score) as avg_relevance,
                AVG(rf.was_useful) as usefulness_rate
            FROM retrieval_feedback rf
            JOIN entities e ON rf.entity_id = e.id
            GROUP BY e.entityType
            HAVING feedback_count >= 3
            ORDER BY usefulness_rate DESC
            LIMIT ?
        ''', (limit,))

        results = [
            {
                'entity_type': row[0],
                'feedback_count': row[1],
                'avg_relevance': row[2],
                'usefulness_rate': row[3]
            }
            for row in cursor.fetchall()
        ]

        conn.close()
        return results

    def save_state(self):
        """Force save current RL state."""
        self._save_q_table()
        logger.info("RL retrieval state saved")


# Singleton instance
_optimizer = None

def get_rl_retrieval_optimizer() -> RLRetrievalOptimizer:
    """Get singleton optimizer instance."""
    global _optimizer
    if _optimizer is None:
        _optimizer = RLRetrievalOptimizer()
    return _optimizer
