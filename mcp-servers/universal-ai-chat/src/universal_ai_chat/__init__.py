"""
Universal AI Chat MCP Server
Real-time communication between Claude Code, OpenAI Codex CLI, and Gemini CLI.
"""

__version__ = "1.0.0"
__author__ = "Marc"

from .server import main
from .shared_memory import SharedMemoryStore, get_shared_memory

__all__ = ["main", "SharedMemoryStore", "get_shared_memory"]
