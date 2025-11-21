"""
Temporal Reasoning Module

Provides causal understanding and temporal chain management for AGI memory.

Key Features:
- Causal link discovery and tracking
- Temporal chain management
- Event sequence pattern detection
- Predictive reasoning based on causal history
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger("temporal-reasoning")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class TemporalReasoning:
    """Manages temporal chains and causal relationships"""

    def __init__(self):
        pass

    def create_causal_link(
        self,
        cause_entity_id: int,
        effect_entity_id: int,
        relationship_type: str = "direct",
        strength: float = 0.5,
        typical_delay_seconds: Optional[int] = None,
        context_conditions: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Create a causal link between two entities

        Args:
            cause_entity_id: Entity that causes the effect
            effect_entity_id: Entity that is the effect
            relationship_type: "direct", "indirect", "contributory", "preventive"
            strength: 0.0 (weak) to 1.0 (strong)
            typical_delay_seconds: Average time between cause and effect
            context_conditions: Conditions under which this link holds

        Returns:
            link_id
        """
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            cursor.execute(
                '''
                INSERT INTO causal_links (
                    cause_entity_id, effect_entity_id,
                    relationship_type, strength,
                    typical_delay_seconds, context_conditions,
                    first_observed, last_observed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    cause_entity_id, effect_entity_id,
                    relationship_type, strength,
                    typical_delay_seconds,
                    json.dumps(context_conditions or {}),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                )
            )

            link_id = cursor.lastrowid
            conn.commit()

            logger.info(f"Created causal link: {cause_entity_id} → {effect_entity_id} (strength: {strength})")

            return link_id

        except sqlite3.IntegrityError:
            # Link already exists, update it instead
            cursor.execute(
                '''
                UPDATE causal_links
                SET
                    evidence_count = evidence_count + 1,
                    strength = (strength + ?) / 2,  -- Running average
                    last_observed = ?
                WHERE cause_entity_id = ? AND effect_entity_id = ?
                RETURNING link_id
                ''',
                (strength, datetime.now().isoformat(), cause_entity_id, effect_entity_id)
            )

            row = cursor.fetchone()
            link_id = row[0] if row else None
            conn.commit()

            logger.info(f"Updated existing causal link: {cause_entity_id} → {effect_entity_id}")

            return link_id

        finally:
            conn.close()

    def get_causal_chain(
        self,
        entity_id: int,
        direction: str = "forward",
        depth: int = 5,
        min_strength: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Get causal chain from an entity

        Args:
            entity_id: Starting entity
            direction: "forward" (effects) or "backward" (causes)
            depth: How many levels deep to traverse
            min_strength: Minimum link strength to follow

        Returns:
            List of entities in causal chain with link metadata
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        chain = []
        visited = set()
        current_level = [(entity_id, 0, None)]  # (entity_id, level, link_info)

        while current_level and len(current_level) > 0:
            next_level = []

            for current_id, level, link_info in current_level:
                if current_id in visited or level >= depth:
                    continue

                visited.add(current_id)

                # Add to chain
                if link_info:
                    chain.append({
                        "entity_id": current_id,
                        "level": level,
                        "link": link_info
                    })

                # Get next links
                if direction == "forward":
                    cursor.execute(
                        '''
                        SELECT
                            cl.*,
                            e.name as effect_name,
                            e.entity_type as effect_type
                        FROM causal_links cl
                        JOIN entities e ON cl.effect_entity_id = e.id
                        WHERE cl.cause_entity_id = ?
                        AND cl.strength >= ?
                        ORDER BY cl.strength DESC
                        ''',
                        (current_id, min_strength)
                    )
                else:  # backward
                    cursor.execute(
                        '''
                        SELECT
                            cl.*,
                            e.name as cause_name,
                            e.entity_type as cause_type
                        FROM causal_links cl
                        JOIN entities e ON cl.cause_entity_id = e.id
                        WHERE cl.effect_entity_id = ?
                        AND cl.strength >= ?
                        ORDER BY cl.strength DESC
                        ''',
                        (current_id, min_strength)
                    )

                rows = cursor.fetchall()

                for row in rows:
                    link = dict(row)

                    # Parse JSON fields
                    if link.get('context_conditions'):
                        try:
                            link['context_conditions'] = json.loads(link['context_conditions'])
                        except:
                            pass

                    next_id = link['effect_entity_id'] if direction == "forward" else link['cause_entity_id']
                    next_level.append((next_id, level + 1, link))

            current_level = next_level

        conn.close()

        return chain

    def predict_outcome(
        self,
        action_entity_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict likely outcomes of an action based on causal history

        Args:
            action_entity_id: Entity representing the action
            context: Current context conditions

        Returns:
            {
                "likely_outcomes": List[Dict],
                "confidence": float,
                "reasoning": str,
                "similar_cases": int
            }
        """
        # Get forward causal chain
        chain = self.get_causal_chain(
            action_entity_id,
            direction="forward",
            depth=3,
            min_strength=0.4
        )

        if not chain:
            return {
                "likely_outcomes": [],
                "confidence": 0.0,
                "reasoning": "No historical causal data for this action",
                "similar_cases": 0
            }

        # Aggregate outcomes by effect with weighted probabilities
        outcomes = {}
        total_strength = 0

        for item in chain:
            link = item['link']
            effect_id = link['effect_entity_id']
            strength = link['strength']
            evidence = link['evidence_count']

            # Weight by both strength and evidence count
            weight = strength * min(evidence / 10, 1.0)  # Cap evidence bonus at 10
            total_strength += weight

            if effect_id not in outcomes:
                outcomes[effect_id] = {
                    "entity_id": effect_id,
                    "entity_name": link.get('effect_name', 'unknown'),
                    "entity_type": link.get('effect_type', 'unknown'),
                    "probability": 0.0,
                    "typical_delay_seconds": link.get('typical_delay_seconds'),
                    "relationship_type": link['relationship_type'],
                    "evidence_count": evidence
                }

            outcomes[effect_id]["probability"] += weight

        # Normalize probabilities
        if total_strength > 0:
            for outcome in outcomes.values():
                outcome["probability"] /= total_strength

        # Sort by probability
        sorted_outcomes = sorted(
            outcomes.values(),
            key=lambda x: x["probability"],
            reverse=True
        )

        # Calculate overall confidence
        avg_strength = total_strength / len(chain) if chain else 0
        confidence = min(avg_strength * (1 + min(len(chain) / 10, 0.5)), 1.0)

        return {
            "likely_outcomes": sorted_outcomes[:5],  # Top 5
            "confidence": confidence,
            "reasoning": f"Based on {len(chain)} historical causal links",
            "similar_cases": len(chain)
        }

    def detect_causal_pattern(
        self,
        entity_ids: List[int],
        time_window_hours: int = 24
    ) -> Optional[Dict[str, Any]]:
        """
        Detect if a sequence of entities represents a causal pattern

        Args:
            entity_ids: Ordered list of entity IDs
            time_window_hours: Time window to look for patterns

        Returns:
            Pattern info if found, None otherwise
        """
        if len(entity_ids) < 2:
            return None

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if consecutive pairs have causal links
        pattern_strength = 0.0
        links_found = 0

        for i in range(len(entity_ids) - 1):
            cursor.execute(
                '''
                SELECT strength, evidence_count
                FROM causal_links
                WHERE cause_entity_id = ? AND effect_entity_id = ?
                ''',
                (entity_ids[i], entity_ids[i + 1])
            )

            row = cursor.fetchone()
            if row:
                pattern_strength += row[0]  # strength
                links_found += 1

        conn.close()

        if links_found == 0:
            return None

        avg_strength = pattern_strength / (len(entity_ids) - 1)

        return {
            "pattern_type": "causal_sequence",
            "entity_ids": entity_ids,
            "links_found": links_found,
            "coverage": links_found / (len(entity_ids) - 1),
            "avg_strength": avg_strength,
            "confidence": avg_strength * (links_found / (len(entity_ids) - 1))
        }

    def create_temporal_chain(
        self,
        entity_ids: List[int],
        chain_type: str,
        chain_name: Optional[str] = None,
        description: Optional[str] = None,
        confidence: float = 0.5
    ) -> str:
        """
        Create a temporal chain from a sequence of entities

        Args:
            entity_ids: Ordered list of entity IDs in the chain
            chain_type: "causal", "sequential", "conditional", "cyclic"
            chain_name: Optional name for the chain
            description: Optional description
            confidence: Confidence in this chain (0.0-1.0)

        Returns:
            chain_id
        """
        chain_id = str(uuid4())

        # Calculate chain strength from links
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        total_strength = 0.0
        link_count = 0

        for i in range(len(entity_ids) - 1):
            cursor.execute(
                'SELECT strength FROM causal_links WHERE cause_entity_id = ? AND effect_entity_id = ?',
                (entity_ids[i], entity_ids[i + 1])
            )
            row = cursor.fetchone()
            if row:
                total_strength += row[0]
                link_count += 1

        avg_strength = total_strength / link_count if link_count > 0 else 0.5

        cursor.execute(
            '''
            INSERT INTO temporal_chains (
                chain_id, chain_type, chain_name, description,
                entities, confidence, strength,
                discovered_at, discovery_method, evidence_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                chain_id, chain_type, chain_name, description,
                json.dumps(entity_ids), confidence, avg_strength,
                datetime.now().isoformat(), "manual", 1
            )
        )

        conn.commit()
        conn.close()

        logger.info(f"Created temporal chain: {chain_id} ({chain_type}, {len(entity_ids)} entities)")

        return chain_id

    def get_temporal_chain(self, chain_id: str) -> Optional[Dict[str, Any]]:
        """Get temporal chain details"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM temporal_chains WHERE chain_id = ?',
            (chain_id,)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        chain = dict(row)

        # Parse JSON fields
        if chain.get('entities'):
            try:
                chain['entities'] = json.loads(chain['entities'])
            except:
                pass

        if chain.get('typical_delays'):
            try:
                chain['typical_delays'] = json.loads(chain['typical_delays'])
            except:
                pass

        if chain.get('metadata'):
            try:
                chain['metadata'] = json.loads(chain['metadata'])
            except:
                pass

        return chain
