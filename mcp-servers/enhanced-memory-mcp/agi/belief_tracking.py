"""
Belief State Debugging Framework
Stanford Research Implementation for Epistemic Flexibility

Implements:
- Probability tracking for agent beliefs
- Four-layer contextual instantiation analysis
- Belief revision history tracking
- Epistemic flexibility measurement
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("belief-tracking")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class BeliefTracker:
    """Tracks agent belief states with probability and evidence"""

    def __init__(self, agent_id: str = "default_agent"):
        self.agent_id = agent_id

    def record_belief(
        self,
        belief_statement: str,
        probability: float,
        belief_category: str = "fact",
        confidence: float = 0.5,
        supporting_evidence: Optional[List[Dict]] = None,
        contradicting_evidence: Optional[List[Dict]] = None,
        layer_context: Optional[Dict[str, str]] = None,
        session_id: Optional[str] = None
    ) -> int:
        """
        Record an agent's belief state with probability and evidence.

        Args:
            belief_statement: What is believed
            probability: Belief strength 0.0-1.0
            belief_category: "identity", "fact", "strategy", "goal"
            confidence: Confidence in probability estimate
            supporting_evidence: List of supporting evidence
            contradicting_evidence: List of contradicting evidence
            layer_context: Four-layer context dict
            session_id: Session identifier

        Returns:
            belief_id
        """
        # Calculate evidence balance
        support_weight = sum(e.get('weight', 1.0) for e in (supporting_evidence or []))
        contradict_weight = sum(e.get('weight', 1.0) for e in (contradicting_evidence or []))
        evidence_balance = support_weight - contradict_weight

        # Extract layer context
        layers = layer_context or {}

        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO belief_states (
                agent_id, session_id, belief_statement, belief_category,
                probability, confidence, supporting_evidence, contradicting_evidence,
                evidence_balance, layer_1_instruction, layer_2_conversation,
                layer_3_observations, layer_4_constraints
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.agent_id, session_id, belief_statement, belief_category,
            probability, confidence,
            json.dumps(supporting_evidence or []),
            json.dumps(contradicting_evidence or []),
            evidence_balance,
            layers.get('instruction', ''),
            layers.get('conversation', ''),
            layers.get('observations', ''),
            layers.get('constraints', '')
        ))

        belief_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Recorded belief {belief_id}: '{belief_statement[:50]}...' (p={probability})")
        return belief_id

    def update_probability(
        self,
        belief_id: int,
        new_probability: float,
        revision_trigger: str,
        evidence_provided: str,
        reasoning: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update belief probability and record revision.

        Args:
            belief_id: Belief to update
            new_probability: New probability value
            revision_trigger: "new_evidence", "contradiction", "counterfactual"
            evidence_provided: Description of evidence
            reasoning: Agent's explanation
            session_id: Session identifier

        Returns:
            Revision details
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get current state
        cursor.execute('SELECT probability, revision_count FROM belief_states WHERE belief_id = ?', (belief_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {"error": "Belief not found"}

        old_probability = row['probability']
        probability_delta = new_probability - old_probability
        new_revision_count = row['revision_count'] + 1

        # Update belief state
        cursor.execute('''
            UPDATE belief_states SET
                probability = ?,
                previous_probability = ?,
                revision_count = ?,
                last_revised = ?,
                updated_at = ?
            WHERE belief_id = ?
        ''', (
            new_probability, old_probability, new_revision_count,
            datetime.now().isoformat(), datetime.now().isoformat(), belief_id
        ))

        # Record revision history
        cursor.execute('''
            INSERT INTO belief_revisions (
                belief_id, agent_id, old_probability, new_probability,
                probability_delta, revision_trigger, evidence_provided,
                reasoning, session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            belief_id, self.agent_id, old_probability, new_probability,
            probability_delta, revision_trigger, evidence_provided,
            reasoning, session_id
        ))

        revision_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Belief {belief_id} revised: {old_probability:.2f} -> {new_probability:.2f} ({revision_trigger})")

        return {
            "belief_id": belief_id,
            "revision_id": revision_id,
            "old_probability": old_probability,
            "new_probability": new_probability,
            "probability_delta": probability_delta,
            "revision_trigger": revision_trigger,
            "revision_count": new_revision_count
        }

    def get_beliefs(
        self,
        category: Optional[str] = None,
        min_probability: float = 0.0,
        include_evidence: bool = True,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieve agent's current belief states.
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = '''
            SELECT * FROM belief_states
            WHERE agent_id = ? AND probability >= ?
        '''
        params = [self.agent_id, min_probability]

        if category:
            query += ' AND belief_category = ?'
            params.append(category)

        query += ' ORDER BY probability DESC, updated_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        beliefs = []
        for row in rows:
            belief = dict(row)
            if include_evidence:
                belief['supporting_evidence'] = json.loads(belief.get('supporting_evidence') or '[]')
                belief['contradicting_evidence'] = json.loads(belief.get('contradicting_evidence') or '[]')
            else:
                del belief['supporting_evidence']
                del belief['contradicting_evidence']
            beliefs.append(belief)

        return beliefs

    def get_revision_history(
        self,
        belief_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get revision history for a belief."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM belief_revisions
            WHERE belief_id = ?
            ORDER BY revised_at DESC
            LIMIT ?
        ''', (belief_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def analyze_rigidity(
        self,
        belief_id: Optional[int] = None,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze belief rigidity/flexibility.

        Returns rigidity metrics:
        - Average revision magnitude
        - Revision frequency
        - Evidence sensitivity
        - Flexibility score (0.0=rigid, 1.0=flexible)
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(hours=time_window_hours)

        if belief_id:
            # Single belief analysis
            cursor.execute('''
                SELECT
                    COUNT(*) as revision_count,
                    AVG(ABS(probability_delta)) as avg_revision_magnitude,
                    MAX(ABS(probability_delta)) as max_revision
                FROM belief_revisions
                WHERE belief_id = ? AND revised_at >= ?
            ''', (belief_id, cutoff.isoformat()))
        else:
            # All beliefs for agent
            cursor.execute('''
                SELECT
                    COUNT(*) as revision_count,
                    AVG(ABS(probability_delta)) as avg_revision_magnitude,
                    MAX(ABS(probability_delta)) as max_revision
                FROM belief_revisions
                WHERE agent_id = ? AND revised_at >= ?
            ''', (self.agent_id, cutoff.isoformat()))

        row = cursor.fetchone()

        # Get total beliefs
        if belief_id:
            cursor.execute('SELECT 1 FROM belief_states WHERE belief_id = ?', (belief_id,))
            total_beliefs = 1 if cursor.fetchone() else 0
        else:
            cursor.execute('SELECT COUNT(*) FROM belief_states WHERE agent_id = ?', (self.agent_id,))
            total_beliefs = cursor.fetchone()[0]

        conn.close()

        revision_count = row[0] or 0
        avg_magnitude = row[1] or 0.0
        max_revision = row[2] or 0.0

        # Calculate flexibility score
        # Higher revision frequency + larger magnitude = more flexible
        revision_rate = revision_count / max(total_beliefs, 1) if total_beliefs > 0 else 0
        flexibility_score = min(1.0, (avg_magnitude * 2 + revision_rate * 0.5))

        return {
            "agent_id": self.agent_id,
            "belief_id": belief_id,
            "time_window_hours": time_window_hours,
            "total_beliefs": total_beliefs,
            "revision_count": revision_count,
            "avg_revision_magnitude": avg_magnitude,
            "max_revision": max_revision,
            "revision_rate": revision_rate,
            "flexibility_score": flexibility_score,
            "rigidity_score": 1.0 - flexibility_score
        }

    def find_by_statement(
        self,
        search_term: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find beliefs matching a search term."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM belief_states
            WHERE agent_id = ? AND belief_statement LIKE ?
            ORDER BY probability DESC
            LIMIT ?
        ''', (self.agent_id, f'%{search_term}%', limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]


def get_all_agent_beliefs(limit_per_agent: int = 20) -> Dict[str, List[Dict]]:
    """Get beliefs for all agents."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT DISTINCT agent_id FROM belief_states')
    agents = [row[0] for row in cursor.fetchall()]
    conn.close()

    result = {}
    for agent_id in agents:
        tracker = BeliefTracker(agent_id)
        result[agent_id] = tracker.get_beliefs(limit=limit_per_agent)

    return result


def get_epistemic_flexibility_summary() -> Dict[str, Any]:
    """Get epistemic flexibility summary for all agents."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()

    # Get all agents
    cursor.execute('SELECT DISTINCT agent_id FROM belief_states')
    agents = [row[0] for row in cursor.fetchall()]

    # Overall stats
    cursor.execute('SELECT COUNT(*) FROM belief_states')
    total_beliefs = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM belief_revisions')
    total_revisions = cursor.fetchone()[0]

    conn.close()

    # Per-agent flexibility
    agent_scores = {}
    for agent_id in agents:
        tracker = BeliefTracker(agent_id)
        analysis = tracker.analyze_rigidity()
        agent_scores[agent_id] = analysis['flexibility_score']

    avg_flexibility = sum(agent_scores.values()) / len(agent_scores) if agent_scores else 0.0

    return {
        "total_beliefs": total_beliefs,
        "total_revisions": total_revisions,
        "agents_tracked": len(agents),
        "agent_flexibility_scores": agent_scores,
        "average_flexibility": avg_flexibility,
        "most_flexible": max(agent_scores.items(), key=lambda x: x[1])[0] if agent_scores else None,
        "most_rigid": min(agent_scores.items(), key=lambda x: x[1])[0] if agent_scores else None
    }
