"""
Advanced Prompting Techniques for Autonomous AGI Systems
=========================================================

This module implements systematic prompting patterns from research
on advanced AI prompting techniques, adapted for autonomous recursive
self-improvement systems.

Core Modules:
- chain_of_verification: Self-correction loops with mandatory verification
- meta_prompting: Agents design their own optimal prompts
- multi_agent_debate: Competing perspectives for critical decisions
- reasoning_scaffolds: Deliberate over-instruction and reference priming
- edge_case_learning: Graduated examples for boundary detection

Based on insights from: Teaching Advanced Prompting Techniques
Video ID: GTEz5WWbfiw
"""

__version__ = "1.0.0"

from .chain_of_verification import (
    ChainOfVerification,
    VerificationStep,
    VerificationResult,
    VerificationPhase
)
from .meta_prompting import (
    MetaPrompter,
    PromptOptimizer,
    ReversePrompter,
    DesignedPrompt,
    MetaPromptResult
)
from .multi_agent_debate import (
    MultiAgentDebate,
    AgentPerspective,
    DebateProtocol,
    PriorityType,
    DebateResult
)
from .reasoning_scaffolds import (
    DeliberateOverInstruction,
    ReferenceClassPriming,
    ZeroShotCoT,
    ReasoningScaffoldOrchestrator,
    ScaffoldType,
    build_full_scaffold
)
from .edge_case_learning import (
    EdgeCaseLearner,
    GraduatedExample,
    BoundaryDetector,
    EdgeCase,
    EdgeCaseSeverity,
    ExampleType
)

__all__ = [
    # Chain of Verification
    "ChainOfVerification",
    "VerificationStep",
    "VerificationResult",
    "VerificationPhase",

    # Meta Prompting
    "MetaPrompter",
    "PromptOptimizer",
    "ReversePrompter",
    "DesignedPrompt",
    "MetaPromptResult",

    # Multi-Agent Debate
    "MultiAgentDebate",
    "AgentPerspective",
    "DebateProtocol",
    "PriorityType",
    "DebateResult",

    # Reasoning Scaffolds
    "DeliberateOverInstruction",
    "ReferenceClassPriming",
    "ZeroShotCoT",
    "ReasoningScaffoldOrchestrator",
    "ScaffoldType",
    "build_full_scaffold",

    # Edge Case Learning
    "EdgeCaseLearner",
    "GraduatedExample",
    "BoundaryDetector",
    "EdgeCase",
    "EdgeCaseSeverity",
    "ExampleType",
]
