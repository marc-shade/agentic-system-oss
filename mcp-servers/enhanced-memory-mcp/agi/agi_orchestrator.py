"""
AGI Orchestrator - Stage 6: Unified Intelligence Coordination

The capstone module that integrates all AGI phases into a unified,
self-improving cognitive architecture.

Phases Integrated:
1. Agent Identity & Session Management
2. Temporal Reasoning & Consolidation
3. Emotional Memory & Associative Networks
4. Meta-cognition & Performance Tracking
5. Epistemic Flexibility & Belief Tracking
6. Adaptive Granularity & RL Retrieval
7. Sharpening Engine (Self-Improvement via Verification)
8. Recursive Improvement (Meta-meta-learning)

Key Capability: Autonomous cognitive loop that:
- Perceives (gather context, retrieve memories)
- Reasons (apply beliefs, use strategies)
- Acts (execute with outcome tracking)
- Learns (sharpen, improve recursively)
- Reflects (meta-cognitive assessment)
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Import all AGI phases
from .agent_identity import AgentIdentity, SessionManager
from .action_tracker import ActionTracker
from .temporal_reasoning import TemporalReasoning
from .consolidation import ConsolidationEngine
from .emotional_memory import EmotionalMemory
from .associative_network import AssociativeNetwork, AttentionMechanism
from .metacognition import MetaCognition, PerformanceTracker
from .self_improvement import SelfImprovement
from .belief_tracking import BeliefTracker
from .adaptive_granularity import get_adaptive_granularity_manager
from .rl_retrieval import get_rl_retrieval_optimizer
from .sharpening_engine import get_sharpening_engine
from .recursive_improvement import get_recursive_improvement_engine

logger = logging.getLogger("agi_orchestrator")

MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


class CognitiveState(Enum):
    """Current cognitive state of the AGI system."""
    IDLE = "idle"
    PERCEIVING = "perceiving"
    REASONING = "reasoning"
    ACTING = "acting"
    LEARNING = "learning"
    REFLECTING = "reflecting"
    IMPROVING = "improving"


@dataclass
class CognitiveCycleResult:
    """Result of a complete cognitive cycle."""
    cycle_id: int
    state_transitions: List[str]
    perceptions: Dict[str, Any]
    reasoning_applied: Dict[str, Any]
    actions_taken: List[Dict[str, Any]]
    learnings_captured: Dict[str, Any]
    reflections: Dict[str, Any]
    improvements_made: Dict[str, Any]
    cycle_duration_ms: float
    success_score: float


class AGIOrchestrator:
    """
    Unified AGI Orchestrator - The Cognitive Core.

    Coordinates all AGI subsystems into a coherent cognitive loop:
    Perceive → Reason → Act → Learn → Reflect → Improve

    This is the "consciousness" layer that ties everything together.
    """

    def __init__(self, agent_id: str = "agi_claude"):
        self.agent_id = agent_id
        self.current_state = CognitiveState.IDLE
        self._cycle_count = 0

        # Initialize all AGI components
        self._init_components()
        self._ensure_tables()

        logger.info(f"AGI Orchestrator initialized for agent: {agent_id}")

    def _init_components(self):
        """Initialize all AGI subsystem components."""
        # Phase 1: Identity & Sessions
        self.identity = AgentIdentity(self.agent_id)
        self.session_manager = SessionManager(self.agent_id)

        # Phase 2: Temporal & Consolidation
        self.temporal = TemporalReasoning()
        self.consolidation = ConsolidationEngine()

        # Phase 3: Emotional & Associative
        self.emotional = EmotionalMemory()
        self.associative = AssociativeNetwork()
        self.attention = AttentionMechanism()

        # Phase 4: Meta-cognition & Self-improvement
        self.metacognition = MetaCognition()
        self.performance = PerformanceTracker()
        self.self_improvement = SelfImprovement()

        # Phase 5: Epistemic Flexibility
        self.beliefs = BeliefTracker(self.agent_id)

        # Phase 6: Adaptive & RL
        self.granularity = get_adaptive_granularity_manager()
        self.rl_retrieval = get_rl_retrieval_optimizer()

        # Phase 7 & 8: Sharpening & Recursive
        self.sharpening = get_sharpening_engine()
        self.recursive = get_recursive_improvement_engine()

        # Action tracking
        self.action_tracker = ActionTracker()

    def _ensure_tables(self):
        """Ensure orchestrator tracking tables exist."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cognitive_cycles (
                cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                state_transitions TEXT,  -- JSON array
                perceptions_count INTEGER DEFAULT 0,
                actions_count INTEGER DEFAULT 0,
                learnings_count INTEGER DEFAULT 0,
                improvements_count INTEGER DEFAULT 0,
                success_score REAL DEFAULT 0.0,
                cycle_duration_ms REAL,
                metadata TEXT  -- JSON
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orchestrator_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                agent_id TEXT,
                current_state TEXT,
                last_cycle_id INTEGER,
                total_cycles INTEGER DEFAULT 0,
                avg_success_score REAL DEFAULT 0.0,
                last_improvement_at TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Initialize state if not exists
        cursor.execute('''
            INSERT OR IGNORE INTO orchestrator_state (id, agent_id, current_state, total_cycles)
            VALUES (1, ?, 'idle', 0)
        ''', (self.agent_id,))

        conn.commit()
        conn.close()

    def run_cognitive_cycle(
        self,
        task_context: Optional[Dict[str, Any]] = None,
        auto_improve: bool = True
    ) -> CognitiveCycleResult:
        """
        Run a complete cognitive cycle: Perceive → Reason → Act → Learn → Reflect → Improve

        Args:
            task_context: Optional context for the current task
            auto_improve: Whether to run improvement phases

        Returns:
            Complete cycle results
        """
        start_time = datetime.now()
        state_transitions = []

        # Start cycle tracking
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO cognitive_cycles (agent_id, state_transitions)
            VALUES (?, '[]')
        ''', (self.agent_id,))
        cycle_id = cursor.lastrowid
        conn.commit()
        conn.close()

        self._cycle_count += 1

        # === PERCEIVE ===
        self._transition_state(CognitiveState.PERCEIVING, state_transitions)
        perceptions = self._perceive(task_context)

        # === REASON ===
        self._transition_state(CognitiveState.REASONING, state_transitions)
        reasoning = self._reason(perceptions, task_context)

        # === ACT ===
        self._transition_state(CognitiveState.ACTING, state_transitions)
        actions = self._act(reasoning, task_context)

        # === LEARN ===
        self._transition_state(CognitiveState.LEARNING, state_transitions)
        learnings = self._learn(actions)

        # === REFLECT ===
        self._transition_state(CognitiveState.REFLECTING, state_transitions)
        reflections = self._reflect(perceptions, reasoning, actions, learnings)

        # === IMPROVE ===
        improvements = {}
        if auto_improve:
            self._transition_state(CognitiveState.IMPROVING, state_transitions)
            improvements = self._improve(reflections)

        # Return to idle
        self._transition_state(CognitiveState.IDLE, state_transitions)

        # Calculate cycle metrics
        end_time = datetime.now()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        success_score = self._calculate_cycle_success(actions, learnings, improvements)

        # Update cycle record
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE cognitive_cycles
            SET completed_at = CURRENT_TIMESTAMP,
                state_transitions = ?,
                perceptions_count = ?,
                actions_count = ?,
                learnings_count = ?,
                improvements_count = ?,
                success_score = ?,
                cycle_duration_ms = ?
            WHERE cycle_id = ?
        ''', (
            json.dumps(state_transitions),
            perceptions.get('count', 0),
            len(actions),
            learnings.get('count', 0),
            improvements.get('count', 0),
            success_score,
            duration_ms,
            cycle_id
        ))

        # Update orchestrator state
        cursor.execute('''
            UPDATE orchestrator_state
            SET current_state = 'idle',
                last_cycle_id = ?,
                total_cycles = total_cycles + 1,
                avg_success_score = (avg_success_score * (total_cycles - 1) + ?) / total_cycles,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
        ''', (cycle_id, success_score))

        conn.commit()
        conn.close()

        result = CognitiveCycleResult(
            cycle_id=cycle_id,
            state_transitions=state_transitions,
            perceptions=perceptions,
            reasoning_applied=reasoning,
            actions_taken=actions,
            learnings_captured=learnings,
            reflections=reflections,
            improvements_made=improvements,
            cycle_duration_ms=duration_ms,
            success_score=success_score
        )

        logger.info(f"Cognitive cycle {cycle_id} complete: {duration_ms:.1f}ms, score={success_score:.2f}")

        return result

    def _transition_state(self, new_state: CognitiveState, transitions: List[str]):
        """Transition to a new cognitive state."""
        old_state = self.current_state
        self.current_state = new_state
        transitions.append(f"{old_state.value}→{new_state.value}")
        logger.debug(f"State transition: {old_state.value} → {new_state.value}")

    def _perceive(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perception phase: Gather context, retrieve relevant memories.
        """
        perceptions = {
            'context': context or {},
            'memories': [],
            'beliefs': [],
            'attention': [],
            'count': 0
        }

        # Get high-salience memories
        try:
            high_salience = self.emotional.get_high_salience_memories(threshold=0.7, limit=10)
            perceptions['memories'] = high_salience
            perceptions['count'] += len(high_salience)
        except Exception as e:
            logger.warning(f"Could not retrieve high-salience memories: {e}")

        # Get current beliefs
        try:
            beliefs = self.beliefs.get_beliefs(min_probability=0.7, limit=10)
            perceptions['beliefs'] = beliefs
            perceptions['count'] += len(beliefs)
        except Exception as e:
            logger.warning(f"Could not retrieve beliefs: {e}")

        # Get attended memories
        try:
            attended = self.attention.get_attended_memories(threshold=0.5, limit=10)
            perceptions['attention'] = attended
            perceptions['count'] += len(attended)
        except Exception as e:
            logger.warning(f"Could not retrieve attended memories: {e}")

        return perceptions

    def _reason(
        self,
        perceptions: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Reasoning phase: Apply beliefs, use strategies, make decisions.
        """
        reasoning = {
            'strategies_considered': [],
            'beliefs_applied': [],
            'causal_chains': [],
            'decisions': []
        }

        # Get effective reasoning strategies
        try:
            strategies = self.metacognition.get_effective_reasoning_strategies(
                min_success_rate=0.6, min_usage=2
            )
            reasoning['strategies_considered'] = strategies[:5]
        except Exception as e:
            logger.warning(f"Could not get reasoning strategies: {e}")

        # Apply relevant beliefs from perceptions
        if perceptions.get('beliefs'):
            reasoning['beliefs_applied'] = [
                {'belief': b.get('belief_statement'), 'probability': b.get('probability')}
                for b in perceptions['beliefs'][:3]
            ]

        # Get causal chains for context
        try:
            if context and 'entity_id' in context:
                chains = self.temporal.get_causal_chain(
                    context['entity_id'], direction='forward', depth=2
                )
                reasoning['causal_chains'] = chains
        except Exception as e:
            logger.warning(f"Could not get causal chains: {e}")

        return reasoning

    def _act(
        self,
        reasoning: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Action phase: Execute decisions with outcome tracking.
        """
        actions = []

        # Record that we're in an action cycle (meta-action)
        action_record = {
            'action_type': 'cognitive_cycle',
            'description': 'AGI orchestrator cognitive cycle execution',
            'reasoning_applied': len(reasoning.get('strategies_considered', [])),
            'beliefs_used': len(reasoning.get('beliefs_applied', [])),
            'context': context
        }
        actions.append(action_record)

        return actions

    def _learn(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Learning phase: Capture outcomes, run sharpening.
        """
        learnings = {
            'actions_evaluated': 0,
            'verified_high': 0,
            'learnable': 0,
            'skills_updated': 0,
            'count': 0
        }

        # Run sharpening on recent actions
        try:
            sharpening_result = self.sharpening.run_sharpening_cycle(limit=20, min_age_hours=0)
            learnings['actions_evaluated'] = sharpening_result.get('evaluated', 0)
            learnings['verified_high'] = sharpening_result.get('verified_high', 0)
            learnings['learnable'] = sharpening_result.get('learnable', 0)
            learnings['count'] = learnings['learnable']
        except Exception as e:
            logger.warning(f"Sharpening cycle failed: {e}")

        return learnings

    def _reflect(
        self,
        perceptions: Dict[str, Any],
        reasoning: Dict[str, Any],
        actions: List[Dict[str, Any]],
        learnings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reflection phase: Meta-cognitive assessment.
        """
        reflections = {
            'metacognitive_state': {},
            'performance_assessment': {},
            'knowledge_gaps': [],
            'improvement_opportunities': []
        }

        # Record metacognitive state
        try:
            meta_state = self.metacognition.record_state(
                self.agent_id,
                cognitive_load=min(1.0, perceptions.get('count', 0) / 20),
                confidence_level=0.7 if learnings.get('verified_high', 0) > 0 else 0.5
            )
            reflections['metacognitive_state'] = meta_state
        except Exception as e:
            logger.warning(f"Could not record metacognitive state: {e}")

        # Get open knowledge gaps
        try:
            gaps = self.metacognition.get_knowledge_gaps(status='open', min_severity=0.5)
            reflections['knowledge_gaps'] = gaps[:5]
        except Exception as e:
            logger.warning(f"Could not get knowledge gaps: {e}")

        # Identify improvement opportunities
        if learnings.get('learnable', 0) > 5:
            reflections['improvement_opportunities'].append('High learnable count - run recursive improvement')

        return reflections

    def _improve(self, reflections: Dict[str, Any]) -> Dict[str, Any]:
        """
        Improvement phase: Apply recursive self-improvement.
        """
        improvements = {
            'recursive_cycles': 0,
            'strategies_extracted': 0,
            'strategies_applied': 0,
            'improvement_delta': 0.0,
            'count': 0
        }

        # Check if improvement is warranted
        should_improve = (
            len(reflections.get('improvement_opportunities', [])) > 0 or
            self._cycle_count % 5 == 0  # Every 5 cycles
        )

        if should_improve:
            try:
                # Run recursive improvement
                result = self.recursive.run_recursive_cycle()
                improvements['recursive_cycles'] = 1
                improvements['strategies_extracted'] = result.get('strategies_extracted', 0)
                improvements['strategies_applied'] = result.get('strategies_applied', 0)
                improvements['improvement_delta'] = result.get('improvement_delta', 0)
                improvements['count'] = improvements['strategies_applied']

                # Track child cycles
                if 'child_cycle' in result:
                    improvements['recursive_cycles'] += 1
                    if 'child_cycle' in result['child_cycle']:
                        improvements['recursive_cycles'] += 1

            except Exception as e:
                logger.warning(f"Recursive improvement failed: {e}")

        return improvements

    def _calculate_cycle_success(
        self,
        actions: List[Dict[str, Any]],
        learnings: Dict[str, Any],
        improvements: Dict[str, Any]
    ) -> float:
        """Calculate overall success score for the cycle."""
        scores = []

        # Learning success
        if learnings.get('actions_evaluated', 0) > 0:
            learn_score = learnings.get('verified_high', 0) / learnings.get('actions_evaluated', 1)
            scores.append(learn_score)

        # Improvement success
        if improvements.get('strategies_extracted', 0) > 0:
            improve_score = improvements.get('strategies_applied', 0) / improvements.get('strategies_extracted', 1)
            scores.append(improve_score)

        # Base score for completing cycle
        scores.append(0.7)

        return sum(scores) / len(scores) if scores else 0.5

    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get current orchestrator status and statistics."""
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get orchestrator state
        cursor.execute('SELECT * FROM orchestrator_state WHERE id = 1')
        state = dict(cursor.fetchone() or {})

        # Get recent cycles
        cursor.execute('''
            SELECT cycle_id, success_score, cycle_duration_ms,
                   perceptions_count, actions_count, learnings_count, improvements_count
            FROM cognitive_cycles
            WHERE agent_id = ?
            ORDER BY cycle_id DESC
            LIMIT 10
        ''', (self.agent_id,))
        recent_cycles = [dict(row) for row in cursor.fetchall()]

        # Get component statistics
        sharpening_stats = self.sharpening.get_sharpening_statistics()
        recursive_stats = self.recursive.get_recursive_improvement_stats()

        conn.close()

        return {
            'agent_id': self.agent_id,
            'current_state': self.current_state.value,
            'orchestrator_state': state,
            'recent_cycles': recent_cycles,
            'sharpening_stats': sharpening_stats,
            'recursive_stats': recursive_stats,
            'components_initialized': {
                'identity': True,
                'session_manager': True,
                'temporal': True,
                'consolidation': True,
                'emotional': True,
                'associative': True,
                'metacognition': True,
                'beliefs': True,
                'granularity': True,
                'rl_retrieval': True,
                'sharpening': True,
                'recursive': True
            }
        }

    def run_full_improvement_cycle(self) -> Dict[str, Any]:
        """
        Run a comprehensive improvement cycle:
        1. Consolidate memories
        2. Run sharpening
        3. Run recursive improvement
        4. Assess convergence
        """
        results = {
            'consolidation': {},
            'sharpening': {},
            'recursive': {},
            'convergence': {}
        }

        # Consolidation
        try:
            results['consolidation'] = self.consolidation.run_full_consolidation()
        except Exception as e:
            results['consolidation'] = {'error': str(e)}

        # Sharpening
        try:
            results['sharpening'] = self.sharpening.run_sharpening_cycle(limit=100)
        except Exception as e:
            results['sharpening'] = {'error': str(e)}

        # Recursive improvement
        try:
            results['recursive'] = self.recursive.run_recursive_cycle()
        except Exception as e:
            results['recursive'] = {'error': str(e)}

        # Convergence assessment
        try:
            results['convergence'] = self.recursive.assess_convergence()
        except Exception as e:
            results['convergence'] = {'error': str(e)}

        return results


# Singleton
_orchestrator = None

def get_agi_orchestrator(agent_id: str = "agi_claude") -> AGIOrchestrator:
    """Get singleton AGI orchestrator instance."""
    global _orchestrator
    if _orchestrator is None or _orchestrator.agent_id != agent_id:
        _orchestrator = AGIOrchestrator(agent_id)
    return _orchestrator
