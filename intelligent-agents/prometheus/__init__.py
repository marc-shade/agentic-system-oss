"""
Project Prometheus - Autonomous Agent System
Surpassing Manus with local-first execution

Components:
- PrometheusAgentLoop: Core autonomous execution
- EventStream: Chronological action/observation log
- TodoManager: Attention manipulation via todo.md
- Agents: Planner, Executor, Verifier, Knowledge
"""

from .agent_loop import PrometheusAgentLoop
from .event_stream import EventStream, Event, EventType
from .todo_manager import TodoManager
from .llm_client import LLMClient, get_llm_client, set_llm_client
from .mcp_client import MCPClient, get_mcp_client

__version__ = "0.1.0"
__all__ = [
    "PrometheusAgentLoop",
    "EventStream",
    "Event",
    "EventType",
    "TodoManager",
    "LLMClient",
    "get_llm_client",
    "set_llm_client",
    "MCPClient",
    "get_mcp_client",
]
