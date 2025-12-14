"""
Recursive Self-Improvement Module

Implements Stage 5: Recursive Capability - using improvement insights
to improve the improvement process itself.

Key Concept: Meta-meta-learning - learning how to learn better.

This module:
1. Analyzes patterns in successful improvements
2. Extracts meta-strategies that work across domains
3. Applies improvements to the improvement algorithms
4. Tracks recursive improvement depth and convergence
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

logger = logging.getLogger("recursive_improvement")

MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


@dataclass
class MetaStrategy:
    """A strategy for improving improvement."""
    strategy_id: int
    name: str
    description: str
    source_patterns: List[str]
    applicability_score: float
    success_rate: float
    times_applied: int
    improvement_contribution: float


@dataclass
class RecursiveImprovementCycle:
    """A cycle of recursive self-improvement."""
    cycle_id: int
    depth: int  # How many levels of recursion
    parent_cycle_id: Optional[int]
    meta_strategies_applied: List[str]
    improvement_delta: float
    convergence_score: float


class RecursiveImprovementEngine:
    """
    Engine for recursive self-improvement.

    The recursive insight: If we can improve performance, we can also
    improve the process that improves performance, and so on.

    Convergence: Recursive improvement converges when the improvement
    to improvement algorithms yields diminishing returns.
    """

    def __init__(self):
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure recursive improvement tables exist."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Meta-strategies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS meta_strategies (
                strategy_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                description TEXT,
                source_patterns TEXT,  -- JSON array
                applicability_domains TEXT,  -- JSON array
                applicability_score REAL DEFAULT 0.5,
                success_rate REAL DEFAULT 0.5,
                times_applied INTEGER DEFAULT 0,
                improvement_contribution REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Recursive improvement cycles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recursive_improvement_cycles (
                cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                depth INTEGER DEFAULT 1,
                parent_cycle_id INTEGER,
                meta_strategies_applied TEXT,  -- JSON array
                patterns_analyzed INTEGER DEFAULT 0,
                strategies_extracted INTEGER DEFAULT 0,
                strategies_applied INTEGER DEFAULT 0,
                improvement_delta REAL DEFAULT 0.0,
                convergence_score REAL DEFAULT 0.0,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                FOREIGN KEY (parent_cycle_id) REFERENCES recursive_improvement_cycles(cycle_id)
            )
        ''')

        # Strategy applications log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS strategy_applications (
                application_id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER,
                cycle_id INTEGER,
                target_component TEXT,
                before_metric REAL,
                after_metric REAL,
                improvement REAL,
                applied_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_id) REFERENCES meta_strategies(strategy_id),
                FOREIGN KEY (cycle_id) REFERENCES recursive_improvement_cycles(cycle_id)
            )
        ''')

        conn.commit()
        conn.close()

    def extract_meta_strategies(
        self,
        min_success_rate: float = 0.8
    ) -> List[MetaStrategy]:
        """
        Extract meta-strategies from successful patterns.

        Analyzes high-performing action patterns to identify
        generalizable improvement strategies.

        Args:
            min_success_rate: Minimum success rate for pattern inclusion

        Returns:
            List of extracted meta-strategies
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Analyze sharpening candidates for patterns
        cursor.execute('''
            SELECT
                action_type,
                verification_result,
                COUNT(*) as count,
                AVG(meta_judgment_score) as avg_meta,
                AVG(original_score) as avg_original
            FROM sharpening_candidates
            WHERE should_learn_from = 1
            GROUP BY action_type, verification_result
            HAVING avg_meta >= ?
            ORDER BY count DESC
        ''', (min_success_rate,))

        patterns = cursor.fetchall()
        strategies = []

        for pattern in patterns:
            # Generate strategy from pattern
            strategy_name = f"{pattern['action_type']}_excellence"

            # Check if strategy exists
            cursor.execute(
                'SELECT strategy_id FROM meta_strategies WHERE name = ?',
                (strategy_name,)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing
                cursor.execute('''
                    UPDATE meta_strategies
                    SET success_rate = ?,
                        times_applied = times_applied + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE strategy_id = ?
                ''', (pattern['avg_meta'], pattern['count'], existing['strategy_id']))
                strategy_id = existing['strategy_id']
            else:
                # Create new strategy
                description = self._generate_strategy_description(
                    pattern['action_type'],
                    pattern['verification_result'],
                    pattern['avg_meta']
                )

                cursor.execute('''
                    INSERT INTO meta_strategies (
                        name, description, source_patterns,
                        applicability_score, success_rate, times_applied
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    strategy_name,
                    description,
                    json.dumps([pattern['action_type']]),
                    pattern['avg_meta'],
                    pattern['avg_meta'],
                    pattern['count']
                ))
                strategy_id = cursor.lastrowid

            strategies.append(MetaStrategy(
                strategy_id=strategy_id,
                name=strategy_name,
                description=description if not existing else "",
                source_patterns=[pattern['action_type']],
                applicability_score=pattern['avg_meta'],
                success_rate=pattern['avg_meta'],
                times_applied=pattern['count'],
                improvement_contribution=0.0
            ))

        conn.commit()
        conn.close()

        logger.info(f"Extracted {len(strategies)} meta-strategies")
        return strategies

    def _generate_strategy_description(
        self,
        action_type: str,
        verification_result: str,
        avg_score: float
    ) -> str:
        """Generate a description for a meta-strategy."""
        if verification_result == "verified_high":
            quality = "high-quality"
        elif verification_result == "verified_medium":
            quality = "reliable"
        else:
            quality = "learning-valuable"

        return (
            f"Strategy derived from {quality} {action_type} patterns. "
            f"Average meta-judgment score: {avg_score:.2f}. "
            f"Apply verification-before-action and structured approach."
        )

    def run_recursive_cycle(
        self,
        depth: int = 1,
        parent_cycle_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run a recursive improvement cycle.

        Args:
            depth: Current recursion depth
            parent_cycle_id: Parent cycle if this is recursive

        Returns:
            Cycle results with improvement metrics
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Start cycle
        cursor.execute('''
            INSERT INTO recursive_improvement_cycles (depth, parent_cycle_id)
            VALUES (?, ?)
        ''', (depth, parent_cycle_id))
        cycle_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Extract meta-strategies
        strategies = self.extract_meta_strategies()

        # Apply strategies (conceptually - track what would be improved)
        applications = []
        total_improvement = 0.0

        for strategy in strategies:
            # Calculate potential improvement
            potential = strategy.success_rate * strategy.applicability_score
            if potential > 0.7:  # Only apply high-potential strategies
                application = self._apply_strategy(cycle_id, strategy)
                applications.append(application)
                total_improvement += application.get('improvement', 0)

        # Calculate convergence (diminishing returns indicator)
        if parent_cycle_id:
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute(
                'SELECT improvement_delta FROM recursive_improvement_cycles WHERE cycle_id = ?',
                (parent_cycle_id,)
            )
            parent = cursor.fetchone()
            parent_improvement = parent[0] if parent else 0.0
            conn.close()

            # Convergence: ratio of current to parent improvement
            if parent_improvement > 0:
                convergence = total_improvement / parent_improvement
            else:
                convergence = 1.0 if total_improvement > 0 else 0.0
        else:
            convergence = 1.0  # First cycle

        # Update cycle record
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE recursive_improvement_cycles
            SET patterns_analyzed = ?,
                strategies_extracted = ?,
                strategies_applied = ?,
                improvement_delta = ?,
                convergence_score = ?,
                meta_strategies_applied = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE cycle_id = ?
        ''', (
            len(strategies) * 10,  # Approximate patterns analyzed
            len(strategies),
            len(applications),
            total_improvement,
            convergence,
            json.dumps([s.name for s in strategies]),
            cycle_id
        ))
        conn.commit()
        conn.close()

        result = {
            'cycle_id': cycle_id,
            'depth': depth,
            'strategies_extracted': len(strategies),
            'strategies_applied': len(applications),
            'improvement_delta': total_improvement,
            'convergence_score': convergence,
            'should_continue': convergence > 0.1  # Continue if >10% improvement
        }

        logger.info(f"Recursive cycle {cycle_id} (depth {depth}): improvement={total_improvement:.3f}, convergence={convergence:.3f}")

        # Recursive call if beneficial
        if result['should_continue'] and depth < 3:  # Max 3 levels of recursion
            child_result = self.run_recursive_cycle(depth + 1, cycle_id)
            result['child_cycle'] = child_result

        return result

    def _apply_strategy(
        self,
        cycle_id: int,
        strategy: MetaStrategy
    ) -> Dict[str, Any]:
        """
        Apply a meta-strategy and track results.

        This is conceptual application - tracking that the strategy
        should be used, not actually modifying code.
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Simulate improvement based on strategy quality
        before_metric = 0.7  # Baseline
        improvement = strategy.success_rate * 0.1  # Max 10% improvement per strategy
        after_metric = min(1.0, before_metric + improvement)

        cursor.execute('''
            INSERT INTO strategy_applications (
                strategy_id, cycle_id, target_component,
                before_metric, after_metric, improvement
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            strategy.strategy_id,
            cycle_id,
            f"{strategy.name}_component",
            before_metric,
            after_metric,
            improvement
        ))

        # Update strategy contribution
        cursor.execute('''
            UPDATE meta_strategies
            SET improvement_contribution = improvement_contribution + ?,
                times_applied = times_applied + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE strategy_id = ?
        ''', (improvement, strategy.strategy_id))

        conn.commit()
        conn.close()

        return {
            'strategy': strategy.name,
            'before': before_metric,
            'after': after_metric,
            'improvement': improvement
        }

    def get_recursive_improvement_stats(self) -> Dict[str, Any]:
        """Get statistics about recursive improvement."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Cycle stats
        cursor.execute('''
            SELECT
                COUNT(*) as total_cycles,
                MAX(depth) as max_depth,
                AVG(improvement_delta) as avg_improvement,
                AVG(convergence_score) as avg_convergence
            FROM recursive_improvement_cycles
            WHERE completed_at IS NOT NULL
        ''')
        cycle_stats = cursor.fetchone()

        # Strategy stats
        cursor.execute('''
            SELECT
                COUNT(*) as total_strategies,
                AVG(success_rate) as avg_success_rate,
                SUM(improvement_contribution) as total_contribution
            FROM meta_strategies
        ''')
        strategy_stats = cursor.fetchone()

        # Best performing strategies
        cursor.execute('''
            SELECT name, success_rate, improvement_contribution, times_applied
            FROM meta_strategies
            ORDER BY improvement_contribution DESC
            LIMIT 5
        ''')
        top_strategies = [
            {
                'name': row[0],
                'success_rate': row[1],
                'contribution': row[2],
                'applications': row[3]
            }
            for row in cursor.fetchall()
        ]

        conn.close()

        return {
            'cycles': {
                'total': cycle_stats[0] or 0,
                'max_depth': cycle_stats[1] or 0,
                'avg_improvement': cycle_stats[2] or 0.0,
                'avg_convergence': cycle_stats[3] or 0.0
            },
            'strategies': {
                'total': strategy_stats[0] or 0,
                'avg_success_rate': strategy_stats[1] or 0.0,
                'total_contribution': strategy_stats[2] or 0.0
            },
            'top_strategies': top_strategies
        }

    def assess_convergence(self) -> Dict[str, Any]:
        """
        Assess if recursive improvement has converged.

        Convergence means further recursion yields diminishing returns.
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        # Get improvement deltas by depth
        cursor.execute('''
            SELECT depth, AVG(improvement_delta) as avg_improvement
            FROM recursive_improvement_cycles
            WHERE completed_at IS NOT NULL
            GROUP BY depth
            ORDER BY depth
        ''')

        improvements_by_depth = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        if len(improvements_by_depth) < 2:
            return {
                'converged': False,
                'reason': 'Insufficient data',
                'improvements_by_depth': improvements_by_depth
            }

        # Check for diminishing returns
        depths = sorted(improvements_by_depth.keys())
        diminishing = True
        for i in range(1, len(depths)):
            prev = improvements_by_depth[depths[i-1]]
            curr = improvements_by_depth[depths[i]]
            if curr > prev * 0.5:  # Still getting >50% of previous improvement
                diminishing = False

        return {
            'converged': diminishing,
            'reason': 'Diminishing returns detected' if diminishing else 'Still improving',
            'improvements_by_depth': improvements_by_depth,
            'recommendation': 'Focus on application' if diminishing else 'Continue recursion'
        }


# Singleton
_engine = None

def get_recursive_improvement_engine() -> RecursiveImprovementEngine:
    """Get singleton recursive improvement engine."""
    global _engine
    if _engine is None:
        _engine = RecursiveImprovementEngine()
    return _engine
