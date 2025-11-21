"""
Associative Network Module

Implements associative memory and activation spreading for AGI.

Key Features:
- Associative links between memories
- Activation spreading (neural network-like)
- Context-dependent retrieval
- Attention mechanisms
- Forgetting curves with spaced repetition
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict
from math import exp

logger = logging.getLogger("associative-network")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class AssociativeNetwork:
    """Manages associative links and activation spreading"""

    def __init__(self):
        pass

    def create_association(
        self,
        entity_a_id: int,
        entity_b_id: int,
        association_type: str = "semantic",
        association_strength: float = 0.5,
        bidirectional: bool = True,
        context_conditions: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Create associative link between two entities

        Args:
            entity_a_id: First entity
            entity_b_id: Second entity
            association_type: semantic, temporal, causal, emotional, spatial
            association_strength: 0.0 to 1.0
            bidirectional: Can activate in both directions?
            context_conditions: Optional context requirements

        Returns:
            association_id
        """
        # Ensure a < b for uniqueness
        if entity_a_id > entity_b_id:
            entity_a_id, entity_b_id = entity_b_id, entity_a_id

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''
                INSERT INTO memory_associations (
                    entity_a_id, entity_b_id,
                    association_type, association_strength,
                    bidirectional, context_conditions,
                    discovered_method
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    entity_a_id, entity_b_id,
                    association_type, association_strength,
                    bidirectional,
                    json.dumps(context_conditions or {}),
                    "manual"
                )
            )

            association_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Created association: {entity_a_id} ↔ {entity_b_id} "
                       f"(type: {association_type}, strength: {association_strength:.2f})")

            return association_id

        except sqlite3.IntegrityError:
            # Association already exists, update it
            cursor.execute(
                '''
                UPDATE memory_associations
                SET
                    association_strength = (association_strength + ?) / 2,
                    co_activation_count = co_activation_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE entity_a_id = ? AND entity_b_id = ?
                RETURNING association_id
                ''',
                (association_strength, entity_a_id, entity_b_id)
            )

            row = cursor.fetchone()
            association_id = row[0] if row else None
            conn.commit()

            logger.info(f"Strengthened existing association: {entity_a_id} ↔ {entity_b_id}")

            return association_id

        finally:
            conn.close()

    def get_associations(
        self,
        entity_id: int,
        min_strength: float = 0.0,
        association_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all associations for an entity

        Args:
            entity_id: Entity to get associations for
            min_strength: Minimum association strength
            association_type: Optional type filter

        Returns:
            List of associations
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query (entity can be in either position)
        conditions = ["(ma.entity_a_id = ? OR ma.entity_b_id = ?)", "ma.association_strength >= ?"]
        params = [entity_id, entity_id, min_strength]

        if association_type:
            conditions.append("ma.association_type = ?")
            params.append(association_type)

        where_clause = " AND ".join(conditions)

        query = f'''
            SELECT
                ma.*,
                CASE
                    WHEN ma.entity_a_id = ? THEN ma.entity_b_id
                    ELSE ma.entity_a_id
                END as associated_entity_id,
                e.name as associated_entity_name,
                e.entity_type as associated_entity_type
            FROM memory_associations ma
            JOIN entities e ON (
                CASE
                    WHEN ma.entity_a_id = ? THEN ma.entity_b_id
                    ELSE ma.entity_a_id
                END = e.id
            )
            WHERE {where_clause}
            ORDER BY ma.association_strength DESC
        '''

        cursor.execute(query, [entity_id, entity_id] + params)

        results = []
        for row in cursor.fetchall():
            assoc = dict(row)
            # Parse JSON fields
            if assoc.get('context_conditions'):
                try:
                    assoc['context_conditions'] = json.loads(assoc['context_conditions'])
                except:
                    pass
            results.append(assoc)

        conn.close()

        return results

    def spread_activation(
        self,
        source_entity_id: int,
        initial_activation: float = 1.0,
        max_hops: int = 3,
        activation_threshold: float = 0.3,
        context_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Spread activation from source entity through associative network

        Implements spreading activation algorithm similar to neural networks.

        Args:
            source_entity_id: Starting entity
            initial_activation: Starting activation level (0.0-1.0)
            max_hops: Maximum distance to spread
            activation_threshold: Minimum activation to continue spreading
            context_id: Optional context for context-dependent associations

        Returns:
            List of activated entities with activation levels
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Track activated entities
        activations = {source_entity_id: initial_activation}
        visited = set([source_entity_id])
        activation_log = []

        # BFS-like spreading
        current_level = [(source_entity_id, initial_activation, 0)]

        while current_level:
            next_level = []

            for entity_id, activation, distance in current_level:
                if distance >= max_hops:
                    continue

                # Get associations
                cursor.execute(
                    '''
                    SELECT
                        CASE
                            WHEN entity_a_id = ? THEN entity_b_id
                            ELSE entity_a_id
                        END as neighbor_id,
                        association_id,
                        association_strength,
                        spread_decay,
                        activation_threshold as assoc_threshold,
                        context_dependent,
                        context_conditions
                    FROM memory_associations
                    WHERE (entity_a_id = ? OR entity_b_id = ?)
                        AND association_strength >= ?
                    ''',
                    (entity_id, entity_id, entity_id, activation_threshold)
                )

                neighbors = cursor.fetchall()

                for neighbor_id, assoc_id, strength, decay, assoc_threshold, context_dep, context_cond in neighbors:
                    if neighbor_id in visited:
                        continue

                    # Check context dependency
                    if context_dep and context_id:
                        # TODO: Check context conditions match
                        pass

                    # Calculate activation spreading
                    # New activation = current_activation * strength * (1 - decay)
                    spread_activation = activation * strength * (1.0 - decay)

                    if spread_activation >= assoc_threshold:
                        # Accumulate activation
                        if neighbor_id in activations:
                            activations[neighbor_id] += spread_activation
                        else:
                            activations[neighbor_id] = spread_activation

                        # Log spreading event
                        activation_log.append({
                            "source": entity_id,
                            "target": neighbor_id,
                            "association_id": assoc_id,
                            "initial_activation": activation,
                            "final_activation": spread_activation,
                            "distance": distance + 1
                        })

                        # Add to next level
                        next_level.append((neighbor_id, spread_activation, distance + 1))
                        visited.add(neighbor_id)

            current_level = next_level

        # Store spreading log
        for log_entry in activation_log:
            cursor.execute(
                '''
                INSERT INTO activation_spreading_log (
                    source_entity_id, activated_entity_id, association_id,
                    initial_activation, final_activation, spread_distance,
                    context_id, spreading_triggered_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    log_entry["source"], log_entry["target"], log_entry["association_id"],
                    log_entry["initial_activation"], log_entry["final_activation"],
                    log_entry["distance"], context_id, "manual"
                )
            )

        conn.commit()
        conn.close()

        # Get entity names
        activated_entities = []
        for entity_id, activation_level in activations.items():
            if entity_id == source_entity_id:
                continue  # Skip source

            activated_entities.append({
                "entity_id": entity_id,
                "activation_level": activation_level
            })

        # Sort by activation level
        activated_entities.sort(key=lambda x: x["activation_level"], reverse=True)

        logger.info(f"Activation spread from {source_entity_id}: {len(activated_entities)} entities activated")

        return activated_entities

    def reinforce_association(
        self,
        entity_a_id: int,
        entity_b_id: int,
        reinforcement: float = 0.1
    ):
        """
        Reinforce an association (e.g., when co-activated)

        Args:
            entity_a_id: First entity
            entity_b_id: Second entity
            reinforcement: Strength increase (0.0-1.0)
        """
        # Ensure a < b
        if entity_a_id > entity_b_id:
            entity_a_id, entity_b_id = entity_b_id, entity_a_id

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            '''
            UPDATE memory_associations
            SET
                association_strength = MIN(1.0, association_strength + ?),
                co_activation_count = co_activation_count + 1,
                last_co_activation = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE entity_a_id = ? AND entity_b_id = ?
            ''',
            (reinforcement, entity_a_id, entity_b_id)
        )

        conn.commit()
        conn.close()

        logger.info(f"Reinforced association: {entity_a_id} ↔ {entity_b_id} (+{reinforcement:.2f})")

    def get_strong_associations(
        self,
        threshold: float = 0.7,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get strong associations"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            '''
            SELECT * FROM strong_associations
            WHERE association_strength >= ?
            LIMIT ?
            ''',
            (threshold, limit)
        )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results


class AttentionMechanism:
    """Manages attention weights for selective retrieval"""

    def __init__(self):
        pass

    def set_attention(
        self,
        entity_id: int,
        relevance_score: float,
        context_id: Optional[int] = None,
        recency_weight: float = 0.3,
        frequency_weight: float = 0.3,
        emotional_weight: float = 0.4
    ):
        """
        Set attention weights for an entity

        Args:
            entity_id: Entity to attend to
            relevance_score: Current relevance (0.0-1.0)
            context_id: Optional context (None = global)
            recency_weight: Weight for recent access
            frequency_weight: Weight for frequent access
            emotional_weight: Weight for emotional salience
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Calculate current attention
        current_attention = (
            recency_weight * 0.5 +  # TODO: Calculate from actual recency
            frequency_weight * 0.5 +  # TODO: Calculate from access count
            emotional_weight * relevance_score
        )

        try:
            cursor.execute(
                '''
                INSERT INTO attention_weights (
                    entity_id, relevance_score,
                    recency_weight, frequency_weight, emotional_weight,
                    current_attention, context_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    entity_id, relevance_score,
                    recency_weight, frequency_weight, emotional_weight,
                    current_attention, context_id
                )
            )
        except sqlite3.IntegrityError:
            cursor.execute(
                '''
                UPDATE attention_weights
                SET
                    relevance_score = ?,
                    recency_weight = ?,
                    frequency_weight = ?,
                    emotional_weight = ?,
                    current_attention = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE entity_id = ? AND context_id IS ?
                ''',
                (
                    relevance_score, recency_weight, frequency_weight, emotional_weight,
                    current_attention, entity_id, context_id
                )
            )

        conn.commit()
        conn.close()

        logger.info(f"Set attention for entity {entity_id}: {current_attention:.2f}")

    def get_attended_memories(
        self,
        threshold: float = 0.3,
        context_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get currently attended memories"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if context_id is not None:
            query = '''
                SELECT * FROM attended_memories
                WHERE current_attention >= ?
                    AND context_name = (SELECT context_name FROM retrieval_contexts WHERE context_id = ?)
                LIMIT ?
            '''
            params = (threshold, context_id, limit)
        else:
            query = '''
                SELECT * FROM attended_memories
                WHERE current_attention >= ?
                LIMIT ?
            '''
            params = (threshold, limit)

        cursor.execute(query, params)

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results


class ForgettingCurve:
    """Manages forgetting curves and spaced repetition"""

    def __init__(self):
        pass

    def initialize_curve(
        self,
        entity_id: int,
        initial_strength: float = 1.0,
        decay_constant: float = 0.5
    ):
        """Initialize forgetting curve for an entity"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''
                INSERT INTO forgetting_curves (
                    entity_id, initial_strength,
                    current_strength, decay_constant,
                    last_strength_check
                ) VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    entity_id, initial_strength,
                    initial_strength, decay_constant,
                    datetime.now().isoformat()
                )
            )

            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Already exists

        conn.close()

    def apply_forgetting(
        self,
        entity_id: int,
        time_elapsed_hours: float
    ) -> float:
        """
        Apply Ebbinghaus forgetting curve

        strength(t) = e^(-k*t)

        Args:
            entity_id: Entity to apply forgetting to
            time_elapsed_hours: Hours since last check

        Returns:
            New strength
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            'SELECT current_strength, decay_constant FROM forgetting_curves WHERE entity_id = ?',
            (entity_id,)
        )

        row = cursor.fetchone()
        if not row:
            conn.close()
            return 1.0

        current_strength, decay_constant = row

        # Calculate new strength: S = e^(-kt)
        new_strength = exp(-decay_constant * time_elapsed_hours)

        # Update
        cursor.execute(
            '''
            UPDATE forgetting_curves
            SET
                current_strength = ?,
                last_strength_check = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE entity_id = ?
            ''',
            (new_strength, datetime.now().isoformat(), entity_id)
        )

        conn.commit()
        conn.close()

        return new_strength

    def get_memories_needing_review(
        self,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get memories that need review (weak or due for spaced repetition)"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM memories_needing_review LIMIT ?',
            (limit,)
        )

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results
