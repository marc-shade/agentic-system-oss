"""
DSPy Optimizer Module for AGI System
=====================================

Production-ready DSPy integration for automatic prompt optimization,
self-improving modules, and integration with Darwin-Gödel machine.

Components:
- optimizer.py: Main DSPy optimization engine
- modules.py: Reusable DSPy modules for common tasks
- metrics.py: Performance tracking and analysis
- integration.py: Darwin-Gödel machine integration
"""

from .optimizer import DSPyOptimizer, OptimizationConfig
from .modules import (
    AgentReasoningModule,
    CodeAnalysisModule,
    PromptEvolutionModule,
    ChainOfThoughtAgent,
    ReActAgent,
)
from .metrics import MetricsCollector, PromptPerformance
from .integration import DarwinGodelIntegration

__version__ = "1.0.0"
__all__ = [
    "DSPyOptimizer",
    "OptimizationConfig",
    "AgentReasoningModule",
    "CodeAnalysisModule",
    "PromptEvolutionModule",
    "ChainOfThoughtAgent",
    "ReActAgent",
    "MetricsCollector",
    "PromptPerformance",
    "DarwinGodelIntegration",
]
