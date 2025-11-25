#!/usr/bin/env python3
"""
Feedback Loop Integration
=========================

Connects all self-improvement components into a cohesive feedback loop:

1. Meta-Learning Engine → tracks outcomes and recommends agents
2. Darwin-Gödel Machine → proposes and tracks modifications
3. Continuous Eval Runner → grades outputs in real-time
4. Skill Evolution System → A/B tests improvements

Flow:
    Agent Output → Eval → Meta-Learning → Pattern Detection →
    Darwin-Gödel Proposal → Approval → Apply → Re-Eval → Confirm/Rollback

This closes the loop on self-improvement by ensuring every modification
is measured and its impact is fed back into the learning system.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "intelligent-agents"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class FeedbackEvent:
    """An event in the feedback loop."""
    event_type: str  # eval_complete, pattern_detected, modification_proposed, modification_applied
    source: str
    data: Dict[str, Any]
    timestamp: str


@dataclass
class ImprovementCycle:
    """A complete improvement cycle."""
    cycle_id: str
    trigger: str  # pattern, low_score, manual
    proposed_at: str
    applied_at: Optional[str]
    verified_at: Optional[str]
    modification_id: Optional[str]
    baseline_score: float
    new_score: Optional[float]
    improvement: Optional[float]
    status: str  # proposed, applied, verified, rolled_back


class FeedbackLoop:
    """
    Coordinates the self-improvement feedback loop.

    Responsibilities:
    - Monitor eval results for patterns
    - Trigger improvement proposals when needed
    - Track modification impact
    - Feed results back to meta-learning
    - Maintain improvement history
    """

    def __init__(self):
        # Import components lazily to avoid circular imports
        self._meta_learning = None
        self._darwin_godel = None
        self._skill_evolution = None
        self._eval_runner = None

        # Event subscribers
        self.subscribers: Dict[str, List[Callable]] = {
            'eval_complete': [],
            'pattern_detected': [],
            'modification_proposed': [],
            'modification_applied': [],
            'improvement_verified': [],
            'rollback_triggered': []
        }

        # Active improvement cycles
        self.active_cycles: Dict[str, ImprovementCycle] = {}

        # Thresholds
        self.low_score_threshold = 0.6  # Trigger improvement if avg < this
        self.high_score_threshold = 0.9  # Candidate for skill promotion
        self.min_samples_for_pattern = 5
        self.improvement_threshold = 0.05  # Min 5% improvement to keep

        # History
        self.event_history: List[FeedbackEvent] = []
        self.max_history = 1000

    @property
    def meta_learning(self):
        if self._meta_learning is None:
            try:
                from meta_learning_engine import MetaLearningEngine
                self._meta_learning = MetaLearningEngine()
            except ImportError:
                logger.warning("Meta-learning engine not available")
        return self._meta_learning

    @property
    def darwin_godel(self):
        if self._darwin_godel is None:
            try:
                from darwin_godel_machine import DarwinGodelMachine
                self._darwin_godel = DarwinGodelMachine()
            except ImportError:
                logger.warning("Darwin-Gödel machine not available")
        return self._darwin_godel

    @property
    def skill_evolution(self):
        if self._skill_evolution is None:
            try:
                from skill_evolution_system import SkillEvolutionSystem
                self._skill_evolution = SkillEvolutionSystem()
            except ImportError:
                logger.warning("Skill evolution system not available")
        return self._skill_evolution

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to feedback events."""
        if event_type in self.subscribers:
            self.subscribers[event_type].append(callback)

    def _emit_event(self, event: FeedbackEvent):
        """Emit an event to subscribers."""
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history = self.event_history[-self.max_history:]

        for callback in self.subscribers.get(event.event_type, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Event callback failed: {e}")

    def on_eval_complete(
        self,
        eval_type: str,
        agent_id: str,
        task_id: str,
        score: float,
        passed: bool,
        dimensions: Dict[str, Any]
    ):
        """
        Handle completed evaluation.

        This is the entry point for the feedback loop.
        """
        logger.info(f"Eval complete: {eval_type} by {agent_id} = {score:.2f}")

        # Record in meta-learning
        if self.meta_learning:
            from meta_learning_engine import TaskOutcome
            outcome = TaskOutcome(
                task_id=task_id,
                task_type=eval_type,
                agent_used=agent_id,
                success=passed,
                execution_time_ms=0,
                error_message=None if passed else f"Score below threshold: {score:.2f}",
                quality_score=score,
                timestamp=datetime.now(),
                context={'dimensions': dimensions}
            )
            self.meta_learning.record_outcome(outcome)

        # Emit event
        self._emit_event(FeedbackEvent(
            event_type='eval_complete',
            source='eval_runner',
            data={
                'eval_type': eval_type,
                'agent_id': agent_id,
                'task_id': task_id,
                'score': score,
                'passed': passed
            },
            timestamp=datetime.now().isoformat()
        ))

        # Check for patterns and potential improvements
        self._check_for_improvement_triggers(eval_type, agent_id, score)

    def _check_for_improvement_triggers(
        self,
        eval_type: str,
        agent_id: str,
        score: float
    ):
        """Check if we should trigger an improvement cycle."""
        if not self.meta_learning:
            return

        # Get recent performance for this eval type
        summary = self.meta_learning.get_learning_summary()
        recent_success = summary.get('recent_success_rate', 1.0)
        recent_quality = summary.get('recent_quality_score', 1.0)

        # Check for low performance pattern
        if recent_quality < self.low_score_threshold:
            logger.info(f"Low quality detected ({recent_quality:.2f}), considering improvement")
            self._propose_improvement(
                trigger='low_score',
                context={
                    'eval_type': eval_type,
                    'agent_id': agent_id,
                    'recent_quality': recent_quality
                }
            )

        # Check for patterns
        patterns = self.meta_learning.detect_patterns(lookback_days=7)
        if patterns:
            for pattern in patterns:
                self._emit_event(FeedbackEvent(
                    event_type='pattern_detected',
                    source='meta_learning',
                    data=pattern,
                    timestamp=datetime.now().isoformat()
                ))

    def _propose_improvement(self, trigger: str, context: Dict[str, Any]):
        """Propose a self-improvement based on detected issues."""
        if not self.darwin_godel:
            logger.warning("Darwin-Gödel not available for improvement proposal")
            return

        import uuid
        cycle_id = str(uuid.uuid4())

        # Get baseline score
        summary = self.meta_learning.get_learning_summary() if self.meta_learning else {}
        baseline_score = summary.get('recent_quality_score', 0.0)

        cycle = ImprovementCycle(
            cycle_id=cycle_id,
            trigger=trigger,
            proposed_at=datetime.now().isoformat(),
            applied_at=None,
            verified_at=None,
            modification_id=None,
            baseline_score=baseline_score,
            new_score=None,
            improvement=None,
            status='proposed'
        )

        self.active_cycles[cycle_id] = cycle

        self._emit_event(FeedbackEvent(
            event_type='modification_proposed',
            source='feedback_loop',
            data={
                'cycle_id': cycle_id,
                'trigger': trigger,
                'baseline_score': baseline_score,
                'context': context
            },
            timestamp=datetime.now().isoformat()
        ))

        logger.info(f"Improvement cycle {cycle_id} proposed (trigger: {trigger})")
        return cycle_id

    def apply_improvement(self, cycle_id: str, modification_id: str) -> bool:
        """Apply an improvement and start verification."""
        if cycle_id not in self.active_cycles:
            logger.error(f"Unknown cycle: {cycle_id}")
            return False

        cycle = self.active_cycles[cycle_id]

        if self.darwin_godel:
            success = self.darwin_godel.apply_modification_by_id(modification_id)
            if not success:
                logger.error(f"Failed to apply modification {modification_id}")
                return False

        cycle.modification_id = modification_id
        cycle.applied_at = datetime.now().isoformat()
        cycle.status = 'applied'

        self._emit_event(FeedbackEvent(
            event_type='modification_applied',
            source='feedback_loop',
            data={
                'cycle_id': cycle_id,
                'modification_id': modification_id
            },
            timestamp=datetime.now().isoformat()
        ))

        logger.info(f"Improvement {modification_id} applied in cycle {cycle_id}")
        return True

    def verify_improvement(self, cycle_id: str, new_score: float) -> Dict[str, Any]:
        """
        Verify if an improvement actually improved things.

        Returns decision: keep, rollback, or uncertain
        """
        if cycle_id not in self.active_cycles:
            return {'decision': 'unknown', 'reason': 'Cycle not found'}

        cycle = self.active_cycles[cycle_id]
        cycle.new_score = new_score
        cycle.improvement = new_score - cycle.baseline_score
        cycle.verified_at = datetime.now().isoformat()

        # Determine outcome
        if cycle.improvement >= self.improvement_threshold:
            decision = 'keep'
            cycle.status = 'verified'
            reason = f"Improvement of {cycle.improvement:.1%} exceeds threshold"
        elif cycle.improvement < -self.improvement_threshold:
            decision = 'rollback'
            cycle.status = 'rolled_back'
            reason = f"Regression of {-cycle.improvement:.1%} detected"
        else:
            decision = 'uncertain'
            cycle.status = 'verified'
            reason = f"Change of {cycle.improvement:.1%} within noise threshold"

        self._emit_event(FeedbackEvent(
            event_type='improvement_verified',
            source='feedback_loop',
            data={
                'cycle_id': cycle_id,
                'decision': decision,
                'baseline': cycle.baseline_score,
                'new_score': new_score,
                'improvement': cycle.improvement
            },
            timestamp=datetime.now().isoformat()
        ))

        # If rollback needed, trigger it
        if decision == 'rollback' and self.darwin_godel:
            self.darwin_godel.rollback_last()
            self._emit_event(FeedbackEvent(
                event_type='rollback_triggered',
                source='feedback_loop',
                data={'cycle_id': cycle_id, 'modification_id': cycle.modification_id},
                timestamp=datetime.now().isoformat()
            ))

        logger.info(f"Improvement verification: {decision} ({reason})")

        return {
            'decision': decision,
            'reason': reason,
            'improvement': cycle.improvement,
            'baseline': cycle.baseline_score,
            'new_score': new_score
        }

    def get_improvement_stats(self) -> Dict[str, Any]:
        """Get statistics about improvement cycles."""
        total = len(self.active_cycles)
        if total == 0:
            return {'total_cycles': 0}

        verified = [c for c in self.active_cycles.values() if c.status == 'verified']
        rolled_back = [c for c in self.active_cycles.values() if c.status == 'rolled_back']

        improvements = [c.improvement for c in verified if c.improvement is not None]

        return {
            'total_cycles': total,
            'verified': len(verified),
            'rolled_back': len(rolled_back),
            'pending': total - len(verified) - len(rolled_back),
            'avg_improvement': sum(improvements) / len(improvements) if improvements else 0.0,
            'success_rate': len([i for i in improvements if i > 0]) / len(improvements) if improvements else 0.0
        }

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Get recent feedback events."""
        return [
            {
                'event_type': e.event_type,
                'source': e.source,
                'data': e.data,
                'timestamp': e.timestamp
            }
            for e in self.event_history[-limit:]
        ]


# Singleton instance
_feedback_loop_instance = None


def get_feedback_loop() -> FeedbackLoop:
    """Get or create the singleton feedback loop."""
    global _feedback_loop_instance
    if _feedback_loop_instance is None:
        _feedback_loop_instance = FeedbackLoop()
    return _feedback_loop_instance


if __name__ == "__main__":
    # Demo usage
    loop = FeedbackLoop()

    # Simulate some evaluations
    loop.on_eval_complete(
        eval_type='code',
        agent_id='coder_1',
        task_id='task_001',
        score=0.85,
        passed=True,
        dimensions={'syntax': 1.0, 'execution': 0.8, 'style': 0.75}
    )

    loop.on_eval_complete(
        eval_type='code',
        agent_id='coder_1',
        task_id='task_002',
        score=0.55,  # Low score
        passed=False,
        dimensions={'syntax': 1.0, 'execution': 0.3, 'style': 0.65}
    )

    print("\n=== Improvement Stats ===")
    print(json.dumps(loop.get_improvement_stats(), indent=2))

    print("\n=== Recent Events ===")
    for event in loop.get_recent_events(limit=5):
        print(f"  [{event['event_type']}] {event['source']}: {event['data']}")
