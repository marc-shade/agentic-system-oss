"""
AGI Memory Enhancement Module

Provides AGI-level memory capabilities:
- Phase 1: Cross-session identity & memory-action loop
- Phase 2: Temporal reasoning & consolidation
- Phase 3: Emotional tagging & associative networks
- Phase 4: Meta-cognitive awareness & self-improvement
"""

from .agent_identity import AgentIdentity, SessionManager
from .action_tracker import ActionTracker
from .temporal_reasoning import TemporalReasoning
from .consolidation import ConsolidationEngine
from .emotional_memory import EmotionalMemory
from .associative_network import AssociativeNetwork, AttentionMechanism, ForgettingCurve
from .metacognition import MetaCognition, PerformanceTracker
from .self_improvement import SelfImprovement, CoordinationManager

__all__ = [
    'AgentIdentity',
    'SessionManager',
    'ActionTracker',
    'TemporalReasoning',
    'ConsolidationEngine',
    'EmotionalMemory',
    'AssociativeNetwork',
    'AttentionMechanism',
    'ForgettingCurve',
    'MetaCognition',
    'PerformanceTracker',
    'SelfImprovement',
    'CoordinationManager'
]
