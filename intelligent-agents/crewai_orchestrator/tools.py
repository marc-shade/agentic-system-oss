"""
MCP Tool Wrappers for CrewAI Integration

Provides CrewAI-compatible tool wrappers for existing MCP infrastructure.
"""

import json
import httpx
from typing import Any, Optional, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool


class MemorySearchInput(BaseModel):
    """Input for memory search tool."""
    query: str = Field(description="Search query for memory retrieval")
    limit: int = Field(default=10, description="Maximum results to return")


class MemorySearchTool(BaseTool):
    """Search enhanced memory system for relevant knowledge."""
    name: str = "memory_search"
    description: str = "Search the enhanced memory system for relevant knowledge, patterns, and past learnings"
    args_schema: Type[BaseModel] = MemorySearchInput

    def _run(self, query: str, limit: int = 10) -> str:
        try:
            response = httpx.post(
                "http://localhost:3100/search",
                json={"query": query, "limit": limit},
                timeout=30.0
            )
            if response.status_code == 200:
                return json.dumps(response.json(), indent=2)
            return f"Memory search returned status {response.status_code}"
        except Exception as e:
            return f"Memory search error: {str(e)}"


class MemoryStoreInput(BaseModel):
    """Input for memory store tool."""
    name: str = Field(description="Entity name for the memory")
    entity_type: str = Field(description="Type of entity (e.g., learning, pattern, code)")
    observations: list[str] = Field(description="List of observations to store")


class MemoryStoreTool(BaseTool):
    """Store knowledge in enhanced memory system."""
    name: str = "memory_store"
    description: str = "Store new knowledge, patterns, or learnings in the enhanced memory system"
    args_schema: Type[BaseModel] = MemoryStoreInput

    def _run(self, name: str, entity_type: str, observations: list[str]) -> str:
        try:
            response = httpx.post(
                "http://localhost:3100/entities",
                json={"entities": [{"name": name, "entityType": entity_type, "observations": observations}]},
                timeout=30.0
            )
            if response.status_code == 200:
                return f"Successfully stored entity: {name}"
            return f"Memory store returned status {response.status_code}"
        except Exception as e:
            return f"Memory store error: {str(e)}"


class TaskCreateInput(BaseModel):
    """Input for task creation tool."""
    title: str = Field(description="Task title")
    description: str = Field(default="", description="Task description")
    priority: int = Field(default=5, description="Priority 1-10")


class TaskCreateTool(BaseTool):
    """Create persistent task in agent runtime."""
    name: str = "create_task"
    description: str = "Create a persistent task that survives across sessions"
    args_schema: Type[BaseModel] = TaskCreateInput

    def _run(self, title: str, description: str = "", priority: int = 5) -> str:
        try:
            response = httpx.post(
                "http://localhost:3101/tasks",
                json={"title": title, "description": description, "priority": priority},
                timeout=30.0
            )
            if response.status_code == 200:
                return json.dumps(response.json(), indent=2)
            return f"Task creation returned status {response.status_code}"
        except Exception as e:
            return f"Task creation error: {str(e)}"


class VoiceAnnounceInput(BaseModel):
    """Input for voice announcement tool."""
    message: str = Field(description="Message to announce")
    wait_for_response: bool = Field(default=False, description="Wait for user response")


class VoiceAnnounceTool(BaseTool):
    """Announce status via voice mode."""
    name: str = "voice_announce"
    description: str = "Announce status or milestone via text-to-speech"
    args_schema: Type[BaseModel] = VoiceAnnounceInput

    def _run(self, message: str, wait_for_response: bool = False) -> str:
        try:
            response = httpx.post(
                "http://localhost:3102/converse",
                json={"message": message, "wait_for_response": wait_for_response},
                timeout=60.0
            )
            if response.status_code == 200:
                return "Announcement delivered"
            return f"Voice announce returned status {response.status_code}"
        except Exception as e:
            return f"Voice announce error: {str(e)}"


class CodeAnalysisInput(BaseModel):
    """Input for code analysis tool."""
    code: str = Field(description="Code to analyze")
    language: str = Field(default="python", description="Programming language")


class CodeAnalysisTool(BaseTool):
    """Analyze code for quality, security, and best practices."""
    name: str = "analyze_code"
    description: str = "Analyze code for quality issues, security vulnerabilities, and best practices"
    args_schema: Type[BaseModel] = CodeAnalysisInput

    def _run(self, code: str, language: str = "python") -> str:
        issues = []
        if "eval(" in code or "exec(" in code:
            issues.append("SECURITY: Avoid eval/exec - potential code injection")
        if "import *" in code:
            issues.append("STYLE: Avoid wildcard imports")
        if "except:" in code and "except Exception" not in code:
            issues.append("STYLE: Avoid bare except clauses")
        if "password" in code.lower() and "=" in code:
            issues.append("SECURITY: Potential hardcoded password detected")
        if not issues:
            return "Code analysis passed - no issues detected"
        return "Code analysis issues:\n" + "\n".join(f"- {i}" for i in issues)


class MCPToolWrapper:
    """Factory for creating MCP-integrated CrewAI tools."""

    @staticmethod
    def get_memory_tools() -> list[BaseTool]:
        """Get memory-related tools."""
        return [MemorySearchTool(), MemoryStoreTool()]

    @staticmethod
    def get_task_tools() -> list[BaseTool]:
        """Get task management tools."""
        return [TaskCreateTool()]

    @staticmethod
    def get_voice_tools() -> list[BaseTool]:
        """Get voice communication tools."""
        return [VoiceAnnounceTool()]

    @staticmethod
    def get_analysis_tools() -> list[BaseTool]:
        """Get code analysis tools."""
        return [CodeAnalysisTool()]

    @staticmethod
    def get_all_tools() -> list[BaseTool]:
        """Get all available MCP tools."""
        return [
            MemorySearchTool(),
            MemoryStoreTool(),
            TaskCreateTool(),
            VoiceAnnounceTool(),
            CodeAnalysisTool(),
        ]
