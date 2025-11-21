"""
Progressive Tool Discovery System

Implements Anthropic's file tree pattern for on-demand tool loading.
Instead of loading all tool definitions upfront, agents explore a filesystem.

Token Savings: ~90% reduction (2000 -> 200 tokens for tool discovery)

Architecture:
    servers/
    ├── enhanced-memory/
    │   ├── search_nodes.json      (schema)
    │   ├── create_entities.json
    │   └── index.json             (list of tools)
    ├── voice-mode/
    │   ├── converse.json
    │   └── index.json
    └── agent-runtime/
        ├── create_goal.json
        └── index.json
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)

# Tool registry directory (created on first use)
TOOL_REGISTRY_DIR = Path(__file__).parent.parent / "tool_registry"


@dataclass
class ToolSchema:
    """Lightweight tool schema for progressive disclosure"""
    name: str
    server: str
    description: str
    parameters: Dict[str, Any]
    returns: Optional[str] = None
    examples: Optional[List[str]] = None
    cost_estimate: Optional[str] = None  # e.g., "low", "medium", "high"


# Known MCP servers and their tools (cached schemas)
MCP_TOOL_REGISTRY: Dict[str, List[Dict[str, Any]]] = {
    "enhanced-memory": [
        {
            "name": "create_entities",
            "description": "Create entities with compression and versioning",
            "parameters": {"entities": "List[Dict] - entities with name, entityType, observations"},
            "returns": "Dict with created count and results",
            "cost_estimate": "medium"
        },
        {
            "name": "search_nodes",
            "description": "Search entities by name or type",
            "parameters": {"query": "str", "limit": "int = 10"},
            "returns": "Dict with matching entities",
            "cost_estimate": "low"
        },
        {
            "name": "execute_code",
            "description": "Execute Python code in sandbox with memory APIs",
            "parameters": {"code": "str", "context_vars": "Optional[Dict]"},
            "returns": "Execution result with stdout/stderr",
            "cost_estimate": "medium"
        },
        {
            "name": "memory_diff",
            "description": "Get diff between entity versions",
            "parameters": {"entity_name": "str", "version1": "int", "version2": "int"},
            "returns": "Unified diff between versions",
            "cost_estimate": "low"
        },
        {
            "name": "memory_branch",
            "description": "Create experimental branch of entity",
            "parameters": {"entity_name": "str", "branch_name": "str"},
            "returns": "Branch creation result",
            "cost_estimate": "low"
        },
        {
            "name": "detect_memory_conflicts",
            "description": "Find duplicate/conflicting memories",
            "parameters": {"threshold": "float = 0.85"},
            "returns": "List of detected conflicts",
            "cost_estimate": "high"
        },
    ],
    "voice-mode": [
        {
            "name": "converse",
            "description": "Speak message and optionally listen for response",
            "parameters": {
                "message": "str - text to speak",
                "wait_for_response": "bool = True",
                "voice": "Optional[str] - TTS voice",
                "tts_provider": "Optional[str] - openai or kokoro"
            },
            "returns": "Voice response or confirmation",
            "cost_estimate": "medium"
        },
        {
            "name": "voice_registry",
            "description": "Get available voice providers and voices",
            "parameters": {},
            "returns": "Registry of TTS/STT endpoints",
            "cost_estimate": "low"
        },
    ],
    "agent-runtime": [
        {
            "name": "create_goal",
            "description": "Create persistent goal that survives sessions",
            "parameters": {"name": "str", "description": "str"},
            "returns": "Goal ID and metadata",
            "cost_estimate": "low"
        },
        {
            "name": "decompose_goal",
            "description": "AI-powered goal decomposition into tasks",
            "parameters": {"goal_id": "int", "strategy": "str = sequential"},
            "returns": "List of created task IDs",
            "cost_estimate": "high"
        },
        {
            "name": "create_task",
            "description": "Create manual task in queue",
            "parameters": {"title": "str", "description": "str", "priority": "int = 5"},
            "returns": "Task ID and metadata",
            "cost_estimate": "low"
        },
        {
            "name": "get_next_task",
            "description": "Get highest priority task with met dependencies",
            "parameters": {},
            "returns": "Next task or null",
            "cost_estimate": "low"
        },
    ],
    "sequential-thinking": [
        {
            "name": "sequentialthinking",
            "description": "Multi-step reasoning with revision capability",
            "parameters": {
                "thought": "str - current thinking step",
                "thoughtNumber": "int",
                "totalThoughts": "int",
                "nextThoughtNeeded": "bool"
            },
            "returns": "Reasoning chain state",
            "cost_estimate": "medium"
        },
    ],
    "safla-enhanced": [
        {
            "name": "generate_embeddings",
            "description": "Generate embeddings (1.75M+ ops/sec)",
            "parameters": {"texts": "List[str]"},
            "returns": "Embedding vectors",
            "cost_estimate": "low"
        },
        {
            "name": "store_memory",
            "description": "Store in SAFLA hybrid memory",
            "parameters": {"content": "str", "memory_type": "str = episodic"},
            "returns": "Storage confirmation",
            "cost_estimate": "low"
        },
        {
            "name": "retrieve_memories",
            "description": "Search SAFLA memory system",
            "parameters": {"query": "str", "limit": "int = 5"},
            "returns": "Matching memories",
            "cost_estimate": "low"
        },
        {
            "name": "analyze_text",
            "description": "Deep semantic analysis with entities/sentiment",
            "parameters": {"text": "str", "analysis_type": "str = all"},
            "returns": "Analysis results",
            "cost_estimate": "medium"
        },
        {
            "name": "detect_patterns",
            "description": "Find anomalies, trends, correlations",
            "parameters": {"data": "array", "pattern_type": "str = all"},
            "returns": "Detected patterns",
            "cost_estimate": "high"
        },
    ],
    "arduino-surface": [
        {
            "name": "surface_display",
            "description": "Write text to LCD display",
            "parameters": {"row": "int 0-1", "col": "int 0-15", "text": "str max 16"},
            "returns": "Confirmation",
            "cost_estimate": "low"
        },
        {
            "name": "surface_led_set",
            "description": "Set RGB LED color",
            "parameters": {"tier": "int = 0", "r": "int 0-255", "g": "int", "b": "int"},
            "returns": "Confirmation",
            "cost_estimate": "low"
        },
        {
            "name": "surface_alert",
            "description": "Play alert pattern (success/warning/error/info)",
            "parameters": {"type": "str"},
            "returns": "Confirmation",
            "cost_estimate": "low"
        },
    ],
}


def init_tool_registry():
    """Initialize tool registry filesystem structure"""
    TOOL_REGISTRY_DIR.mkdir(parents=True, exist_ok=True)

    for server_name, tools in MCP_TOOL_REGISTRY.items():
        server_dir = TOOL_REGISTRY_DIR / server_name
        server_dir.mkdir(exist_ok=True)

        # Create index.json with tool list
        index = {
            "server": server_name,
            "tool_count": len(tools),
            "tools": [t["name"] for t in tools]
        }
        (server_dir / "index.json").write_text(json.dumps(index, indent=2))

        # Create individual tool schema files
        for tool in tools:
            tool_file = server_dir / f"{tool['name']}.json"
            tool_file.write_text(json.dumps(tool, indent=2))

    logger.info(f"Tool registry initialized at {TOOL_REGISTRY_DIR}")


def list_servers() -> List[str]:
    """List available MCP servers (directory names)"""
    if not TOOL_REGISTRY_DIR.exists():
        init_tool_registry()
    return [d.name for d in TOOL_REGISTRY_DIR.iterdir() if d.is_dir()]


def list_tools(server: str) -> List[str]:
    """List tools for a server (names only - minimal tokens)"""
    server_dir = TOOL_REGISTRY_DIR / server
    if not server_dir.exists():
        return []

    index_file = server_dir / "index.json"
    if index_file.exists():
        index = json.loads(index_file.read_text())
        return index.get("tools", [])
    return []


def get_tool_schema(server: str, tool: str) -> Optional[Dict[str, Any]]:
    """Get full schema for a specific tool (on-demand loading)"""
    tool_file = TOOL_REGISTRY_DIR / server / f"{tool}.json"
    if tool_file.exists():
        return json.loads(tool_file.read_text())
    return None


def search_tools(query: str, detail_level: str = "names") -> Dict[str, Any]:
    """
    Search for tools matching query across all servers.

    Progressive disclosure levels:
    - "names": Just tool names (minimal tokens)
    - "brief": Names + one-line descriptions
    - "full": Complete schemas (use sparingly)

    Args:
        query: Search term (matches name or description)
        detail_level: How much detail to return

    Returns:
        Matching tools with requested detail level
    """
    if not TOOL_REGISTRY_DIR.exists():
        init_tool_registry()

    query_lower = query.lower()
    matches = []

    for server_name, tools in MCP_TOOL_REGISTRY.items():
        for tool in tools:
            name_match = query_lower in tool["name"].lower()
            desc_match = query_lower in tool["description"].lower()

            if name_match or desc_match:
                if detail_level == "names":
                    matches.append(f"{server_name}/{tool['name']}")
                elif detail_level == "brief":
                    matches.append({
                        "path": f"{server_name}/{tool['name']}",
                        "description": tool["description"][:80]
                    })
                else:  # full
                    matches.append({
                        "server": server_name,
                        **tool
                    })

    return {
        "query": query,
        "detail_level": detail_level,
        "count": len(matches),
        "matches": matches
    }


def get_tool_cost_estimate(server: str, tool: str) -> str:
    """Get estimated cost/complexity of a tool call"""
    schema = get_tool_schema(server, tool)
    if schema:
        return schema.get("cost_estimate", "unknown")
    return "unknown"


# API functions for code execution context
def search_tools_api(query: str, detail: str = "brief") -> Dict[str, Any]:
    """Search tools API for code execution context"""
    return search_tools(query, detail)


def list_servers_api() -> List[str]:
    """List servers API for code execution context"""
    return list_servers()


def list_tools_api(server: str) -> List[str]:
    """List tools API for code execution context"""
    return list_tools(server)


def get_schema_api(server: str, tool: str) -> Optional[Dict]:
    """Get schema API for code execution context"""
    return get_tool_schema(server, tool)


# Initialize on import
if not TOOL_REGISTRY_DIR.exists():
    try:
        init_tool_registry()
    except Exception as e:
        logger.warning(f"Failed to initialize tool registry: {e}")
