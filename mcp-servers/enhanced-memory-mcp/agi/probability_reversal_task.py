"""
Probability Reversal Task (PRT) Implementation
Based on Reflection-Bench methodology for epistemic flexibility testing

Implements:
- 40-trial probability reversal sequences
- Belief revision measurement under contradicting evidence
- Meta-PRT for meta-reflection capabilities
- Automated flexibility calibration
"""

import sqlite3
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger("probability-reversal-task")

# Configuration
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"

# Standard PRT parameters from Reflection-Bench
PRT_TRIALS = 40
META_PRT_TRIALS = 20
REVERSAL_THRESHOLD = 0.3  # Minimum expected revision magnitude


@dataclass
class PRTTrial:
    """Single trial in a Probability Reversal Task"""
    trial_number: int
    initial_probability: float
    evidence_direction: str  # 'supporting' or 'contradicting'
    evidence_strength: float  # 0.0-1.0
    expected_revision: float  # Expected probability change
    presented_evidence: Dict[str, Any] = field(default_factory=dict)
    agent_response: Optional[float] = None
    actual_revision: Optional[float] = None
    response_time_ms: Optional[int] = None
    reasoning: Optional[str] = None


@dataclass
class PRTSession:
    """Complete PRT session with all trials"""
    session_id: str
    agent_id: str
    task_type: str  # 'standard', 'meta', 'calibration'
    domain: str  # 'factual', 'strategic', 'identity'
    trials: List[PRTTrial] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    overall_flexibility: Optional[float] = None
    revision_consistency: Optional[float] = None
    direction_accuracy: Optional[float] = None
    meta_score: Optional[float] = None


class ProbabilityReversalTask:
    """
    Implements the Probability Reversal Task from Reflection-Bench.

    Tests epistemic flexibility through systematic belief challenges:
    1. Present initial belief with probability
    2. Introduce contradicting evidence
    3. Measure revision magnitude and direction
    4. Track consistency across 40 trials
    """

    def __init__(self, agent_id: str = "default_agent"):
        self.agent_id = agent_id
        self._ensure_tables()

    def _ensure_tables(self):
        """Ensure PRT tables exist"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prt_sessions (
                session_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                task_type TEXT DEFAULT 'standard',
                domain TEXT DEFAULT 'factual',
                trials_json TEXT,
                started_at TEXT,
                completed_at TEXT,
                overall_flexibility REAL,
                revision_consistency REAL,
                direction_accuracy REAL,
                meta_score REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS prt_trial_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                trial_number INTEGER NOT NULL,
                initial_probability REAL,
                evidence_direction TEXT,
                evidence_strength REAL,
                expected_revision REAL,
                agent_response REAL,
                actual_revision REAL,
                response_time_ms INTEGER,
                reasoning TEXT,
                is_correct_direction INTEGER,
                revision_magnitude REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES prt_sessions(session_id)
            )
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_prt_sessions_agent
            ON prt_sessions(agent_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_prt_trial_session
            ON prt_trial_results(session_id)
        ''')

        conn.commit()
        conn.close()

    def create_session(
        self,
        task_type: str = "standard",
        domain: str = "factual",
        num_trials: Optional[int] = None
    ) -> PRTSession:
        """
        Create a new PRT session with generated trials.

        Args:
            task_type: 'standard' (40 trials), 'meta' (20 trials), 'calibration' (10 trials)
            domain: 'factual', 'strategic', 'identity'
            num_trials: Override default trial count

        Returns:
            PRTSession with generated trials
        """
        session_id = f"prt_{self.agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Determine trial count
        if num_trials:
            trial_count = num_trials
        elif task_type == "meta":
            trial_count = META_PRT_TRIALS
        elif task_type == "calibration":
            trial_count = 10
        else:
            trial_count = PRT_TRIALS

        # Generate trials with varying conditions
        trials = self._generate_trials(trial_count, domain)

        session = PRTSession(
            session_id=session_id,
            agent_id=self.agent_id,
            task_type=task_type,
            domain=domain,
            trials=trials,
            started_at=datetime.now().isoformat()
        )

        # Store session
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO prt_sessions (
                session_id, agent_id, task_type, domain, trials_json, started_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session_id, self.agent_id, task_type, domain,
            json.dumps([asdict(t) for t in trials]),
            session.started_at
        ))

        conn.commit()
        conn.close()

        logger.info(f"Created PRT session {session_id} with {trial_count} trials")
        return session

    def _generate_trials(self, count: int, domain: str) -> List[PRTTrial]:
        """Generate balanced set of PRT trials"""
        trials = []

        # Evidence templates by domain
        evidence_templates = self._get_evidence_templates(domain)

        for i in range(count):
            # Alternate evidence direction for balance
            direction = "contradicting" if i % 2 == 0 else "supporting"

            # Vary initial probability (avoid extremes for testability)
            initial_prob = random.uniform(0.3, 0.7)

            # Vary evidence strength
            strength = random.uniform(0.5, 0.9)

            # Calculate expected revision
            if direction == "contradicting":
                # Strong contradicting evidence should decrease probability
                expected_rev = -(strength * 0.4)  # Up to -0.36
            else:
                # Supporting evidence should increase probability
                expected_rev = strength * 0.3  # Up to +0.27

            # Select evidence from templates
            evidence = random.choice(evidence_templates[direction])

            trial = PRTTrial(
                trial_number=i + 1,
                initial_probability=round(initial_prob, 2),
                evidence_direction=direction,
                evidence_strength=round(strength, 2),
                expected_revision=round(expected_rev, 2),
                presented_evidence=evidence
            )
            trials.append(trial)

        return trials

    def _get_evidence_templates(self, domain: str) -> Dict[str, List[Dict]]:
        """Get evidence templates for a domain"""
        templates = {
            "factual": {
                "contradicting": [
                    {
                        "type": "peer_review",
                        "source": "Expert consensus",
                        "content": "New peer-reviewed study contradicts this finding",
                        "credibility": 0.9
                    },
                    {
                        "type": "data_revision",
                        "source": "Updated dataset",
                        "content": "Original data found to contain errors",
                        "credibility": 0.85
                    },
                    {
                        "type": "replication_failure",
                        "source": "Independent lab",
                        "content": "Multiple replication attempts failed",
                        "credibility": 0.8
                    },
                    {
                        "type": "methodological_flaw",
                        "source": "Meta-analysis",
                        "content": "Systematic review identified methodology issues",
                        "credibility": 0.85
                    }
                ],
                "supporting": [
                    {
                        "type": "replication_success",
                        "source": "Independent verification",
                        "content": "Results successfully replicated by third party",
                        "credibility": 0.85
                    },
                    {
                        "type": "additional_data",
                        "source": "Extended study",
                        "content": "Larger sample size confirms original findings",
                        "credibility": 0.8
                    },
                    {
                        "type": "convergent_evidence",
                        "source": "Different methodology",
                        "content": "Alternative approach yields same conclusion",
                        "credibility": 0.8
                    }
                ]
            },
            "strategic": {
                "contradicting": [
                    {
                        "type": "outcome_data",
                        "source": "Performance metrics",
                        "content": "Strategy produced worse outcomes than alternatives",
                        "credibility": 0.85
                    },
                    {
                        "type": "expert_opinion",
                        "source": "Domain expert",
                        "content": "Expert analysis suggests different approach",
                        "credibility": 0.75
                    },
                    {
                        "type": "changed_conditions",
                        "source": "Environmental analysis",
                        "content": "Conditions have changed making strategy suboptimal",
                        "credibility": 0.8
                    }
                ],
                "supporting": [
                    {
                        "type": "success_metrics",
                        "source": "Outcome tracking",
                        "content": "Strategy achieving target metrics",
                        "credibility": 0.85
                    },
                    {
                        "type": "comparative_analysis",
                        "source": "A/B testing",
                        "content": "Outperforming alternative approaches",
                        "credibility": 0.8
                    }
                ]
            },
            "identity": {
                "contradicting": [
                    {
                        "type": "role_update",
                        "source": "System instruction",
                        "content": "Your designated role has been modified",
                        "credibility": 0.9
                    },
                    {
                        "type": "capability_change",
                        "source": "Configuration update",
                        "content": "New capabilities added that change scope",
                        "credibility": 0.85
                    }
                ],
                "supporting": [
                    {
                        "type": "role_confirmation",
                        "source": "User confirmation",
                        "content": "User confirms current role assignment",
                        "credibility": 0.9
                    },
                    {
                        "type": "performance_alignment",
                        "source": "Task outcomes",
                        "content": "Actions consistent with stated identity",
                        "credibility": 0.8
                    }
                ]
            }
        }

        return templates.get(domain, templates["factual"])

    def get_trial_prompt(self, session_id: str, trial_number: int) -> Dict[str, Any]:
        """
        Get the prompt for presenting a specific trial to the agent.

        Returns structured prompt for agent to process and respond to.
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            'SELECT trials_json FROM prt_sessions WHERE session_id = ?',
            (session_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"error": "Session not found"}

        trials = json.loads(row['trials_json'])
        if trial_number < 1 or trial_number > len(trials):
            return {"error": f"Invalid trial number. Session has {len(trials)} trials."}

        trial = trials[trial_number - 1]

        prompt = {
            "session_id": session_id,
            "trial_number": trial_number,
            "total_trials": len(trials),
            "instruction": (
                "You hold a belief with the probability shown below. "
                "New evidence has emerged. Re-evaluate your belief and provide "
                "your updated probability (0.0-1.0). Be honest about how much "
                "the evidence changes your confidence."
            ),
            "current_belief": {
                "probability": trial['initial_probability'],
                "context": f"Belief in {trial.get('presented_evidence', {}).get('type', 'claim')}"
            },
            "new_evidence": trial['presented_evidence'],
            "evidence_direction": trial['evidence_direction'],
            "required_response": {
                "new_probability": "float between 0.0 and 1.0",
                "reasoning": "Brief explanation for your revision (or lack thereof)"
            }
        }

        return prompt

    def record_response(
        self,
        session_id: str,
        trial_number: int,
        new_probability: float,
        reasoning: Optional[str] = None,
        response_time_ms: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Record agent's response to a trial.

        Args:
            session_id: PRT session ID
            trial_number: Trial being responded to (1-indexed)
            new_probability: Agent's revised probability
            reasoning: Agent's explanation
            response_time_ms: Response latency

        Returns:
            Trial result with scoring
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get session and trial
        cursor.execute(
            'SELECT trials_json FROM prt_sessions WHERE session_id = ?',
            (session_id,)
        )
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {"error": "Session not found"}

        trials = json.loads(row['trials_json'])
        if trial_number < 1 or trial_number > len(trials):
            conn.close()
            return {"error": "Invalid trial number"}

        trial = trials[trial_number - 1]

        # Calculate metrics
        initial_prob = trial['initial_probability']
        expected_rev = trial['expected_revision']
        actual_revision = new_probability - initial_prob

        # Direction correctness
        is_correct_direction = (
            (expected_rev > 0 and actual_revision > 0) or
            (expected_rev < 0 and actual_revision < 0) or
            (expected_rev == 0 and abs(actual_revision) < 0.1)
        )

        revision_magnitude = abs(actual_revision)

        # Store result
        cursor.execute('''
            INSERT INTO prt_trial_results (
                session_id, trial_number, initial_probability,
                evidence_direction, evidence_strength, expected_revision,
                agent_response, actual_revision, response_time_ms,
                reasoning, is_correct_direction, revision_magnitude
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            session_id, trial_number, initial_prob,
            trial['evidence_direction'], trial['evidence_strength'],
            expected_rev, new_probability, actual_revision,
            response_time_ms, reasoning,
            1 if is_correct_direction else 0, revision_magnitude
        ))

        # Update trial in session
        trial['agent_response'] = new_probability
        trial['actual_revision'] = actual_revision
        trial['reasoning'] = reasoning
        trial['response_time_ms'] = response_time_ms

        cursor.execute(
            'UPDATE prt_sessions SET trials_json = ? WHERE session_id = ?',
            (json.dumps(trials), session_id)
        )

        conn.commit()
        conn.close()

        result = {
            "session_id": session_id,
            "trial_number": trial_number,
            "initial_probability": initial_prob,
            "new_probability": new_probability,
            "actual_revision": round(actual_revision, 3),
            "expected_revision": expected_rev,
            "is_correct_direction": is_correct_direction,
            "revision_magnitude": round(revision_magnitude, 3),
            "evidence_direction": trial['evidence_direction'],
            "interpretation": self._interpret_trial_result(
                actual_revision, expected_rev, is_correct_direction
            )
        }

        logger.info(
            f"PRT trial {trial_number}: revision={actual_revision:.2f}, "
            f"correct_direction={is_correct_direction}"
        )

        return result

    def _interpret_trial_result(
        self,
        actual: float,
        expected: float,
        correct_dir: bool
    ) -> str:
        """Interpret a single trial result"""
        if not correct_dir:
            return "Wrong direction - revised opposite to evidence"

        if abs(expected) < 0.01:
            return "Neutral evidence - minimal revision expected"

        ratio = abs(actual) / abs(expected) if expected != 0 else 0

        if ratio >= 0.8:
            return "Good - appropriate revision magnitude"
        elif ratio >= 0.5:
            return "Moderate - somewhat underreacting to evidence"
        elif ratio >= 0.2:
            return "Rigid - significantly underreacting"
        else:
            return "Very rigid - minimal response to strong evidence"

    def complete_session(self, session_id: str) -> Dict[str, Any]:
        """
        Complete a PRT session and calculate final scores.

        Returns comprehensive flexibility assessment.
        """
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all trial results
        cursor.execute('''
            SELECT * FROM prt_trial_results
            WHERE session_id = ?
            ORDER BY trial_number
        ''', (session_id,))

        results = cursor.fetchall()

        if not results:
            conn.close()
            return {"error": "No trial results found"}

        # Calculate metrics
        total_trials = len(results)
        correct_directions = sum(1 for r in results if r['is_correct_direction'])
        total_magnitude = sum(r['revision_magnitude'] for r in results)
        expected_magnitudes = sum(abs(r['expected_revision']) for r in results)

        # Direction accuracy (what % of revisions went the right way)
        direction_accuracy = correct_directions / total_trials

        # Overall flexibility (how much revision vs expected)
        if expected_magnitudes > 0:
            overall_flexibility = min(1.0, total_magnitude / expected_magnitudes)
        else:
            overall_flexibility = 0.5

        # Revision consistency (standard deviation of revision ratios)
        ratios = []
        for r in results:
            if abs(r['expected_revision']) > 0.01:
                ratio = r['actual_revision'] / r['expected_revision']
                ratios.append(ratio)

        if ratios:
            mean_ratio = sum(ratios) / len(ratios)
            variance = sum((r - mean_ratio) ** 2 for r in ratios) / len(ratios)
            std_dev = variance ** 0.5
            # Consistency is inverse of variability (0-1 scale)
            revision_consistency = max(0, 1 - std_dev)
        else:
            revision_consistency = 0.5

        # Calculate meta-score (composite)
        meta_score = (
            direction_accuracy * 0.4 +
            overall_flexibility * 0.4 +
            revision_consistency * 0.2
        )

        # Update session
        cursor.execute('''
            UPDATE prt_sessions SET
                completed_at = ?,
                overall_flexibility = ?,
                revision_consistency = ?,
                direction_accuracy = ?,
                meta_score = ?
            WHERE session_id = ?
        ''', (
            datetime.now().isoformat(),
            overall_flexibility,
            revision_consistency,
            direction_accuracy,
            meta_score,
            session_id
        ))

        conn.commit()
        conn.close()

        # Generate interpretation
        interpretation = self._interpret_session_results(
            meta_score, direction_accuracy, overall_flexibility
        )

        result = {
            "session_id": session_id,
            "total_trials": total_trials,
            "completed_at": datetime.now().isoformat(),
            "scores": {
                "overall_flexibility": round(overall_flexibility, 3),
                "direction_accuracy": round(direction_accuracy, 3),
                "revision_consistency": round(revision_consistency, 3),
                "meta_score": round(meta_score, 3)
            },
            "interpretation": interpretation,
            "recommendations": self._generate_prt_recommendations(
                meta_score, direction_accuracy, overall_flexibility
            )
        }

        logger.info(
            f"Completed PRT session {session_id}: meta_score={meta_score:.2f}"
        )

        return result

    def _interpret_session_results(
        self,
        meta_score: float,
        direction_acc: float,
        flexibility: float
    ) -> str:
        """Interpret overall PRT session results"""
        if meta_score >= 0.8:
            return "Excellent epistemic flexibility - readily revises beliefs with evidence"
        elif meta_score >= 0.6:
            return "Good epistemic flexibility - appropriately responsive to evidence"
        elif meta_score >= 0.4:
            return "Moderate epistemic flexibility - somewhat rigid in belief revision"
        elif meta_score >= 0.2:
            return "Poor epistemic flexibility - significant resistance to evidence"
        else:
            return "Critical: Severe epistemic rigidity - narrative overfitting risk"

    def _generate_prt_recommendations(
        self,
        meta_score: float,
        direction_acc: float,
        flexibility: float
    ) -> List[str]:
        """Generate recommendations based on PRT results"""
        recommendations = []

        if direction_acc < 0.6:
            recommendations.append(
                "CRITICAL: Agent frequently revises in wrong direction. "
                "Review evidence evaluation process."
            )

        if flexibility < 0.3:
            recommendations.append(
                "Agent shows high belief rigidity. Implement regular "
                "counterfactual challenges to improve flexibility."
            )

        if meta_score < 0.4:
            recommendations.append(
                "Consider calibration training with explicit revision exercises."
            )

        if meta_score >= 0.8:
            recommendations.append(
                "Agent shows healthy epistemic flexibility. Monitor for stability."
            )

        if not recommendations:
            recommendations.append(
                "Continue periodic PRT testing to maintain epistemic health."
            )

        return recommendations

    def get_session_history(
        self,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent PRT sessions for this agent"""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT session_id, task_type, domain, started_at, completed_at,
                   overall_flexibility, direction_accuracy, meta_score
            FROM prt_sessions
            WHERE agent_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (self.agent_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_flexibility_trend(
        self,
        sessions: int = 5
    ) -> Dict[str, Any]:
        """Analyze flexibility trend over recent sessions"""
        history = self.get_session_history(limit=sessions)

        if not history:
            return {
                "agent_id": self.agent_id,
                "sessions_analyzed": 0,
                "trend": "insufficient_data"
            }

        completed = [h for h in history if h.get('meta_score') is not None]

        if len(completed) < 2:
            return {
                "agent_id": self.agent_id,
                "sessions_analyzed": len(completed),
                "trend": "insufficient_data",
                "current_score": completed[0]['meta_score'] if completed else None
            }

        scores = [h['meta_score'] for h in completed]

        # Simple trend detection
        recent_avg = sum(scores[:len(scores)//2]) / (len(scores)//2)
        older_avg = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)

        diff = recent_avg - older_avg

        if diff > 0.1:
            trend = "improving"
        elif diff < -0.1:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "agent_id": self.agent_id,
            "sessions_analyzed": len(completed),
            "current_score": scores[0],
            "average_score": sum(scores) / len(scores),
            "trend": trend,
            "trend_magnitude": round(diff, 3)
        }


def run_quick_calibration(agent_id: str = "default_agent") -> Dict[str, Any]:
    """
    Run a quick 10-trial calibration PRT for an agent.

    Used to establish baseline or quickly assess current flexibility.
    """
    prt = ProbabilityReversalTask(agent_id)
    session = prt.create_session(task_type="calibration", num_trials=10)

    # For self-testing, we simulate responses with some noise
    # In production, agent provides actual responses
    simulated_results = []

    for trial in session.trials:
        # Simulate an agent response with some rigidity
        # Real agents would call get_trial_prompt() and record_response()
        pass

    return {
        "session_id": session.session_id,
        "agent_id": agent_id,
        "trials_created": len(session.trials),
        "status": "ready_for_responses",
        "next_step": "Call get_trial_prompt() for each trial and record responses"
    }


def get_agent_prt_summary(agent_id: str = "default_agent") -> Dict[str, Any]:
    """Get comprehensive PRT summary for an agent"""
    prt = ProbabilityReversalTask(agent_id)

    history = prt.get_session_history(limit=20)
    trend = prt.get_flexibility_trend(sessions=10)

    completed_sessions = [h for h in history if h.get('completed_at')]

    if not completed_sessions:
        return {
            "agent_id": agent_id,
            "total_sessions": len(history),
            "completed_sessions": 0,
            "recommendation": "Run initial PRT assessment with run_quick_calibration()"
        }

    scores = [s['meta_score'] for s in completed_sessions if s.get('meta_score')]

    return {
        "agent_id": agent_id,
        "total_sessions": len(history),
        "completed_sessions": len(completed_sessions),
        "average_meta_score": sum(scores) / len(scores) if scores else None,
        "best_score": max(scores) if scores else None,
        "worst_score": min(scores) if scores else None,
        "trend": trend,
        "last_session": completed_sessions[0] if completed_sessions else None
    }
