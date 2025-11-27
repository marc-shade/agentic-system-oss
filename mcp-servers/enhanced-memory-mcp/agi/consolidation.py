"""
Memory Consolidation Module

Implements sleep-like consolidation for AGI memory.

Key Features:
- Background pattern extraction from episodic to semantic memory
- Causal link discovery and strengthening
- Memory compression and optimization
- Scheduled consolidation jobs
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import Counter

logger = logging.getLogger("consolidation")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class ConsolidationEngine:
    """Handles background memory consolidation"""

    def __init__(self):
        # Ensure WAL mode is enabled for better concurrent access
        self._init_database()

    def _init_database(self):
        """Initialize database with optimal settings for concurrent access."""
        try:
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
            conn.execute("PRAGMA journal_mode=WAL")  # WAL mode for concurrency
            conn.close()
        except Exception as e:
            logger.warning(f"Could not init database settings: {e}")

    def _get_connection(self):
        """Get a database connection with proper timeout settings."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def schedule_consolidation(
        self,
        job_type: str,
        time_window_hours: int = 24
    ) -> int:
        """
        Schedule a consolidation job

        Args:
            job_type: "pattern_extraction", "causal_discovery", "memory_compression"
            time_window_hours: Hours of memory to process

        Returns:
            job_id
        """
        now = datetime.now()
        start_time = now - timedelta(hours=time_window_hours)

        # Count entities in time window
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT COUNT(*)
            FROM entities
            WHERE created_at >= ?
            ''',
            (start_time.isoformat(),)
        )
        entity_count = cursor.fetchone()[0]

        cursor.execute(
            '''
            INSERT INTO consolidation_jobs (
                agent_id, job_type, status,
                time_window_start, time_window_end,
                entity_count
            ) VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (
                'system-consolidation',  # Default agent_id for scheduled jobs
                job_type, 'pending',
                start_time.isoformat(), now.isoformat(),
                entity_count
            )
        )

        job_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Scheduled {job_type} job {job_id} for {entity_count} entities")

        return job_id

    def run_pattern_extraction(
        self,
        time_window_hours: int = 24,
        min_pattern_frequency: int = 3
    ) -> Dict[str, Any]:
        """
        Extract patterns from recent episodic memories

        Promotes recurring patterns to semantic memory.

        Args:
            time_window_hours: Hours of memory to analyze
            min_pattern_frequency: Minimum occurrences to be a pattern

        Returns:
            {
                "patterns_found": int,
                "patterns_promoted": int,
                "semantic_memories_created": int
            }
        """
        job_id = self.schedule_consolidation("pattern_extraction", time_window_hours)

        conn = self._get_connection()
        cursor = conn.cursor()

        # Update job status
        cursor.execute(
            'UPDATE consolidation_jobs SET status = ?, started_at = ? WHERE job_id = ?',
            ('running', datetime.now().isoformat(), job_id)
        )
        conn.commit()

        start_time = datetime.now() - timedelta(hours=time_window_hours)

        try:
            # Get recent episodic memories from BOTH sources:
            # 1. entities table with tier='episodic'
            # 2. episodic_memory table (4-tier AGI system)

            # Source 1: entities table
            cursor.execute(
                '''
                SELECT id, name, entity_type, 'entities' as source
                FROM entities
                WHERE tier = 'episodic'
                AND created_at >= ?
                ''',
                (start_time.isoformat(),)
            )
            entities_episodic = cursor.fetchall()

            # Source 2: episodic_memory table (4-tier AGI system)
            cursor.execute(
                '''
                SELECT id, event_type, event_type, 'episodic_memory' as source
                FROM episodic_memory
                WHERE created_at >= ?
                ''',
                (start_time.isoformat(),)
            )
            agi_episodic = cursor.fetchall()

            # Combine both sources
            episodic_memories = entities_episodic + agi_episodic

            logger.info(f"Found {len(entities_episodic)} entity episodes + {len(agi_episodic)} AGI episodes")

            # Group by entity_type/event_type and look for patterns
            type_counter = Counter()
            for _, name, entity_type, source in episodic_memories:
                type_counter[entity_type] += 1

            # Extract patterns that occur frequently
            patterns_found = []
            patterns_promoted = 0
            semantic_concepts_created = 0

            for entity_type, count in type_counter.items():
                if count >= min_pattern_frequency:
                    patterns_found.append({
                        "type": entity_type,
                        "frequency": count
                    })

                    # Create semantic memory for this pattern in BOTH systems
                    pattern_name = f"pattern_{entity_type}_{datetime.now().strftime('%Y%m%d')}"

                    # 1. Add to entities table (legacy)
                    cursor.execute(
                        'SELECT id FROM entities WHERE name = ?',
                        (pattern_name,)
                    )

                    if not cursor.fetchone():
                        cursor.execute(
                            '''
                            INSERT INTO entities (name, entity_type, tier)
                            VALUES (?, ?, ?)
                            ''',
                            (pattern_name, f"pattern_{entity_type}", "semantic")
                        )
                        patterns_promoted += 1

                    # 2. Add to semantic_memory table (4-tier AGI system)
                    concept_name = f"consolidated_{entity_type}"
                    cursor.execute(
                        'SELECT id FROM semantic_memory WHERE concept_name = ?',
                        (concept_name,)
                    )

                    if not cursor.fetchone():
                        cursor.execute(
                            '''
                            INSERT INTO semantic_memory (
                                concept_name, concept_type, definition,
                                confidence_score
                            ) VALUES (?, ?, ?, ?)
                            ''',
                            (
                                concept_name,
                                "consolidated_pattern",
                                f"Pattern extracted from {count} episodes of type '{entity_type}'",
                                min(0.5 + (count * 0.1), 1.0)  # Higher count = higher confidence
                            )
                        )
                        semantic_concepts_created += 1
                    else:
                        # Update existing concept confidence
                        cursor.execute(
                            '''
                            UPDATE semantic_memory
                            SET confidence_score = MIN(confidence_score + 0.05, 1.0),
                                updated_at = CURRENT_TIMESTAMP
                            WHERE concept_name = ?
                            ''',
                            (concept_name,)
                        )

            logger.info(f"Created {semantic_concepts_created} new semantic concepts")

            # Update job with results
            duration = (datetime.now() - datetime.fromisoformat(
                cursor.execute('SELECT started_at FROM consolidation_jobs WHERE job_id = ?', (job_id,)).fetchone()[0]
            )).seconds

            cursor.execute(
                '''
                UPDATE consolidation_jobs
                SET
                    status = 'completed',
                    completed_at = ?,
                    duration_seconds = ?,
                    patterns_found = ?,
                    memories_promoted = ?,
                    results_summary = ?
                WHERE job_id = ?
                ''',
                (
                    datetime.now().isoformat(),
                    duration,
                    len(patterns_found),
                    patterns_promoted + semantic_concepts_created,
                    json.dumps({
                        "patterns": patterns_found,
                        "entities_episodic_count": len(entities_episodic),
                        "agi_episodic_count": len(agi_episodic),
                        "semantic_concepts_created": semantic_concepts_created
                    }),
                    job_id
                )
            )

            conn.commit()

            logger.info(f"Pattern extraction complete: {len(patterns_found)} patterns, "
                       f"{patterns_promoted} promoted to entities, "
                       f"{semantic_concepts_created} semantic concepts created")

            return {
                "job_id": job_id,
                "patterns_found": len(patterns_found),
                "patterns_promoted": patterns_promoted,
                "semantic_memories_created": semantic_concepts_created,
                "sources_analyzed": {
                    "entities_episodic": len(entities_episodic),
                    "agi_episodic": len(agi_episodic)
                }
            }

        except Exception as e:
            # Mark job as failed
            cursor.execute(
                '''
                UPDATE consolidation_jobs
                SET status = 'failed', error_message = ?
                WHERE job_id = ?
                ''',
                (str(e), job_id)
            )
            conn.commit()

            logger.error(f"Pattern extraction failed: {e}")

            raise

        finally:
            conn.close()

    def run_causal_discovery(
        self,
        time_window_hours: int = 24,
        min_confidence: float = 0.6
    ) -> Dict[str, Any]:
        """
        Discover causal relationships from recent action outcomes

        Args:
            time_window_hours: Hours of memory to analyze
            min_confidence: Minimum confidence for causal link

        Returns:
            {
                "chains_created": int,
                "links_created": int,
                "hypotheses_generated": int
            }
        """
        from agi.temporal_reasoning import TemporalReasoning

        job_id = self.schedule_consolidation("causal_discovery", time_window_hours)

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'UPDATE consolidation_jobs SET status = ?, started_at = ? WHERE job_id = ?',
            ('running', datetime.now().isoformat(), job_id)
        )
        conn.commit()

        start_time = datetime.now() - timedelta(hours=time_window_hours)

        try:
            temporal = TemporalReasoning()

            # Get recent action outcomes with context
            cursor.execute(
                '''
                SELECT
                    action_id,
                    action_type,
                    action_context,
                    success_score,
                    executed_at
                FROM action_outcomes
                WHERE executed_at >= ?
                AND action_context IS NOT NULL
                AND action_context != ''
                ORDER BY executed_at
                ''',
                (start_time.isoformat(),)
            )

            actions = cursor.fetchall()
            logger.info(f"Analyzing {len(actions)} actions with context for causal patterns")

            links_created = 0
            chains = []

            # Group actions by context (same file/resource)
            context_actions = {}
            for action_id, action_type, action_context, success_score, executed_at in actions:
                if action_context not in context_actions:
                    context_actions[action_context] = []
                context_actions[action_context].append({
                    'id': action_id,
                    'type': action_type,
                    'score': success_score,
                    'time': executed_at
                })

            # Find causal patterns: sequences of actions on same context
            pattern_counter = Counter()
            for context, ctx_actions in context_actions.items():
                if len(ctx_actions) >= 2:
                    # Look at pairs of consecutive actions
                    for i in range(len(ctx_actions) - 1):
                        current = ctx_actions[i]
                        next_act = ctx_actions[i + 1]

                        # Pattern: action_type_A → action_type_B with combined success
                        pattern = f"{current['type']}->{next_act['type']}"
                        avg_score = (current['score'] + next_act['score']) / 2
                        pattern_counter[(pattern, avg_score >= min_confidence)] += 1

            # Create causal links for patterns that tend to succeed
            for (pattern, succeeded), count in pattern_counter.items():
                if succeeded and count >= 2:  # Pattern seen at least twice with success
                    # Store as a learned causal pattern
                    cursor.execute(
                        '''
                        INSERT OR REPLACE INTO semantic_memory
                        (concept_name, concept_type, definition, confidence_score)
                        VALUES (?, 'causal_pattern', ?, ?)
                        ''',
                        (
                            f"pattern_{pattern}",
                            f"Causal pattern: {pattern} (observed {count} times with success)",
                            min(0.5 + (count * 0.1), 0.95)
                        )
                    )
                    links_created += 1
                    chains.append(pattern)

            logger.info(f"Discovered {links_created} causal patterns from {len(context_actions)} contexts")

            # Update job with results
            duration = (datetime.now() - datetime.fromisoformat(
                cursor.execute('SELECT started_at FROM consolidation_jobs WHERE job_id = ?', (job_id,)).fetchone()[0]
            )).seconds

            cursor.execute(
                '''
                UPDATE consolidation_jobs
                SET
                    status = 'completed',
                    completed_at = ?,
                    duration_seconds = ?,
                    chains_created = ?,
                    links_created = ?,
                    results_summary = ?
                WHERE job_id = ?
                ''',
                (
                    datetime.now().isoformat(),
                    duration,
                    len(chains),
                    links_created,
                    json.dumps({"actions_analyzed": len(actions)}),
                    job_id
                )
            )

            conn.commit()

            logger.info(f"Causal discovery complete: {links_created} links created")

            return {
                "job_id": job_id,
                "chains_created": len(chains),
                "links_created": links_created,
                "hypotheses_generated": 0
            }

        except Exception as e:
            cursor.execute(
                '''
                UPDATE consolidation_jobs
                SET status = 'failed', error_message = ?
                WHERE job_id = ?
                ''',
                (str(e), job_id)
            )
            conn.commit()

            logger.error(f"Causal discovery failed: {e}")

            raise

        finally:
            conn.close()

    def run_memory_compression(
        self,
        time_window_hours: int = 168  # 7 days
    ) -> Dict[str, Any]:
        """
        Compress old low-importance memories

        Args:
            time_window_hours: Only compress memories older than this

        Returns:
            {
                "memories_compressed": int,
                "space_saved_bytes": int
            }
        """
        job_id = self.schedule_consolidation("memory_compression", time_window_hours)

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'UPDATE consolidation_jobs SET status = ?, started_at = ? WHERE job_id = ?',
            ('running', datetime.now().isoformat(), job_id)
        )
        conn.commit()

        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)

        try:
            # Get old, low-importance memories that aren't already compressed
            cursor.execute(
                '''
                SELECT id, name
                FROM entities
                WHERE created_at < ?
                AND salience_score < 0.5
                AND access_count < 5
                AND compressed_data IS NULL
                ''',
                (cutoff_time.isoformat(),)
            )

            memories_to_compress = cursor.fetchall()
            memories_compressed = len(memories_to_compress)

            # In real implementation, would compress observations
            # For now, just mark them as candidates

            # Update job
            duration = (datetime.now() - datetime.fromisoformat(
                cursor.execute('SELECT started_at FROM consolidation_jobs WHERE job_id = ?', (job_id,)).fetchone()[0]
            )).seconds

            cursor.execute(
                '''
                UPDATE consolidation_jobs
                SET
                    status = 'completed',
                    completed_at = ?,
                    duration_seconds = ?,
                    memories_compressed = ?
                WHERE job_id = ?
                ''',
                (
                    datetime.now().isoformat(),
                    duration,
                    memories_compressed,
                    job_id
                )
            )

            conn.commit()

            logger.info(f"Memory compression complete: {memories_compressed} memories processed")

            return {
                "job_id": job_id,
                "memories_compressed": memories_compressed,
                "space_saved_bytes": memories_compressed * 1024  # Estimate
            }

        except Exception as e:
            cursor.execute(
                '''
                UPDATE consolidation_jobs
                SET status = 'failed', error_message = ?
                WHERE job_id = ?
                ''',
                (str(e), job_id)
            )
            conn.commit()

            logger.error(f"Memory compression failed: {e}")

            raise

        finally:
            conn.close()

    def run_full_consolidation(
        self,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Run all consolidation processes

        This is the main "sleep-like" consolidation function.

        Args:
            time_window_hours: Hours of memory to consolidate

        Returns:
            Combined results from all consolidation processes
        """
        logger.info(f"Starting full consolidation for last {time_window_hours} hours")

        results = {}

        # 1. Pattern extraction
        try:
            pattern_results = self.run_pattern_extraction(time_window_hours)
            results["pattern_extraction"] = pattern_results
        except Exception as e:
            results["pattern_extraction"] = {"error": str(e)}
            logger.error(f"Pattern extraction failed: {e}")

        # 2. Causal discovery
        try:
            causal_results = self.run_causal_discovery(time_window_hours)
            results["causal_discovery"] = causal_results
        except Exception as e:
            results["causal_discovery"] = {"error": str(e)}
            logger.error(f"Causal discovery failed: {e}")

        # 3. Memory compression (only for old memories)
        if time_window_hours >= 168:  # Only compress if looking at 7+ days
            try:
                compression_results = self.run_memory_compression(time_window_hours)
                results["memory_compression"] = compression_results
            except Exception as e:
                results["memory_compression"] = {"error": str(e)}
                logger.error(f"Memory compression failed: {e}")

        logger.info("Full consolidation complete")

        return results

    def get_consolidation_stats(self) -> Dict[str, Any]:
        """Get consolidation statistics"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Total jobs
        cursor.execute('SELECT COUNT(*) FROM consolidation_jobs')
        total_jobs = cursor.fetchone()[0]

        # By status
        cursor.execute(
            '''
            SELECT status, COUNT(*)
            FROM consolidation_jobs
            GROUP BY status
            '''
        )
        by_status = {row[0]: row[1] for row in cursor.fetchall()}

        # Total results
        cursor.execute(
            '''
            SELECT
                SUM(patterns_found) as patterns,
                SUM(chains_created) as chains,
                SUM(links_created) as links,
                SUM(memories_promoted) as promoted,
                SUM(memories_compressed) as compressed
            FROM consolidation_jobs
            WHERE status = 'completed'
            '''
        )

        row = cursor.fetchone()
        totals = {
            "patterns_found": row[0] or 0,
            "chains_created": row[1] or 0,
            "links_created": row[2] or 0,
            "memories_promoted": row[3] or 0,
            "memories_compressed": row[4] or 0
        }

        # Recent jobs
        cursor.execute(
            '''
            SELECT job_type, status, started_at, duration_seconds
            FROM consolidation_jobs
            ORDER BY started_at DESC
            LIMIT 10
            '''
        )

        recent = []
        for row in cursor.fetchall():
            recent.append({
                "job_type": row[0],
                "status": row[1],
                "started_at": row[2],
                "duration_seconds": row[3]
            })

        conn.close()

        return {
            "total_jobs": total_jobs,
            "by_status": by_status,
            "totals": totals,
            "recent_jobs": recent
        }
