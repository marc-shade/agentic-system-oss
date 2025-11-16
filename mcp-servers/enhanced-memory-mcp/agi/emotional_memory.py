"""
Emotional Memory Module

Implements emotional tagging and context for AGI memory.

Key Features:
- Emotional valence, arousal, and dominance (Russell's circumplex model)
- Salience/importance scoring
- Forgetting curves (Ebbinghaus)
- Context-dependent retrieval
- Attention mechanisms
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from math import exp

logger = logging.getLogger("emotional-memory")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class EmotionalMemory:
    """Manages emotional tagging and salience for memories"""

    def __init__(self):
        pass

    def tag_entity(
        self,
        entity_id: int,
        valence: float = 0.0,
        arousal: float = 0.0,
        dominance: float = 0.5,
        primary_emotion: Optional[str] = None,
        emotion_intensity: float = 0.5,
        salience_score: float = 0.5,
        context_type: Optional[str] = None
    ) -> int:
        """
        Tag an entity with emotional metadata

        Args:
            entity_id: Entity to tag
            valence: -1.0 (negative) to +1.0 (positive)
            arousal: 0.0 (calm) to 1.0 (excited)
            dominance: 0.0 (controlled) to 1.0 (in control)
            primary_emotion: joy, sadness, anger, fear, surprise, disgust
            emotion_intensity: 0.0 to 1.0
            salience_score: 0.0 (unimportant) to 1.0 (critical)
            context_type: success, failure, neutral, surprising

        Returns:
            tag_id
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''
                INSERT INTO emotional_tags (
                    entity_id, valence, arousal, dominance,
                    primary_emotion, emotion_intensity,
                    salience_score, context_type,
                    initial_strength, current_strength
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    entity_id, valence, arousal, dominance,
                    primary_emotion, emotion_intensity,
                    salience_score, context_type,
                    1.0, 1.0  # Initial strengths
                )
            )

            tag_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Tagged entity {entity_id}: valence={valence:.2f}, "
                       f"arousal={arousal:.2f}, salience={salience_score:.2f}")

            return tag_id

        except sqlite3.IntegrityError:
            # Tag already exists, update it
            cursor.execute(
                '''
                UPDATE emotional_tags
                SET
                    valence = ?,
                    arousal = ?,
                    dominance = ?,
                    primary_emotion = ?,
                    emotion_intensity = ?,
                    salience_score = ?,
                    context_type = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE entity_id = ?
                RETURNING tag_id
                ''',
                (
                    valence, arousal, dominance,
                    primary_emotion, emotion_intensity,
                    salience_score, context_type,
                    entity_id
                )
            )

            row = cursor.fetchone()
            tag_id = row[0] if row else None
            conn.commit()

            logger.info(f"Updated emotional tag for entity {entity_id}")

            return tag_id

        finally:
            conn.close()

    def get_emotional_tag(self, entity_id: int) -> Optional[Dict[str, Any]]:
        """Get emotional tag for an entity"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM emotional_tags WHERE entity_id = ?',
            (entity_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def search_by_emotion(
        self,
        emotion_filter: Dict[str, Any],
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search memories by emotional criteria

        Args:
            emotion_filter: {
                "valence_min": -1.0,
                "valence_max": 1.0,
                "arousal_min": 0.0,
                "arousal_max": 1.0,
                "primary_emotion": "joy",
                "min_salience": 0.5
            }
            limit: Maximum results

        Returns:
            List of matching entities with emotional tags
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query
        conditions = []
        params = []

        if "valence_min" in emotion_filter:
            conditions.append("et.valence >= ?")
            params.append(emotion_filter["valence_min"])

        if "valence_max" in emotion_filter:
            conditions.append("et.valence <= ?")
            params.append(emotion_filter["valence_max"])

        if "arousal_min" in emotion_filter:
            conditions.append("et.arousal >= ?")
            params.append(emotion_filter["arousal_min"])

        if "arousal_max" in emotion_filter:
            conditions.append("et.arousal <= ?")
            params.append(emotion_filter["arousal_max"])

        if "primary_emotion" in emotion_filter:
            conditions.append("et.primary_emotion = ?")
            params.append(emotion_filter["primary_emotion"])

        if "min_salience" in emotion_filter:
            conditions.append("et.salience_score >= ?")
            params.append(emotion_filter["min_salience"])

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f'''
            SELECT
                e.*,
                et.valence,
                et.arousal,
                et.dominance,
                et.primary_emotion,
                et.salience_score,
                et.current_strength
            FROM entities e
            JOIN emotional_tags et ON e.id = et.entity_id
            WHERE {where_clause}
            ORDER BY et.salience_score DESC, et.current_strength DESC
            LIMIT ?
        '''

        params.append(limit)
        cursor.execute(query, params)

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def update_salience(
        self,
        entity_id: int,
        salience_delta: float,
        reason: str
    ):
        """
        Update salience score for an entity

        Args:
            entity_id: Entity to update
            salience_delta: Change in salience (-1.0 to +1.0)
            reason: Why salience changed
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE emotional_tags
            SET
                salience_score = MAX(0.0, MIN(1.0, salience_score + ?)),
                updated_at = CURRENT_TIMESTAMP
            WHERE entity_id = ?
            ''',
            (salience_delta, entity_id)
        )

        conn.commit()
        conn.close()

        logger.info(f"Updated salience for entity {entity_id}: delta={salience_delta:.2f}, reason={reason}")

    def decay_memory_strength(
        self,
        entity_id: int,
        time_elapsed_hours: float
    ) -> float:
        """
        Apply forgetting curve decay to memory strength

        Uses Ebbinghaus forgetting curve: strength = e^(-kt)

        Args:
            entity_id: Entity to decay
            time_elapsed_hours: Hours since last access

        Returns:
            New strength value
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get current emotional tag
        cursor.execute(
            'SELECT decay_rate, current_strength, last_accessed FROM emotional_tags WHERE entity_id = ?',
            (entity_id,)
        )

        row = cursor.fetchone()
        if not row:
            conn.close()
            return 1.0

        decay_rate, current_strength, last_accessed = row

        # Calculate new strength: S = e^(-kt)
        # k = decay_rate, t = time_elapsed_hours
        decay_factor = exp(-decay_rate * time_elapsed_hours)
        new_strength = current_strength * decay_factor

        # Update strength
        cursor.execute(
            '''
            UPDATE emotional_tags
            SET
                current_strength = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE entity_id = ?
            ''',
            (new_strength, entity_id)
        )

        conn.commit()
        conn.close()

        logger.info(f"Applied decay to entity {entity_id}: {current_strength:.3f} → {new_strength:.3f}")

        return new_strength

    def boost_memory_strength(
        self,
        entity_id: int,
        boost_amount: float = 0.2
    ):
        """
        Boost memory strength (e.g., on retrieval - spacing effect)

        Args:
            entity_id: Entity to boost
            boost_amount: Strength increase (0.0-1.0)
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE emotional_tags
            SET
                current_strength = MIN(1.0, current_strength + ?),
                last_accessed = CURRENT_TIMESTAMP,
                access_count = access_count + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE entity_id = ?
            ''',
            (boost_amount, entity_id)
        )

        conn.commit()
        conn.close()

        logger.info(f"Boosted strength for entity {entity_id}: +{boost_amount:.2f}")

    def get_high_salience_memories(
        self,
        threshold: float = 0.7,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get memories with high salience scores"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT * FROM high_salience_memories
            WHERE salience_score >= ?
            LIMIT ?
            ''',
            (threshold, limit)
        )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def get_emotional_clusters(self) -> List[Dict[str, Any]]:
        """Get emotional memory clusters grouped by emotion"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM emotional_clusters')

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results
