"""
Adaptive Memory Granularity Module

Implements Mem0 research finding: memories should have variable granularity
based on importance, recency, and access patterns.

Key Features:
- Fine-grained storage for high-importance memories (preserve detail)
- Coarse-grained summaries for older/less-accessed memories
- Dynamic granularity adjustment based on usage patterns
- Hierarchical memory representation (summary → detail)

Research Source: Mem0 Architecture Analysis
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("adaptive_granularity")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class GranularityLevel(Enum):
    """Memory granularity levels from Mem0 research."""
    ATOMIC = "atomic"           # Finest grain: individual facts, single steps
    DETAILED = "detailed"       # Full detail: complete context, all metadata
    SUMMARY = "summary"         # Medium grain: key points, reduced context
    COMPRESSED = "compressed"   # Coarse grain: essential info only
    ARCHIVAL = "archival"       # Minimal: just existence and key identifiers


@dataclass
class GranularityMetrics:
    """Metrics for granularity decision."""
    importance_score: float      # 0-1, from salience/emotional tagging
    access_frequency: float      # Accesses per day
    recency_days: float          # Days since last access
    reasoning_category: bool     # Is reasoning-centric content (75% priority)
    reference_count: int         # How many other memories reference this
    content_size_chars: int      # Original content size

    def compute_optimal_granularity(self) -> GranularityLevel:
        """
        Compute optimal granularity level using Mem0-inspired heuristics.

        High importance + high access + reasoning → ATOMIC/DETAILED
        Medium importance + moderate access → SUMMARY
        Low importance + low access → COMPRESSED/ARCHIVAL
        """
        # Weighted score (importance and reasoning weighted highest per 75/15/10 rule)
        score = (
            self.importance_score * 0.35 +
            min(1.0, self.access_frequency / 10) * 0.20 +
            max(0, 1 - self.recency_days / 30) * 0.15 +
            (0.30 if self.reasoning_category else 0.10) +
            min(1.0, self.reference_count / 5) * 0.10
        )

        # Normalize to 0-1
        score = max(0, min(1, score))

        if score >= 0.8:
            return GranularityLevel.ATOMIC
        elif score >= 0.6:
            return GranularityLevel.DETAILED
        elif score >= 0.4:
            return GranularityLevel.SUMMARY
        elif score >= 0.2:
            return GranularityLevel.COMPRESSED
        else:
            return GranularityLevel.ARCHIVAL


class AdaptiveGranularityManager:
    """
    Manages adaptive memory granularity based on Mem0 research.

    Core principle: Not all memories need the same level of detail.
    High-value reasoning memories get preserved in full detail.
    Low-value general memories get progressively compressed.
    """

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure granularity tracking tables exist."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Granularity tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory_granularity (
                entity_id INTEGER PRIMARY KEY,
                current_level TEXT DEFAULT 'detailed',
                original_size_chars INTEGER,
                current_size_chars INTEGER,
                compression_ratio REAL DEFAULT 1.0,
                importance_score REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                last_accessed_at TEXT,
                last_granularity_check TEXT,
                reasoning_category INTEGER DEFAULT 0,
                summary_content TEXT,  -- Cached summary for quick access
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Granularity transitions log (for learning)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS granularity_transitions (
                transition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id INTEGER,
                old_level TEXT,
                new_level TEXT,
                trigger_reason TEXT,
                metrics_snapshot TEXT,  -- JSON of GranularityMetrics
                transitioned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            )
        ''')

        conn.commit()
        conn.close()

    def record_memory_access(self, entity_id: int) -> Dict[str, Any]:
        """
        Record that a memory was accessed (for access frequency tracking).

        Args:
            entity_id: Memory entity ID

        Returns:
            Updated granularity info
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Upsert access tracking
        cursor.execute('''
            INSERT INTO memory_granularity (entity_id, access_count, last_accessed_at)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(entity_id) DO UPDATE SET
                access_count = access_count + 1,
                last_accessed_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        ''', (entity_id,))

        # Get current state
        cursor.execute(
            'SELECT current_level, access_count FROM memory_granularity WHERE entity_id = ?',
            (entity_id,)
        )
        row = cursor.fetchone()

        conn.commit()
        conn.close()

        return {
            'entity_id': entity_id,
            'current_level': row[0] if row else 'detailed',
            'access_count': row[1] if row else 1
        }

    def compute_entity_metrics(self, entity_id: int) -> Optional[GranularityMetrics]:
        """
        Compute granularity metrics for an entity.

        Args:
            entity_id: Memory entity ID

        Returns:
            GranularityMetrics or None if entity not found
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get entity info
        cursor.execute('''
            SELECT e.id, e.observations, e.tier, e.created_at,
                   COALESCE(g.access_count, 0) as access_count,
                   g.last_accessed_at,
                   COALESCE(g.importance_score, 0.5) as importance_score,
                   COALESCE(g.reasoning_category, 0) as reasoning_category
            FROM entities e
            LEFT JOIN memory_granularity g ON e.id = g.entity_id
            WHERE e.id = ?
        ''', (entity_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        # Calculate recency
        last_access = row['last_accessed_at']
        if last_access:
            last_dt = datetime.fromisoformat(last_access)
            recency_days = (datetime.now() - last_dt).total_seconds() / 86400
        else:
            created = datetime.fromisoformat(row['created_at'])
            recency_days = (datetime.now() - created).total_seconds() / 86400

        # Calculate access frequency (per day since creation)
        created_dt = datetime.fromisoformat(row['created_at'])
        days_alive = max(1, (datetime.now() - created_dt).total_seconds() / 86400)
        access_frequency = row['access_count'] / days_alive

        # Count references
        cursor.execute('''
            SELECT COUNT(*) FROM entity_relations
            WHERE target_id = ?
        ''', (entity_id,))
        ref_count = cursor.fetchone()[0]

        conn.close()

        # Content size
        observations = row['observations'] or ''
        content_size = len(observations)

        return GranularityMetrics(
            importance_score=row['importance_score'],
            access_frequency=access_frequency,
            recency_days=recency_days,
            reasoning_category=bool(row['reasoning_category']),
            reference_count=ref_count,
            content_size_chars=content_size
        )

    def evaluate_and_adjust_granularity(
        self,
        entity_id: int,
        force_check: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluate if memory granularity should be adjusted.

        Args:
            entity_id: Memory entity ID
            force_check: Force re-evaluation even if recently checked

        Returns:
            Adjustment result with old/new levels and reason
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Check if recently evaluated (skip if within last hour unless forced)
        if not force_check:
            cursor.execute('''
                SELECT last_granularity_check FROM memory_granularity
                WHERE entity_id = ?
            ''', (entity_id,))
            row = cursor.fetchone()
            if row and row[0]:
                last_check = datetime.fromisoformat(row[0])
                if (datetime.now() - last_check).total_seconds() < 3600:
                    conn.close()
                    return {
                        'entity_id': entity_id,
                        'adjusted': False,
                        'reason': 'Recently checked'
                    }

        # Compute current metrics
        metrics = self.compute_entity_metrics(entity_id)
        if not metrics:
            conn.close()
            return {
                'entity_id': entity_id,
                'adjusted': False,
                'reason': 'Entity not found'
            }

        # Determine optimal granularity
        optimal = metrics.compute_optimal_granularity()

        # Get current level
        cursor.execute(
            'SELECT current_level FROM memory_granularity WHERE entity_id = ?',
            (entity_id,)
        )
        row = cursor.fetchone()
        current_level = GranularityLevel(row[0]) if row else GranularityLevel.DETAILED

        result = {
            'entity_id': entity_id,
            'current_level': current_level.value,
            'optimal_level': optimal.value,
            'adjusted': False,
            'metrics': asdict(metrics)
        }

        # Adjust if needed
        if optimal != current_level:
            # Log transition
            cursor.execute('''
                INSERT INTO granularity_transitions
                (entity_id, old_level, new_level, trigger_reason, metrics_snapshot)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                entity_id,
                current_level.value,
                optimal.value,
                'automatic_optimization',
                json.dumps(asdict(metrics))
            ))

            # Update granularity
            cursor.execute('''
                INSERT INTO memory_granularity
                (entity_id, current_level, last_granularity_check)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(entity_id) DO UPDATE SET
                    current_level = ?,
                    last_granularity_check = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
            ''', (entity_id, optimal.value, optimal.value))

            result['adjusted'] = True
            result['reason'] = f'Optimized from {current_level.value} to {optimal.value}'

            logger.info(f"Adjusted granularity for entity {entity_id}: {current_level.value} → {optimal.value}")
        else:
            # Just update check time
            cursor.execute('''
                INSERT INTO memory_granularity (entity_id, last_granularity_check)
                VALUES (?, CURRENT_TIMESTAMP)
                ON CONFLICT(entity_id) DO UPDATE SET
                    last_granularity_check = CURRENT_TIMESTAMP
            ''', (entity_id,))
            result['reason'] = 'Already optimal'

        conn.commit()
        conn.close()

        return result

    def batch_optimize_granularity(
        self,
        limit: int = 100,
        min_age_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Batch optimize granularity for old/stale memories.

        Args:
            limit: Maximum entities to process
            min_age_hours: Only process entities older than this

        Returns:
            Optimization summary
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cutoff = (datetime.now() - timedelta(hours=min_age_hours)).isoformat()

        # Find entities needing optimization
        cursor.execute('''
            SELECT e.id FROM entities e
            LEFT JOIN memory_granularity g ON e.id = g.entity_id
            WHERE e.created_at < ?
            AND (g.last_granularity_check IS NULL
                 OR g.last_granularity_check < datetime('now', '-24 hours'))
            LIMIT ?
        ''', (cutoff, limit))

        entity_ids = [row[0] for row in cursor.fetchall()]
        conn.close()

        results = {
            'processed': 0,
            'adjusted': 0,
            'by_level': {},
            'errors': 0
        }

        for entity_id in entity_ids:
            try:
                result = self.evaluate_and_adjust_granularity(entity_id, force_check=True)
                results['processed'] += 1

                if result.get('adjusted'):
                    results['adjusted'] += 1
                    new_level = result.get('optimal_level', 'unknown')
                    results['by_level'][new_level] = results['by_level'].get(new_level, 0) + 1

            except Exception as e:
                logger.error(f"Error optimizing entity {entity_id}: {e}")
                results['errors'] += 1

        logger.info(f"Batch optimization complete: {results['processed']} processed, {results['adjusted']} adjusted")

        return results

    def get_granularity_statistics(self) -> Dict[str, Any]:
        """Get statistics about memory granularity distribution."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Count by level
        cursor.execute('''
            SELECT current_level, COUNT(*) as count
            FROM memory_granularity
            GROUP BY current_level
        ''')
        by_level = {row[0]: row[1] for row in cursor.fetchall()}

        # Average compression ratio
        cursor.execute('SELECT AVG(compression_ratio) FROM memory_granularity')
        avg_compression = cursor.fetchone()[0] or 1.0

        # Total entities vs tracked
        cursor.execute('SELECT COUNT(*) FROM entities')
        total_entities = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM memory_granularity')
        tracked_entities = cursor.fetchone()[0]

        # Recent transitions
        cursor.execute('''
            SELECT old_level, new_level, COUNT(*) as count
            FROM granularity_transitions
            WHERE transitioned_at > datetime('now', '-24 hours')
            GROUP BY old_level, new_level
        ''')
        recent_transitions = [
            {'from': row[0], 'to': row[1], 'count': row[2]}
            for row in cursor.fetchall()
        ]

        conn.close()

        return {
            'by_level': by_level,
            'avg_compression_ratio': avg_compression,
            'total_entities': total_entities,
            'tracked_entities': tracked_entities,
            'coverage_percent': (tracked_entities / total_entities * 100) if total_entities > 0 else 0,
            'recent_transitions_24h': recent_transitions
        }

    def promote_to_fine_granularity(
        self,
        entity_id: int,
        reason: str = "manual_promotion"
    ) -> Dict[str, Any]:
        """
        Manually promote a memory to fine granularity (ATOMIC/DETAILED).

        Use when a memory becomes important and needs full detail preserved.

        Args:
            entity_id: Memory entity ID
            reason: Reason for promotion

        Returns:
            Promotion result
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Get current level
        cursor.execute(
            'SELECT current_level FROM memory_granularity WHERE entity_id = ?',
            (entity_id,)
        )
        row = cursor.fetchone()
        old_level = row[0] if row else 'detailed'

        new_level = GranularityLevel.ATOMIC.value

        # Log transition
        cursor.execute('''
            INSERT INTO granularity_transitions
            (entity_id, old_level, new_level, trigger_reason)
            VALUES (?, ?, ?, ?)
        ''', (entity_id, old_level, new_level, reason))

        # Update
        cursor.execute('''
            INSERT INTO memory_granularity
            (entity_id, current_level, importance_score, last_granularity_check)
            VALUES (?, ?, 1.0, CURRENT_TIMESTAMP)
            ON CONFLICT(entity_id) DO UPDATE SET
                current_level = ?,
                importance_score = 1.0,
                last_granularity_check = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
        ''', (entity_id, new_level, new_level))

        conn.commit()
        conn.close()

        logger.info(f"Promoted entity {entity_id} to {new_level}: {reason}")

        return {
            'entity_id': entity_id,
            'old_level': old_level,
            'new_level': new_level,
            'reason': reason
        }


# Singleton instance
_manager = None

def get_adaptive_granularity_manager() -> AdaptiveGranularityManager:
    """Get singleton manager instance."""
    global _manager
    if _manager is None:
        _manager = AdaptiveGranularityManager()
    return _manager
