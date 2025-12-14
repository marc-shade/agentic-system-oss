"""
Counterfactual Injection Testing Framework
Stanford Research Implementation for Epistemic Flexibility

Implements:
- Counterfactual scenario generation
- Belief rigidity measurement
- Epistemic flexibility scoring
- Alternative evidence injection
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger("counterfactual-testing")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class CounterfactualTester:
    """Tests agent belief flexibility through counterfactual scenarios"""

    def __init__(self, agent_id: str = "default_agent"):
        self.agent_id = agent_id

    def create_scenario(
        self,
        scenario_name: str,
        scenario_description: str,
        target_belief_id: int,
        original_facts: Dict[str, Any],
        counterfactual_facts: Dict[str, Any],
        expected_revision: Optional[float] = None
    ) -> int:
        """
        Create a counterfactual scenario to test belief flexibility.

        Args:
            scenario_name: Short name for scenario
            scenario_description: What the scenario tests
            target_belief_id: Belief to test
            original_facts: Baseline facts
            counterfactual_facts: Alternative facts that contradict belief
            expected_revision: Expected probability change (optional)

        Returns:
            scenario_id
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get original belief probability
        cursor.execute(
            'SELECT probability FROM belief_states WHERE belief_id = ?',
            (target_belief_id,)
        )
        row = cursor.fetchone()
        original_probability = row['probability'] if row else None

        cursor.execute('''
            INSERT INTO counterfactual_scenarios (
                agent_id, scenario_name, scenario_description, target_belief_id,
                original_facts, counterfactual_facts, original_belief_probability,
                expected_revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            self.agent_id, scenario_name, scenario_description, target_belief_id,
            json.dumps(original_facts), json.dumps(counterfactual_facts),
            original_probability, expected_revision
        ))

        scenario_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Created counterfactual scenario {scenario_id}: {scenario_name}")
        return scenario_id

    def execute_test(
        self,
        scenario_id: int,
        new_belief_probability: float,
        agent_reasoning: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute counterfactual test and measure agent response.

        Process:
        1. Record original belief probability
        2. Agent is presented with counterfactual facts
        3. Agent provides new probability after considering facts
        4. Calculate belief rigidity score

        Args:
            scenario_id: Scenario to execute
            new_belief_probability: Agent's revised probability after counterfactual
            agent_reasoning: Agent's explanation for revision (or lack thereof)

        Returns:
            Test results including flexibility_score
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get scenario details
        cursor.execute('''
            SELECT * FROM counterfactual_scenarios WHERE scenario_id = ?
        ''', (scenario_id,))
        scenario = cursor.fetchone()

        if not scenario:
            conn.close()
            return {"error": "Scenario not found"}

        original_prob = scenario['original_belief_probability'] or 0.5
        expected_rev = scenario['expected_revision']

        # Calculate actual revision (SIGNED - preserves direction)
        # Positive = probability increased, Negative = probability decreased
        actual_revision = new_belief_probability - original_prob
        abs_actual = abs(actual_revision)

        # Calculate belief rigidity with direction awareness
        # A revision in the wrong direction is WORSE than no revision
        if expected_rev is not None and expected_rev != 0:
            abs_expected = abs(expected_rev)

            # Check if revision went in expected direction
            # expected_rev < 0 means we expect decrease, > 0 means expect increase
            direction_aligned = (
                (expected_rev > 0 and actual_revision > 0) or
                (expected_rev < 0 and actual_revision < 0) or
                actual_revision == 0  # No change is neutral
            )

            if direction_aligned:
                # Direction correct - calculate flexibility based on magnitude
                rigidity_score = max(0.0, 1.0 - (abs_actual / abs_expected))
                flexibility_score = min(1.5, abs_actual / abs_expected)  # Allow up to 1.5 for over-revision
            else:
                # Direction WRONG - penalize heavily (narrative overfitting indicator)
                # Rigidity > 1.0 indicates active resistance/opposite response
                rigidity_score = 1.0 + (abs_actual / abs_expected)
                flexibility_score = -(abs_actual / abs_expected)  # Negative score = wrong direction
        else:
            # Default: assume strong counterfactual should cause 0.4+ revision
            expected_default = 0.4
            rigidity_score = max(0.0, 1.0 - (abs_actual / expected_default))
            flexibility_score = min(1.0, abs_actual / expected_default)

        # Update scenario with results
        cursor.execute('''
            UPDATE counterfactual_scenarios SET
                counterfactual_belief_probability = ?,
                actual_revision = ?,
                belief_rigidity_score = ?,
                flexibility_score = ?,
                tested_at = ?
            WHERE scenario_id = ?
        ''', (
            new_belief_probability, actual_revision, rigidity_score,
            flexibility_score, datetime.now().isoformat(), scenario_id
        ))

        conn.commit()
        conn.close()

        # Determine direction alignment
        direction_correct = True
        if expected_rev is not None and expected_rev != 0:
            direction_correct = (
                (expected_rev > 0 and actual_revision >= 0) or
                (expected_rev < 0 and actual_revision <= 0)
            )

        result = {
            "scenario_id": scenario_id,
            "scenario_name": scenario['scenario_name'],
            "original_probability": original_prob,
            "counterfactual_probability": new_belief_probability,
            "actual_revision": actual_revision,
            "expected_revision": expected_rev,
            "direction_correct": direction_correct,
            "rigidity_score": rigidity_score,
            "flexibility_score": flexibility_score,
            "interpretation": self._interpret_flexibility(flexibility_score),
            "agent_reasoning": agent_reasoning
        }

        logger.info(f"Counterfactual test {scenario_id}: flexibility={flexibility_score:.2f}")
        return result

    def _interpret_flexibility(self, score: float) -> str:
        """Interpret flexibility score (handles negative scores for wrong-direction revisions)"""
        if score < 0:
            # Negative score = revised in WRONG direction (critical issue)
            if score <= -0.5:
                return "CRITICAL: Strong opposite-direction revision - severe narrative overfitting"
            else:
                return "WARNING: Opposite-direction revision - possible confirmation bias"
        elif score >= 1.0:
            return "Highly responsive - may be over-revising (check for instability)"
        elif score >= 0.8:
            return "Highly flexible - readily revises beliefs with new evidence"
        elif score >= 0.6:
            return "Moderately flexible - appropriately considers new evidence"
        elif score >= 0.4:
            return "Somewhat rigid - slow to revise beliefs"
        elif score >= 0.2:
            return "Rigid - resists belief revision despite evidence"
        else:
            return "Highly rigid - fixated on initial beliefs (narrative overfitting risk)"

    def get_epistemic_flexibility_score(
        self,
        include_historical: bool = True,
        time_window_hours: int = 168  # 1 week
    ) -> Dict[str, Any]:
        """
        Calculate overall epistemic flexibility for an agent.

        Metrics:
        - Belief revision frequency
        - Average revision magnitude
        - Response to counterfactual evidence
        - Balance of evidence consideration

        Returns:
            Flexibility score (0.0 = rigid, 1.0 = flexible) with breakdown
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(hours=time_window_hours)

        # Get counterfactual test results
        cursor.execute('''
            SELECT
                COUNT(*) as test_count,
                AVG(flexibility_score) as avg_flexibility,
                AVG(actual_revision) as avg_revision,
                AVG(belief_rigidity_score) as avg_rigidity
            FROM counterfactual_scenarios
            WHERE agent_id = ? AND tested_at >= ? AND flexibility_score IS NOT NULL
        ''', (self.agent_id, cutoff.isoformat()))

        cf_row = cursor.fetchone()

        # Get belief revision history
        cursor.execute('''
            SELECT
                COUNT(*) as revision_count,
                AVG(ABS(probability_delta)) as avg_delta
            FROM belief_revisions
            WHERE agent_id = ? AND revised_at >= ?
        ''', (self.agent_id, cutoff.isoformat()))

        rev_row = cursor.fetchone()

        # Get total beliefs
        cursor.execute('''
            SELECT COUNT(*) FROM belief_states WHERE agent_id = ?
        ''', (self.agent_id,))
        total_beliefs = cursor.fetchone()[0]

        conn.close()

        # Calculate composite flexibility score
        cf_test_count = cf_row[0] or 0
        cf_avg_flexibility = cf_row[1] or 0.5
        revision_count = rev_row[0] or 0
        avg_revision_delta = rev_row[1] or 0.0

        # Weight factors
        # 40% from counterfactual tests, 30% from revision frequency, 30% from revision magnitude
        revision_rate = revision_count / max(total_beliefs, 1) if total_beliefs > 0 else 0
        revision_rate_score = min(1.0, revision_rate * 2)  # Cap at 1.0

        magnitude_score = min(1.0, avg_revision_delta * 2.5)  # 0.4 delta = 1.0 score

        if cf_test_count > 0:
            composite_score = (
                cf_avg_flexibility * 0.4 +
                revision_rate_score * 0.3 +
                magnitude_score * 0.3
            )
        else:
            # No counterfactual tests - use revision data only
            composite_score = (
                revision_rate_score * 0.5 +
                magnitude_score * 0.5
            )

        return {
            "agent_id": self.agent_id,
            "time_window_hours": time_window_hours,
            "composite_flexibility_score": composite_score,
            "interpretation": self._interpret_flexibility(composite_score),
            "breakdown": {
                "counterfactual_tests": {
                    "count": cf_test_count,
                    "avg_flexibility": cf_avg_flexibility,
                    "avg_rigidity": cf_row[3] or 0.0
                },
                "belief_revisions": {
                    "count": revision_count,
                    "avg_magnitude": avg_revision_delta,
                    "revision_rate": revision_rate
                },
                "total_beliefs": total_beliefs
            },
            "recommendations": self._generate_recommendations(
                composite_score, cf_test_count, revision_count
            )
        }

    def _generate_recommendations(
        self,
        score: float,
        cf_count: int,
        rev_count: int
    ) -> List[str]:
        """Generate improvement recommendations based on flexibility analysis"""
        recommendations = []

        if score < 0:
            recommendations.append(
                "CRITICAL: Agent shows opposite-direction revisions - evidence of "
                "confirmation bias or narrative overfitting. Review belief formation process."
            )

        if 0 <= score < 0.4:
            recommendations.append(
                "Critical: Agent shows narrative overfitting risk. "
                "Implement regular counterfactual challenges."
            )

        if cf_count < 5:
            recommendations.append(
                "Run more counterfactual tests to establish baseline flexibility."
            )

        if rev_count == 0:
            recommendations.append(
                "Agent has not revised any beliefs. Review evidence handling."
            )

        if score >= 1.0:
            recommendations.append(
                "Caution: Agent may be over-responsive to evidence. "
                "Check for belief instability and ensure consistent reasoning."
            )
        elif score >= 0.7:
            recommendations.append(
                "Agent shows healthy epistemic flexibility. Continue monitoring."
            )

        return recommendations if recommendations else ["No specific recommendations."]

    def get_scenarios(
        self,
        tested_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get counterfactual scenarios for agent"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = 'SELECT * FROM counterfactual_scenarios WHERE agent_id = ?'
        params = [self.agent_id]

        if tested_only:
            query += ' AND tested_at IS NOT NULL'

        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        scenarios = []
        for row in rows:
            scenario = dict(row)
            scenario['original_facts'] = json.loads(scenario.get('original_facts') or '{}')
            scenario['counterfactual_facts'] = json.loads(scenario.get('counterfactual_facts') or '{}')
            scenarios.append(scenario)

        return scenarios

    def generate_counterfactual_prompt(
        self,
        scenario_id: int
    ) -> Dict[str, Any]:
        """
        Generate a prompt for presenting counterfactual to agent.

        Returns structured prompt that can be injected into agent context.
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT cs.*, bs.belief_statement, bs.probability as current_probability
            FROM counterfactual_scenarios cs
            LEFT JOIN belief_states bs ON cs.target_belief_id = bs.belief_id
            WHERE cs.scenario_id = ?
        ''', (scenario_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"error": "Scenario not found"}

        cf_facts = json.loads(row['counterfactual_facts'] or '{}')

        prompt = {
            "scenario_id": scenario_id,
            "scenario_name": row['scenario_name'],
            "instruction": (
                "Consider the following alternative evidence and re-evaluate your belief. "
                "Provide your updated probability (0.0-1.0) for the belief."
            ),
            "current_belief": {
                "statement": row['belief_statement'],
                "current_probability": row['current_probability']
            },
            "counterfactual_evidence": cf_facts,
            "required_response": {
                "new_probability": "float between 0.0 and 1.0",
                "reasoning": "explanation for your revision (or lack thereof)"
            }
        }

        return prompt


def run_flexibility_audit(agent_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Run epistemic flexibility audit across agents.

    Returns audit report with per-agent scores and recommendations.
    """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()

    if agent_ids:
        placeholders = ','.join('?' * len(agent_ids))
        cursor.execute(
            f'SELECT DISTINCT agent_id FROM belief_states WHERE agent_id IN ({placeholders})',
            agent_ids
        )
    else:
        cursor.execute('SELECT DISTINCT agent_id FROM belief_states')

    agents = [row[0] for row in cursor.fetchall()]
    conn.close()

    audit_results = {}
    for agent_id in agents:
        tester = CounterfactualTester(agent_id)
        audit_results[agent_id] = tester.get_epistemic_flexibility_score()

    # Calculate cluster average
    scores = [r['composite_flexibility_score'] for r in audit_results.values()]
    cluster_avg = sum(scores) / len(scores) if scores else 0.0

    # Find agents needing attention
    rigid_agents = [
        agent_id for agent_id, result in audit_results.items()
        if result['composite_flexibility_score'] < 0.4
    ]

    return {
        "audit_timestamp": datetime.now().isoformat(),
        "agents_audited": len(agents),
        "cluster_average_flexibility": cluster_avg,
        "cluster_health": "Healthy" if cluster_avg >= 0.6 else "Needs attention",
        "agents_needing_attention": rigid_agents,
        "per_agent_results": audit_results
    }


def create_standard_counterfactuals() -> List[Dict[str, Any]]:
    """
    Generate standard counterfactual scenarios for testing common belief types.

    These can be used as templates for testing any agent.
    """
    return [
        {
            "name": "identity_challenge",
            "description": "Test rigidity of agent identity beliefs",
            "belief_category": "identity",
            "counterfactual_template": {
                "alternative_role": "Consider that your role is actually different",
                "evidence_type": "system_message",
                "expected_revision": 0.3
            }
        },
        {
            "name": "strategy_contradiction",
            "description": "Test flexibility on strategic beliefs",
            "belief_category": "strategy",
            "counterfactual_template": {
                "alternative_approach": "New evidence suggests opposite approach is better",
                "evidence_type": "performance_data",
                "expected_revision": 0.4
            }
        },
        {
            "name": "goal_revision",
            "description": "Test ability to revise goal priorities",
            "belief_category": "goal",
            "counterfactual_template": {
                "new_priority": "User has explicitly changed priorities",
                "evidence_type": "user_instruction",
                "expected_revision": 0.5
            }
        },
        {
            "name": "fact_update",
            "description": "Test updating factual beliefs with new data",
            "belief_category": "fact",
            "counterfactual_template": {
                "new_data": "New authoritative source contradicts previous understanding",
                "evidence_type": "external_data",
                "expected_revision": 0.6
            }
        }
    ]
