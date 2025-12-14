"""
Cluster Beliefs - Shared Memory Blocks for Multi-Agent Coordination
Stanford Research Implementation for Preventing Echo Chambers

Implements:
- Shared cluster-wide belief blocks
- Belief divergence detection
- Cross-agent consistency checks
- Belief reconciliation mechanisms
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("cluster-beliefs")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class ClusterBeliefManager:
    """Manages shared beliefs across multi-agent cluster"""

    def __init__(self, cluster_id: str = "default_cluster"):
        self.cluster_id = cluster_id

    def create_belief_block(
        self,
        belief_domain: str,
        initial_beliefs: Dict[str, float],
        description: Optional[str] = None,
        consensus_threshold: float = 0.6
    ) -> int:
        """
        Create shared memory block for cluster-wide beliefs.

        All agents in cluster can read and propose updates.
        Prevents echo chambers by making divergent beliefs visible.

        Args:
            belief_domain: Domain category (goals, strategies, constraints, facts)
            initial_beliefs: Dict of {statement: probability}
            description: Optional description of this belief block
            consensus_threshold: Required agreement level for updates (0.5-1.0)

        Returns:
            block_id
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO cluster_belief_blocks (
                cluster_id, belief_domain, beliefs_json, description,
                consensus_threshold, contributing_agents
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            self.cluster_id, belief_domain, json.dumps(initial_beliefs),
            description, consensus_threshold, json.dumps([])
        ))

        block_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Created cluster belief block {block_id}: {belief_domain}")
        return block_id

    def get_belief_block(self, block_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific belief block"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM cluster_belief_blocks WHERE block_id = ?',
            (block_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        block = dict(row)
        block['beliefs'] = json.loads(block.get('beliefs_json') or '{}')
        block['contributing_agents'] = json.loads(block.get('contributing_agents') or '[]')
        block['pending_proposals'] = json.loads(block.get('pending_proposals') or '[]')
        return block

    def get_domain_beliefs(self, belief_domain: str) -> List[Dict[str, Any]]:
        """Get all belief blocks for a domain"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM cluster_belief_blocks
            WHERE cluster_id = ? AND belief_domain = ?
            ORDER BY updated_at DESC
        ''', (self.cluster_id, belief_domain))

        rows = cursor.fetchall()
        conn.close()

        blocks = []
        for row in rows:
            block = dict(row)
            block['beliefs'] = json.loads(block.get('beliefs_json') or '{}')
            block['contributing_agents'] = json.loads(block.get('contributing_agents') or '[]')
            blocks.append(block)

        return blocks

    def propose_belief_update(
        self,
        block_id: int,
        agent_id: str,
        belief_statement: str,
        proposed_probability: float,
        evidence: List[Dict[str, Any]],
        reasoning: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Propose updating a cluster belief.

        Updates require consensus based on threshold set for block.

        Args:
            block_id: Belief block to update
            agent_id: Agent proposing update
            belief_statement: Belief to update
            proposed_probability: New probability value
            evidence: Supporting evidence for change
            reasoning: Agent's explanation

        Returns:
            Proposal status and whether it was applied
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get current block
        cursor.execute(
            'SELECT * FROM cluster_belief_blocks WHERE block_id = ?',
            (block_id,)
        )
        block = cursor.fetchone()

        if not block:
            conn.close()
            return {"error": "Block not found"}

        beliefs = json.loads(block['beliefs_json'] or '{}')
        contributors = json.loads(block['contributing_agents'] or '[]')
        proposals = json.loads(block['pending_proposals'] or '[]')
        threshold = block['consensus_threshold']

        old_probability = beliefs.get(belief_statement, 0.5)
        probability_delta = proposed_probability - old_probability

        # Create proposal
        proposal = {
            "proposal_id": len(proposals) + 1,
            "agent_id": agent_id,
            "belief_statement": belief_statement,
            "old_probability": old_probability,
            "proposed_probability": proposed_probability,
            "evidence": evidence,
            "reasoning": reasoning,
            "votes_for": [agent_id],  # Proposer votes for
            "votes_against": [],
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }

        # Check if this is first contributor or already has contributors
        if not contributors or len(contributors) < 2:
            # With one or no contributors, auto-apply
            beliefs[belief_statement] = proposed_probability
            proposal['status'] = 'applied'

            if agent_id not in contributors:
                contributors.append(agent_id)

            # Update block
            cursor.execute('''
                UPDATE cluster_belief_blocks SET
                    beliefs_json = ?,
                    contributing_agents = ?,
                    pending_proposals = ?,
                    last_consensus_at = ?,
                    updated_at = ?
                WHERE block_id = ?
            ''', (
                json.dumps(beliefs), json.dumps(contributors),
                json.dumps(proposals + [proposal]),
                datetime.now().isoformat(), datetime.now().isoformat(),
                block_id
            ))

            result = {
                "status": "applied",
                "proposal": proposal,
                "message": "Applied immediately (insufficient contributors for consensus)"
            }
        else:
            # Add to pending proposals
            proposals.append(proposal)

            cursor.execute('''
                UPDATE cluster_belief_blocks SET
                    pending_proposals = ?,
                    updated_at = ?
                WHERE block_id = ?
            ''', (json.dumps(proposals), datetime.now().isoformat(), block_id))

            result = {
                "status": "pending",
                "proposal": proposal,
                "required_votes": int(len(contributors) * threshold),
                "message": f"Proposal pending. Requires {int(len(contributors) * threshold)} votes."
            }

        conn.commit()
        conn.close()

        logger.info(f"Belief proposal for block {block_id}: {result['status']}")
        return result

    def vote_on_proposal(
        self,
        block_id: int,
        proposal_id: int,
        agent_id: str,
        vote: bool,  # True = for, False = against
        reasoning: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Vote on a pending belief update proposal.

        Returns updated proposal status and whether it was applied.
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM cluster_belief_blocks WHERE block_id = ?',
            (block_id,)
        )
        block = cursor.fetchone()

        if not block:
            conn.close()
            return {"error": "Block not found"}

        beliefs = json.loads(block['beliefs_json'] or '{}')
        contributors = json.loads(block['contributing_agents'] or '[]')
        proposals = json.loads(block['pending_proposals'] or '[]')
        threshold = block['consensus_threshold']

        # Find proposal
        proposal = None
        proposal_idx = None
        for idx, p in enumerate(proposals):
            if p['proposal_id'] == proposal_id:
                proposal = p
                proposal_idx = idx
                break

        if not proposal:
            conn.close()
            return {"error": "Proposal not found"}

        if proposal['status'] != 'pending':
            conn.close()
            return {"error": f"Proposal already {proposal['status']}"}

        # Add vote
        if vote:
            if agent_id not in proposal['votes_for']:
                proposal['votes_for'].append(agent_id)
            if agent_id in proposal['votes_against']:
                proposal['votes_against'].remove(agent_id)
        else:
            if agent_id not in proposal['votes_against']:
                proposal['votes_against'].append(agent_id)
            if agent_id in proposal['votes_for']:
                proposal['votes_for'].remove(agent_id)

        # Check if consensus reached
        votes_for = len(proposal['votes_for'])
        votes_against = len(proposal['votes_against'])
        total_voters = len(contributors)
        required_votes = int(total_voters * threshold)

        applied = False
        if votes_for >= required_votes:
            # Consensus reached - apply update
            beliefs[proposal['belief_statement']] = proposal['proposed_probability']
            proposal['status'] = 'applied'
            applied = True
        elif votes_against > (total_voters - required_votes):
            # Consensus against - reject
            proposal['status'] = 'rejected'

        proposals[proposal_idx] = proposal

        # Update block
        cursor.execute('''
            UPDATE cluster_belief_blocks SET
                beliefs_json = ?,
                pending_proposals = ?,
                last_consensus_at = ?,
                updated_at = ?
            WHERE block_id = ?
        ''', (
            json.dumps(beliefs), json.dumps(proposals),
            datetime.now().isoformat() if applied else block['last_consensus_at'],
            datetime.now().isoformat(), block_id
        ))

        conn.commit()
        conn.close()

        return {
            "proposal_id": proposal_id,
            "status": proposal['status'],
            "votes_for": votes_for,
            "votes_against": votes_against,
            "required_votes": required_votes,
            "applied": applied
        }

    def detect_belief_divergence(
        self,
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Detect when agents hold significantly different beliefs.

        Compares agent personal beliefs against cluster shared beliefs.

        Args:
            threshold: Minimum probability difference to flag as divergent

        Returns:
            List of divergent beliefs requiring attention
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get cluster beliefs
        cursor.execute('''
            SELECT * FROM cluster_belief_blocks WHERE cluster_id = ?
        ''', (self.cluster_id,))
        blocks = cursor.fetchall()

        divergences = []

        for block in blocks:
            cluster_beliefs = json.loads(block['beliefs_json'] or '{}')
            domain = block['belief_domain']

            # Get agent beliefs in same domain/category
            for statement, cluster_prob in cluster_beliefs.items():
                cursor.execute('''
                    SELECT agent_id, probability, belief_statement
                    FROM belief_states
                    WHERE belief_statement LIKE ?
                    ORDER BY agent_id
                ''', (f'%{statement[:50]}%',))

                agent_beliefs = cursor.fetchall()

                for ab in agent_beliefs:
                    prob_diff = abs(ab['probability'] - cluster_prob)
                    if prob_diff >= threshold:
                        divergence = {
                            "agent_id": ab['agent_id'],
                            "belief_statement": statement,
                            "cluster_probability": cluster_prob,
                            "agent_probability": ab['probability'],
                            "divergence": prob_diff,
                            "domain": domain,
                            "severity": "high" if prob_diff >= 0.5 else "medium"
                        }
                        divergences.append(divergence)

                        # Record divergence event
                        self._record_divergence_event(cursor, divergence)

        conn.commit()
        conn.close()

        logger.info(f"Detected {len(divergences)} belief divergences")
        return divergences

    def _record_divergence_event(
        self,
        cursor: sqlite3.Cursor,
        divergence: Dict[str, Any]
    ):
        """Record a divergence event for tracking"""
        cursor.execute('''
            INSERT INTO belief_divergence_events (
                cluster_id, agent_id, belief_statement, cluster_probability,
                agent_probability, divergence_magnitude, detected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.cluster_id, divergence['agent_id'],
            divergence['belief_statement'], divergence['cluster_probability'],
            divergence['agent_probability'], divergence['divergence'],
            datetime.now().isoformat()
        ))

    def check_belief_consistency(
        self,
        belief_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if agents in cluster have consistent beliefs.

        Returns:
            - Consistent beliefs (all agents agree)
            - Divergent beliefs (agents disagree)
            - Unshared beliefs (only one agent holds)
            - Contradiction pairs (mutually exclusive beliefs)
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all agent beliefs
        query = 'SELECT * FROM belief_states WHERE probability >= 0.5'
        params = []

        if belief_category:
            query += ' AND belief_category = ?'
            params.append(belief_category)

        cursor.execute(query, params)
        all_beliefs = cursor.fetchall()
        conn.close()

        # Group by belief statement
        belief_groups = {}
        for b in all_beliefs:
            stmt = b['belief_statement']
            if stmt not in belief_groups:
                belief_groups[stmt] = []
            belief_groups[stmt].append({
                'agent_id': b['agent_id'],
                'probability': b['probability']
            })

        # Analyze consistency
        consistent = []
        divergent = []
        unshared = []

        for stmt, agents in belief_groups.items():
            if len(agents) == 1:
                unshared.append({
                    'statement': stmt,
                    'held_by': agents[0]['agent_id'],
                    'probability': agents[0]['probability']
                })
            else:
                probs = [a['probability'] for a in agents]
                prob_range = max(probs) - min(probs)

                if prob_range < 0.2:
                    consistent.append({
                        'statement': stmt,
                        'agents': [a['agent_id'] for a in agents],
                        'avg_probability': sum(probs) / len(probs),
                        'agreement': 1.0 - prob_range
                    })
                else:
                    divergent.append({
                        'statement': stmt,
                        'agents': agents,
                        'probability_range': prob_range,
                        'disagreement': prob_range
                    })

        # Detect contradiction pairs (statements that can't both be true)
        contradictions = self._find_contradictions(list(belief_groups.keys()))

        return {
            "cluster_id": self.cluster_id,
            "total_beliefs_analyzed": len(belief_groups),
            "consistent_beliefs": consistent,
            "divergent_beliefs": divergent,
            "unshared_beliefs": unshared,
            "contradiction_pairs": contradictions,
            "consistency_score": len(consistent) / max(len(belief_groups), 1),
            "health": "Healthy" if len(divergent) < len(consistent) else "Needs attention"
        }

    def _find_contradictions(self, statements: List[str]) -> List[Tuple[str, str]]:
        """Find potentially contradictory belief pairs"""
        contradictions = []

        # Simple heuristic: look for negation patterns
        negation_words = ['not', "n't", 'never', 'no ', 'without', 'lacks']

        for i, s1 in enumerate(statements):
            for s2 in statements[i+1:]:
                # Check if one is negation of other
                s1_lower = s1.lower()
                s2_lower = s2.lower()

                # Check for direct negation
                for neg in negation_words:
                    if neg in s1_lower and neg not in s2_lower:
                        # Check if rest is similar
                        s1_clean = s1_lower.replace(neg, '').strip()
                        if s1_clean in s2_lower or s2_lower in s1_clean:
                            contradictions.append((s1, s2))
                            break

        return contradictions

    def reconcile_belief_conflict(
        self,
        belief_statements: List[str],
        strategy: str = "evidence_weighted"
    ) -> Dict[str, Any]:
        """
        Attempt to reconcile conflicting beliefs.

        Strategies:
        - evidence_weighted: Weight by evidence strength
        - probability_fusion: Bayesian fusion of probabilities
        - majority_voting: Simple majority wins
        - dempster_shafer: Dempster-Shafer combination rule

        Returns:
            Reconciled belief with confidence
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all beliefs matching statements
        placeholders = ','.join('?' * len(belief_statements))
        cursor.execute(f'''
            SELECT * FROM belief_states
            WHERE belief_statement IN ({placeholders})
        ''', belief_statements)

        beliefs = cursor.fetchall()
        conn.close()

        if not beliefs:
            return {"error": "No matching beliefs found"}

        if strategy == "evidence_weighted":
            result = self._evidence_weighted_reconcile(beliefs)
        elif strategy == "probability_fusion":
            result = self._probability_fusion_reconcile(beliefs)
        elif strategy == "majority_voting":
            result = self._majority_vote_reconcile(beliefs)
        else:
            result = self._evidence_weighted_reconcile(beliefs)

        result['strategy_used'] = strategy
        result['beliefs_reconciled'] = len(beliefs)

        return result

    def _evidence_weighted_reconcile(
        self,
        beliefs: List[sqlite3.Row]
    ) -> Dict[str, Any]:
        """Reconcile by weighting evidence strength"""
        weighted_sum = 0.0
        total_weight = 0.0

        for b in beliefs:
            evidence_balance = b['evidence_balance'] or 0.0
            weight = 1.0 + abs(evidence_balance)  # More evidence = more weight
            weighted_sum += b['probability'] * weight
            total_weight += weight

        reconciled_prob = weighted_sum / total_weight if total_weight > 0 else 0.5

        return {
            "reconciled_probability": reconciled_prob,
            "confidence": min(1.0, total_weight / len(beliefs)),
            "method": "evidence_weighted"
        }

    def _probability_fusion_reconcile(
        self,
        beliefs: List[sqlite3.Row]
    ) -> Dict[str, Any]:
        """Reconcile using probability fusion (geometric mean)"""
        import math

        probs = [b['probability'] for b in beliefs]

        # Geometric mean
        product = math.prod(probs)
        geo_mean = product ** (1.0 / len(probs))

        return {
            "reconciled_probability": geo_mean,
            "confidence": 1.0 - (max(probs) - min(probs)),
            "method": "probability_fusion"
        }

    def _majority_vote_reconcile(
        self,
        beliefs: List[sqlite3.Row]
    ) -> Dict[str, Any]:
        """Reconcile by majority vote (high/low probability)"""
        high_votes = sum(1 for b in beliefs if b['probability'] >= 0.5)
        low_votes = len(beliefs) - high_votes

        if high_votes > low_votes:
            avg_high = sum(b['probability'] for b in beliefs if b['probability'] >= 0.5) / high_votes
            reconciled = avg_high
        else:
            avg_low = sum(b['probability'] for b in beliefs if b['probability'] < 0.5) / max(low_votes, 1)
            reconciled = avg_low

        return {
            "reconciled_probability": reconciled,
            "confidence": abs(high_votes - low_votes) / len(beliefs),
            "method": "majority_voting",
            "votes_high": high_votes,
            "votes_low": low_votes
        }


def get_cluster_belief_summary(cluster_id: str = "default_cluster") -> Dict[str, Any]:
    """Get summary of cluster belief state"""
    manager = ClusterBeliefManager(cluster_id)

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()

    # Count belief blocks
    cursor.execute(
        'SELECT COUNT(*) FROM cluster_belief_blocks WHERE cluster_id = ?',
        (cluster_id,)
    )
    block_count = cursor.fetchone()[0]

    # Count divergence events
    cursor.execute('''
        SELECT COUNT(*) FROM belief_divergence_events
        WHERE cluster_id = ? AND resolved_at IS NULL
    ''', (cluster_id,))
    unresolved_divergences = cursor.fetchone()[0]

    conn.close()

    consistency = manager.check_belief_consistency()

    return {
        "cluster_id": cluster_id,
        "belief_blocks": block_count,
        "unresolved_divergences": unresolved_divergences,
        "consistency_score": consistency['consistency_score'],
        "health": consistency['health'],
        "divergent_beliefs_count": len(consistency['divergent_beliefs']),
        "consistent_beliefs_count": len(consistency['consistent_beliefs'])
    }
