"""
Specialized Agents for Multi-Agent Coordinator
==============================================

Real agent implementations for the Multi-Agent Coordinator.

Available Agents:
- CodeGenerationAgent: Generates code from specifications
- AnalysisAgent: Analyzes code, data, and patterns
- ResearchAgent: Researches topics and gathers information
- TestingAgent: Creates and runs tests
- DocumentationAgent: Generates documentation
- OptimizationAgent: Optimizes code and algorithms
"""

from .base_agent import BaseAgent, AgentResult
from .code_generation_agent import CodeGenerationAgent
from .analysis_agent import AnalysisAgent
from .research_agent import ResearchAgent
from .testing_agent import TestingAgent
from .documentation_agent import DocumentationAgent
from .optimization_agent import OptimizationAgent

__all__ = [
    "BaseAgent",
    "AgentResult",
    "CodeGenerationAgent",
    "AnalysisAgent",
    "ResearchAgent",
    "TestingAgent",
    "DocumentationAgent",
    "OptimizationAgent",
]
