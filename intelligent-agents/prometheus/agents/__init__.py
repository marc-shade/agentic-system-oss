"""
Prometheus Agents - Specialized agents for autonomous execution.

Four-agent architecture inspired by Manus:
- Planner: Decomposes tasks into executable steps
- Executor: Runs one tool per iteration
- Verifier: Validates results and triggers replanning
- Knowledge: Retrieves information from multiple sources
"""

from .planner import PlannerAgent
from .executor import ExecutorAgent
from .verifier import VerifierAgent
from .knowledge import KnowledgeAgent

__all__ = [
    "PlannerAgent",
    "ExecutorAgent",
    "VerifierAgent",
    "KnowledgeAgent"
]
