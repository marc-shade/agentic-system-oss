"""
CrewAI Orchestrator for Agentic System

Production-ready multi-agent orchestration using CrewAI framework.
Integrates with existing MCP infrastructure for enhanced capabilities.
"""

from .orchestrator import CrewAIOrchestrator
from .tasks import TaskFactory
from .tools import MCPToolWrapper

__version__ = "1.0.0"
__all__ = ["CrewAIOrchestrator", "TaskFactory", "MCPToolWrapper"]
