#!/usr/bin/env python3
"""
Surprise-Based Memory Consolidation Tools for FastMCP

Implements Titans/MIRAS-inspired surprise scoring for memory consolidation.
Only stores unexpected/novel information, skips predictable content.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def register_surprise_consolidation_tools(app, db_path):
    """Register all surprise-based consolidation tools with FastMCP app"""

    # Import here to avoid circular dependencies
    from surprise_consolidation import SurpriseConsolidator, surprise_based_consolidation
    from surprise_memory import SurpriseBasedMemory, RetentionGate

    # Tool 1: Run Surprise-Based Consolidation
    @app.tool()
    async def run_surprise_consolidation(
        time_window_hours: int = 24,
        min_surprise_threshold: float = 0.4
    ) -> Dict[str, Any]:
        """
        Run surprise-based memory consolidation (Titans/MIRAS inspired).

        Uses surprise scoring to decide which memories to promote:
        - High surprise (novel/unexpected) → Promote to semantic
        - Low surprise (predictable) → Skip storage
        - Very high surprise → Immediate promotion + momentum for related memories

        The retention gate manages capacity by forgetting low-priority memories
        when storage exceeds limits.

        Args:
            time_window_hours: Hours of memories to consolidate (default 24)
            min_surprise_threshold: Minimum surprise score to store (default 0.4)

        Returns:
            Consolidation results with metrics:
            - memories_evaluated: Total memories processed
            - memories_promoted: High-surprise promoted to semantic
            - memories_skipped: Low-surprise skipped
            - memories_forgotten: Removed by retention gate
            - average_surprise_score: Mean surprise across all

        Example:
            run_surprise_consolidation(time_window_hours=24, min_surprise_threshold=0.4)
        """
        try:
            # Get episodic memories from database
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Fetch recent episodic memories
            # Note: episodic_memory table uses episode_data (not content) and event_type (not memory_type)
            cursor.execute("""
                SELECT id, episode_data, event_type, created_at, significance_score
                FROM episodic_memory
                WHERE created_at > datetime('now', ?)
                ORDER BY created_at DESC
            """, (f'-{time_window_hours} hours',))

            rows = cursor.fetchall()
            episodic_memories = []
            for row in rows:
                episodic_memories.append({
                    'id': row['id'],
                    'content': row['episode_data'],  # Map episode_data to content for consolidator
                    'memory_type': row['event_type'] or 'episodic',
                    'created_at': row['created_at']
                })

            conn.close()

            if not episodic_memories:
                return {
                    'success': True,
                    'message': 'No episodic memories found in time window',
                    'memories_evaluated': 0,
                    'memories_promoted': 0,
                    'memories_skipped': 0,
                    'memories_forgotten': 0,
                    'average_surprise_score': 0.0
                }

            # Run surprise-based consolidation
            consolidator = SurpriseConsolidator()
            result = consolidator.consolidate_episodic_memories(
                episodic_memories=episodic_memories,
                time_window_hours=time_window_hours
            )

            # Promote high-surprise memories to semantic
            if result.get('promoted'):
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                for item in result['promoted']:
                    memory = item['memory']
                    score = item['surprise_score']
                    content = memory.get('content', '')

                    # Generate concept name from content (first 100 chars, sanitized)
                    import hashlib
                    concept_name = f"promoted_{memory.get('id', 'unknown')}_{hashlib.md5(content.encode()).hexdigest()[:8]}"

                    # Insert into semantic memory using correct schema
                    # Schema: concept_name (UNIQUE), concept_type, definition, confidence_score, related_concepts
                    cursor.execute("""
                        INSERT OR REPLACE INTO semantic_memory
                        (concept_name, concept_type, definition, confidence_score, related_concepts, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        concept_name,
                        'promoted_episodic',
                        content,
                        score.score if hasattr(score, 'score') else score,
                        f'{{"promoted_from": "episodic", "surprise_reasoning": "{item.get("reason", "")[:200]}"}}',
                        datetime.now().isoformat()
                    ))

                conn.commit()
                conn.close()

            return {
                'success': True,
                'memories_evaluated': result['metrics']['memories_evaluated'],
                'memories_promoted': result['metrics']['memories_promoted'],
                'memories_skipped': result['metrics']['memories_skipped'],
                'memories_forgotten': result['metrics']['memories_forgotten'],
                'average_surprise_score': result['metrics']['average_surprise_score'],
                'high_surprise_count': result['metrics']['high_surprise_count'],
                'low_surprise_count': result['metrics']['low_surprise_count'],
                'retention_gate_triggered': result['metrics']['retention_gate_triggered'],
                'duration_seconds': result['metrics']['duration_seconds']
            }

        except Exception as e:
            logger.error(f"Surprise consolidation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'memories_evaluated': 0,
                'memories_promoted': 0,
                'memories_skipped': 0,
                'memories_forgotten': 0,
                'average_surprise_score': 0.0
            }

    # Tool 2: Calculate Surprise Score
    @app.tool()
    async def calculate_surprise_score(
        content: str,
        memory_type: str = "episodic",
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate surprise score for a piece of content.

        Higher scores indicate more novel/unexpected content worth storing.
        Lower scores indicate predictable content that can be skipped.

        Components:
        - Novelty: How different from existing memories (embedding distance)
        - Salience: How important/meaningful (keywords, structure)
        - Temporal: How unexpected given recent context

        Args:
            content: Text to evaluate
            memory_type: Type (episodic, semantic, procedural)
            context: Recent context for temporal surprise

        Returns:
            Surprise score with components and storage decision

        Example:
            calculate_surprise_score(
                content="Discovered that parallel tool calls reduce latency by 60%",
                memory_type="semantic"
            )
        """
        try:
            scorer = SurpriseBasedMemory()

            # Parse context if provided
            ctx = None
            if context:
                ctx = {'recent_topics': [context]}

            score = scorer.calculate_surprise(
                content=content,
                memory_type=memory_type,
                context=ctx
            )

            return {
                'success': True,
                'score': score.score,
                'should_store': score.should_store,
                'components': {
                    'novelty': score.novelty_component,
                    'salience': score.salience_component,
                    'temporal': score.temporal_component
                },
                'reasoning': score.reasoning
            }

        except Exception as e:
            logger.error(f"Surprise scoring failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'score': 0.5,
                'should_store': True,
                'components': {'novelty': 0.5, 'salience': 0.5, 'temporal': 0.5},
                'reasoning': f'Error - defaulting to store: {e}'
            }

    # Tool 3: Get Retention Candidates
    @app.tool()
    async def get_retention_candidates(
        count_to_remove: int = 10
    ) -> Dict[str, Any]:
        """
        Get memories that are candidates for forgetting based on retention score.

        Retention score combines:
        - Original surprise score (novelty when stored)
        - Access frequency (frequently accessed = keep)
        - Recency (newer = keep, exponential decay)
        - Memory type (procedural > semantic > episodic)

        Args:
            count_to_remove: Number of candidates to identify

        Returns:
            List of memory IDs that are candidates for forgetting

        Example:
            get_retention_candidates(count_to_remove=10)
        """
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get all semantic memories with metadata
            # Note: semantic_memory uses concept_name, definition, concept_type, confidence_score
            cursor.execute("""
                SELECT id, concept_name, definition, concept_type, created_at,
                       COALESCE(confidence_score, 0.5) as surprise_score
                FROM semantic_memory
                ORDER BY created_at DESC
                LIMIT 10000
            """)

            rows = cursor.fetchall()
            memories = []
            for row in rows:
                memories.append({
                    'id': str(row['id']),
                    'surprise_score': row['surprise_score'],
                    'created_at': row['created_at'],
                    'memory_type': row['concept_type'] or 'semantic'
                })

            conn.close()

            if not memories:
                return {
                    'success': True,
                    'candidates': [],
                    'message': 'No memories to evaluate'
                }

            # Use retention gate to find candidates
            retention_gate = RetentionGate(
                max_memories=50000,
                decay_rate=0.02
            )

            candidates = retention_gate.get_candidates_for_forgetting(
                memories=memories,
                count_to_remove=count_to_remove
            )

            return {
                'success': True,
                'total_memories': len(memories),
                'candidates_count': len(candidates),
                'candidates': candidates
            }

        except Exception as e:
            logger.error(f"Retention analysis failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'candidates': []
            }

    # Tool 4: Get Consolidation Stats
    @app.tool()
    async def get_surprise_consolidation_stats(
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get surprise-based consolidation statistics.

        Shows consolidation performance over time including:
        - Total memories evaluated and promoted
        - Average surprise scores
        - Retention gate triggers
        - Promotion rate

        Args:
            days: Number of days to analyze (default 7)

        Returns:
            Consolidation statistics

        Example:
            get_surprise_consolidation_stats(days=7)
        """
        try:
            consolidator = SurpriseConsolidator()
            stats = consolidator.get_consolidation_stats(days=days)

            return {
                'success': True,
                **stats
            }

        except Exception as e:
            logger.error(f"Stats retrieval failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    logger.info("✅ Surprise Consolidation tools registered (4 tools)")
    logger.info("   - run_surprise_consolidation (Titans/MIRAS inspired)")
    logger.info("   - calculate_surprise_score")
    logger.info("   - get_retention_candidates")
    logger.info("   - get_surprise_consolidation_stats")
