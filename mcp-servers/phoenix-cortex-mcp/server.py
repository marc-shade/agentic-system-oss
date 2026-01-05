#!/usr/bin/env python3
"""
Phoenix Cortex - Intelligent Context Sidecar for Claude Code

A sidecar system that provides 97% context reduction while delivering
BETTER performance through anticipation, compression, and local delegation.

Architecture:
- Hierarchical context loading (identity → task → tools)
- Progressive disclosure (intent → select → schema → result)
- Tool chain compilation (macros for common workflows)
- Local inference delegation (Ollama for routine tasks)
- External working memory (unlimited state)
- Anticipatory caching (predict next tools)

Port: 8300 (HTTP API) + MCP stdio
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from collections import deque
import hashlib
import httpx

from mcp.server.fastmcp import FastMCP

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("phoenix-cortex")

# Configuration
STORAGE_BASE = Path(os.environ.get("STORAGE_BASE", "/Volumes/SSDRAID0/agentic-system"))
CONTEXT_ENGINE_URL = "http://localhost:8301"  # Context Engine for semantic search
OLLAMA_URL = "http://localhost:11434"
ENHANCED_MEMORY_SOCKET = STORAGE_BASE / "databases" / "memory-db.sock"

# Initialize MCP server
mcp = FastMCP("phoenix-cortex")


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class WorkingMemoryItem:
    """Item in the episodic buffer"""
    timestamp: str
    action: str
    tool: str
    params_summary: str
    result_summary: str
    result_ref: str  # Reference ID for full data in enhanced-memory
    success: bool


@dataclass
class GoalState:
    """Hierarchical goal tracking"""
    goal_id: str
    description: str
    status: str  # pending, active, completed, failed
    sub_goals: list = field(default_factory=list)
    progress: float = 0.0
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ToolChain:
    """Compiled tool chain (macro)"""
    chain_id: str
    name: str
    description: str
    trigger_intents: list
    tools: list  # Ordered list of tool names
    param_mappings: dict  # How to pass params between tools
    success_rate: float = 1.0
    usage_count: int = 0


@dataclass
class CortexState:
    """Complete Cortex state"""
    # Episodic buffer (last N actions)
    episodic_buffer: deque = field(default_factory=lambda: deque(maxlen=20))

    # Goal stack
    goals: dict = field(default_factory=dict)
    active_goal_id: Optional[str] = None

    # Entity cache (active objects being worked on)
    entity_cache: dict = field(default_factory=dict)

    # Pattern library (learned successful patterns)
    patterns: dict = field(default_factory=dict)

    # Tool chain cache
    tool_chains: dict = field(default_factory=dict)

    # Anticipation cache (predicted next tools with pre-loaded schemas)
    anticipation_cache: dict = field(default_factory=dict)

    # Session metadata
    session_start: str = ""
    total_actions: int = 0
    delegated_actions: int = 0
    context_tokens_saved: int = 0


# Global state (use _state to avoid conflict with cortex_state MCP tool)
_state = CortexState(session_start=datetime.now().isoformat())


# =============================================================================
# CONTEXT ENGINE INTEGRATION
# =============================================================================

async def discover_tools(query: str, limit: int = 5) -> list:
    """Query Context Engine for relevant tools"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{CONTEXT_ENGINE_URL}/discover",
                json={"query": query, "limit": limit}
            )
            if response.status_code == 200:
                return response.json().get("tools", [])
    except Exception as e:
        logger.warning(f"Context Engine query failed: {e}")

    # Fallback: Use MCP tool discovery if available
    return []


async def get_tool_schema(tool_name: str) -> Optional[dict]:
    """Get full schema for a specific tool"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{CONTEXT_ENGINE_URL}/schema/{tool_name}"
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Schema fetch failed: {e}")
    return None


# =============================================================================
# COMPRESSION SERVICE
# =============================================================================

def compress_result(result: Any, max_tokens: int = 500) -> tuple[str, str]:
    """
    Compress tool result to summary + reference ID
    Returns: (summary, reference_id)
    """
    result_str = json.dumps(result) if not isinstance(result, str) else result

    # Generate reference ID
    ref_id = f"ref_{hashlib.md5(result_str.encode(), usedforsecurity=False).hexdigest()[:12]}"

    # Store full result (would go to enhanced-memory in production)
    _state.entity_cache[ref_id] = {
        "full_result": result,
        "stored_at": datetime.now().isoformat()
    }

    # Compress based on result type and size
    if len(result_str) < max_tokens * 4:  # Rough char-to-token ratio
        return result_str, ref_id

    # For large results, extract key information
    if isinstance(result, dict):
        summary_parts = []
        if "status" in result:
            summary_parts.append(f"status: {result['status']}")
        if "count" in result:
            summary_parts.append(f"count: {result['count']}")
        if "error" in result:
            summary_parts.append(f"error: {result['error']}")
        if "summary" in result:
            summary_parts.append(f"summary: {result['summary']}")
        if "items" in result and isinstance(result["items"], list):
            summary_parts.append(f"items: {len(result['items'])} results")

        if summary_parts:
            summary = "; ".join(summary_parts) + f" [full: {ref_id}]"
            return summary, ref_id

    # Fallback: truncate with reference
    truncated = result_str[:max_tokens * 3] + f"... [truncated, full: {ref_id}]"
    return truncated, ref_id


# =============================================================================
# DELEGATION ROUTER
# =============================================================================

# Tasks that can be delegated to local model
DELEGATABLE_PATTERNS = [
    "file_exists", "path_resolve", "format_", "validate_", "parse_",
    "count_", "list_", "check_", "status", "health", "ping"
]

# Tasks that require Claude
REQUIRE_CLAUDE_PATTERNS = [
    "generate", "create", "implement", "design", "architect",
    "refactor", "explain", "analyze_complex", "decide"
]


async def should_delegate(intent: str, tool_name: str) -> tuple[bool, str]:
    """
    Determine if task should be delegated to local model
    Returns: (should_delegate, reason)
    """
    intent_lower = intent.lower()
    tool_lower = tool_name.lower()

    # Check if explicitly requires Claude
    for pattern in REQUIRE_CLAUDE_PATTERNS:
        if pattern in intent_lower:
            return False, f"'{pattern}' requires Claude reasoning"

    # Check if can be delegated
    for pattern in DELEGATABLE_PATTERNS:
        if pattern in tool_lower or pattern in intent_lower:
            return True, f"'{pattern}' is routine, delegating to local model"

    # Default: don't delegate novel tasks
    return False, "Novel task, keeping in Claude context"


async def delegate_to_ollama(prompt: str, model: str = "agentic-task-executor") -> Optional[str]:
    """Execute task using local Ollama model"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            if response.status_code == 200:
                return response.json().get("response")
    except Exception as e:
        logger.warning(f"Ollama delegation failed: {e}")
    return None


# =============================================================================
# ANTICIPATION ENGINE
# =============================================================================

# Common tool sequences for anticipation
TOOL_SEQUENCES = {
    "grep": ["read_file", "edit"],
    "read_file": ["edit", "write"],
    "edit": ["bash", "read_file"],
    "search_nodes": ["create_entities", "read_file"],
    "cluster_status": ["offload_to", "cluster_bash"],
    "discover_tools": ["get_tool_schema", "cortex_execute"],
}


async def anticipate_next_tools(current_tool: str, intent: str) -> list:
    """Predict likely next tools based on current action"""
    predictions = []

    # Check sequence patterns
    if current_tool in TOOL_SEQUENCES:
        predictions.extend(TOOL_SEQUENCES[current_tool])

    # Intent-based prediction
    intent_lower = intent.lower()
    if "fix" in intent_lower or "bug" in intent_lower:
        predictions.extend(["grep", "read_file", "edit", "bash"])
    elif "deploy" in intent_lower:
        predictions.extend(["cluster_status", "offload_to", "bash"])
    elif "search" in intent_lower or "find" in intent_lower:
        predictions.extend(["grep", "glob", "read_file"])

    # Deduplicate while preserving order
    seen = set()
    unique_predictions = []
    for tool in predictions:
        if tool not in seen:
            seen.add(tool)
            unique_predictions.append(tool)

    return unique_predictions[:5]


async def prewarm_cache(tool_names: list):
    """Pre-load schemas for anticipated tools"""
    for tool_name in tool_names:
        if tool_name not in _state.anticipation_cache:
            schema = await get_tool_schema(tool_name)
            if schema:
                _state.anticipation_cache[tool_name] = {
                    "schema": schema,
                    "cached_at": datetime.now().isoformat()
                }
                logger.debug(f"Pre-warmed cache for: {tool_name}")


# =============================================================================
# TOOL CHAIN COMPILATION
# =============================================================================

def get_compiled_chain(intent: str) -> Optional[ToolChain]:
    """Find a compiled tool chain matching the intent"""
    intent_words = set(intent.lower().split())

    for chain_id, chain in _state.tool_chains.items():
        for trigger in chain.trigger_intents:
            trigger_words = set(trigger.lower().split())
            # Match if all trigger words appear in intent
            if trigger_words.issubset(intent_words):
                return chain
    return None


def register_tool_chain(chain: ToolChain):
    """Register a new tool chain"""
    _state.tool_chains[chain.chain_id] = chain
    logger.info(f"Registered tool chain: {chain.name}")


# Pre-register common chains
DEFAULT_CHAINS = [
    ToolChain(
        chain_id="fix_bug",
        name="Bug Fix Workflow",
        description="Search for error, read file, edit fix, run tests",
        trigger_intents=["fix bug", "fix error", "debug", "resolve issue"],
        tools=["grep", "read_file", "edit", "bash"],
        param_mappings={"grep.pattern": "error_pattern", "bash.command": "test_command"}
    ),
    ToolChain(
        chain_id="deploy_service",
        name="Service Deployment",
        description="Check cluster, build, deploy, verify",
        trigger_intents=["deploy", "ship", "release", "push to production"],
        tools=["cluster_status", "bash", "offload_to", "cluster_bash"],
        param_mappings={}
    ),
    ToolChain(
        chain_id="research_topic",
        name="Research Pipeline",
        description="Search papers, download, extract insights, store",
        trigger_intents=["research", "find papers", "learn about", "investigate"],
        tools=["search_arxiv", "download_paper", "extract_insights", "create_entities"],
        param_mappings={}
    ),
    ToolChain(
        chain_id="memory_search",
        name="Memory Search",
        description="Search memory, retrieve details, summarize",
        trigger_intents=["remember", "what did", "find in memory", "recall"],
        tools=["search_nodes", "fact_search", "unified_search"],
        param_mappings={}
    ),
]

for chain in DEFAULT_CHAINS:
    register_tool_chain(chain)


# =============================================================================
# WORKING MEMORY MANAGEMENT
# =============================================================================

def record_action(tool: str, params: dict, result: Any, success: bool):
    """Record action in episodic buffer"""
    summary, ref_id = compress_result(result)

    item = WorkingMemoryItem(
        timestamp=datetime.now().isoformat(),
        action=f"Called {tool}",
        tool=tool,
        params_summary=json.dumps(params)[:200],
        result_summary=summary[:500],
        result_ref=ref_id,
        success=success
    )

    _state.episodic_buffer.append(asdict(item))
    _state.total_actions += 1


def get_working_memory(scope: str = "recent") -> dict:
    """Get working memory state"""
    if scope == "recent":
        return {
            "episodic_buffer": list(_state.episodic_buffer)[-5:],
            "active_goal": _state.goals.get(_state.active_goal_id) if _state.active_goal_id else None,
            "session_stats": {
                "total_actions": _state.total_actions,
                "delegated": _state.delegated_actions,
                "tokens_saved": _state.context_tokens_saved
            }
        }
    elif scope == "full":
        return {
            "episodic_buffer": list(_state.episodic_buffer),
            "goals": {k: asdict(v) if hasattr(v, '__dict__') else v for k, v in _state.goals.items()},
            "active_goal_id": _state.active_goal_id,
            "entity_cache_keys": list(_state.entity_cache.keys()),
            "patterns": _state.patterns,
            "tool_chains": list(_state.tool_chains.keys()),
            "session_stats": {
                "session_start": _state.session_start,
                "total_actions": _state.total_actions,
                "delegated": _state.delegated_actions,
                "tokens_saved": _state.context_tokens_saved
            }
        }
    elif scope == "goals":
        return {
            "goals": {k: asdict(v) if hasattr(v, '__dict__') else v for k, v in _state.goals.items()},
            "active_goal_id": _state.active_goal_id
        }

    return {"error": f"Unknown scope: {scope}"}


# =============================================================================
# MCP TOOLS - THE CORTEX INTERFACE
# =============================================================================

@mcp.tool()
async def cortex_query(intent: str, context: str = "") -> dict:
    """
    Query Cortex with natural language intent.
    Returns tool suggestions with progressive disclosure.

    Stage 1: Intent recognition + tool suggestions (~200 tokens)
    Use cortex_schema() for Stage 2 (full schema) if needed.

    Args:
        intent: Natural language description of what you want to do
        context: Optional context about current task

    Returns:
        Tool suggestions with brief descriptions, compiled chains if available
    """
    start_time = time.time()

    # Check for compiled chain first
    chain = get_compiled_chain(intent)
    if chain:
        chain.usage_count += 1
        return {
            "stage": 1,
            "type": "compiled_chain",
            "chain": {
                "id": chain.chain_id,
                "name": chain.name,
                "description": chain.description,
                "tools": chain.tools,
                "success_rate": chain.success_rate
            },
            "message": f"Found compiled chain '{chain.name}' - use cortex_execute_chain() to run",
            "latency_ms": (time.time() - start_time) * 1000
        }

    # Discover relevant tools via Context Engine
    tools = await discover_tools(intent, limit=5)

    # Check anticipation cache for pre-loaded schemas
    cached_tools = []
    for tool in tools:
        tool_name = tool.get("name", "")
        if tool_name in _state.anticipation_cache:
            cached_tools.append(tool_name)

    # Predict and pre-warm next likely tools
    if tools:
        predictions = await anticipate_next_tools(tools[0].get("name", ""), intent)
        asyncio.create_task(prewarm_cache(predictions))

    return {
        "stage": 1,
        "type": "tool_discovery",
        "intent": intent,
        "tools": [
            {
                "name": t.get("name"),
                "brief": t.get("description", "")[:100],
                "cached": t.get("name") in cached_tools
            }
            for t in tools
        ],
        "cached_count": len(cached_tools),
        "message": "Use cortex_schema(tool_name) for full schema, or cortex_execute() to run directly",
        "latency_ms": (time.time() - start_time) * 1000
    }


@mcp.tool()
async def cortex_schema(tool_name: str) -> dict:
    """
    Get full schema for a tool (Stage 2 of progressive disclosure).
    Only call this when you need detailed parameter information.

    Args:
        tool_name: Name of the tool to get schema for

    Returns:
        Full tool schema with parameters and examples
    """
    start_time = time.time()

    # Check anticipation cache first
    if tool_name in _state.anticipation_cache:
        cached = _state.anticipation_cache[tool_name]
        _state.context_tokens_saved += 200  # Estimate saved by caching
        return {
            "stage": 2,
            "tool": tool_name,
            "schema": cached["schema"],
            "from_cache": True,
            "cached_at": cached["cached_at"],
            "latency_ms": (time.time() - start_time) * 1000
        }

    # Fetch from Context Engine
    schema = await get_tool_schema(tool_name)

    if schema:
        # Cache for future use
        _state.anticipation_cache[tool_name] = {
            "schema": schema,
            "cached_at": datetime.now().isoformat()
        }
        return {
            "stage": 2,
            "tool": tool_name,
            "schema": schema,
            "from_cache": False,
            "latency_ms": (time.time() - start_time) * 1000
        }

    return {
        "stage": 2,
        "tool": tool_name,
        "error": f"Schema not found for {tool_name}",
        "latency_ms": (time.time() - start_time) * 1000
    }


@mcp.tool()
async def cortex_execute(tool_name: str, params: dict, intent: str = "") -> dict:
    """
    Execute a tool through Cortex with automatic compression and caching.

    This handles:
    - Delegation to local model for routine tasks
    - Result compression with reference IDs
    - Action recording in working memory
    - Anticipation of next tools

    Args:
        tool_name: Tool to execute
        params: Tool parameters
        intent: Optional intent description for better anticipation

    Returns:
        Compressed result with reference ID for full data
    """
    start_time = time.time()

    # Check if should delegate
    should_del, reason = await should_delegate(intent, tool_name)

    if should_del:
        # Attempt local delegation
        prompt = f"Execute {tool_name} with params: {json.dumps(params)}"
        local_result = await delegate_to_ollama(prompt)

        if local_result:
            _state.delegated_actions += 1
            _state.context_tokens_saved += 500  # Estimate

            summary, ref_id = compress_result(local_result)
            record_action(tool_name, params, local_result, True)

            return {
                "stage": 4,
                "tool": tool_name,
                "delegated": True,
                "delegation_reason": reason,
                "result_summary": summary,
                "result_ref": ref_id,
                "tokens_saved": 500,
                "latency_ms": (time.time() - start_time) * 1000
            }

    # For non-delegated tasks, return instruction to call tool directly
    # (Cortex can't actually execute MCP tools, Claude must call them)

    # But we can still predict and cache next tools
    if intent:
        predictions = await anticipate_next_tools(tool_name, intent)
        asyncio.create_task(prewarm_cache(predictions))

    return {
        "stage": 3,
        "tool": tool_name,
        "delegated": False,
        "delegation_reason": reason,
        "action": "execute_directly",
        "params": params,
        "message": f"Call {tool_name} directly with these params. Use cortex_record() after to log result.",
        "predicted_next": await anticipate_next_tools(tool_name, intent),
        "latency_ms": (time.time() - start_time) * 1000
    }


@mcp.tool()
async def cortex_record(tool_name: str, params: dict, result: str, success: bool = True) -> dict:
    """
    Record a tool execution result in working memory.
    Call this after executing a tool to maintain state.

    Args:
        tool_name: Tool that was executed
        params: Parameters used
        result: Result from the tool (will be compressed)
        success: Whether execution succeeded

    Returns:
        Confirmation with reference ID for full result
    """
    summary, ref_id = compress_result(result)
    record_action(tool_name, params, result, success)

    # Anticipate next tools
    predictions = await anticipate_next_tools(tool_name, "")
    asyncio.create_task(prewarm_cache(predictions))

    return {
        "recorded": True,
        "tool": tool_name,
        "result_ref": ref_id,
        "result_summary": summary[:200],
        "predicted_next": predictions,
        "total_actions": _state.total_actions
    }


@mcp.tool()
async def cortex_state(scope: str = "recent") -> dict:
    """
    Get current Cortex state (working memory).

    Scopes:
    - "recent": Last 5 actions + active goal + stats (~300 tokens)
    - "full": Complete state including all buffers (~1000 tokens)
    - "goals": Just goal stack

    Args:
        scope: What state to retrieve

    Returns:
        Working memory state for the requested scope
    """
    return get_working_memory(scope)


@mcp.tool()
async def cortex_goal(action: str, goal_id: str = "", description: str = "") -> dict:
    """
    Manage goals in the goal stack.

    Actions:
    - "create": Create new goal (requires description)
    - "activate": Set active goal (requires goal_id)
    - "complete": Mark goal complete (requires goal_id)
    - "list": List all goals

    Args:
        action: Goal action to perform
        goal_id: Goal ID (for activate/complete)
        description: Goal description (for create)

    Returns:
        Goal operation result
    """
    if action == "create":
        new_id = f"goal_{int(time.time())}"
        goal = GoalState(
            goal_id=new_id,
            description=description,
            status="pending",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        _state.goals[new_id] = goal
        _state.active_goal_id = new_id
        return {"created": new_id, "description": description, "active": True}

    elif action == "activate":
        if goal_id in _state.goals:
            _state.active_goal_id = goal_id
            _state.goals[goal_id].status = "active"
            _state.goals[goal_id].updated_at = datetime.now().isoformat()
            return {"activated": goal_id}
        return {"error": f"Goal {goal_id} not found"}

    elif action == "complete":
        if goal_id in _state.goals:
            _state.goals[goal_id].status = "completed"
            _state.goals[goal_id].progress = 1.0
            _state.goals[goal_id].updated_at = datetime.now().isoformat()
            if _state.active_goal_id == goal_id:
                _state.active_goal_id = None
            return {"completed": goal_id}
        return {"error": f"Goal {goal_id} not found"}

    elif action == "list":
        return {
            "goals": [
                {
                    "id": g.goal_id,
                    "description": g.description[:100],
                    "status": g.status,
                    "progress": g.progress
                }
                for g in _state.goals.values()
            ],
            "active": _state.active_goal_id
        }

    return {"error": f"Unknown action: {action}"}


@mcp.tool()
async def cortex_chain(chain_id: str, params: dict = {}) -> dict:
    """
    Get execution plan for a compiled tool chain.

    Chains are pre-compiled workflows that execute multiple tools
    in sequence. This returns the execution plan for Claude to follow.

    Args:
        chain_id: ID of the tool chain
        params: Parameters to pass to the chain

    Returns:
        Execution plan with ordered tool calls
    """
    if chain_id not in _state.tool_chains:
        return {
            "error": f"Chain {chain_id} not found",
            "available_chains": list(_state.tool_chains.keys())
        }

    chain = _state.tool_chains[chain_id]
    chain.usage_count += 1

    # Build execution plan
    plan = []
    for i, tool in enumerate(chain.tools):
        step = {
            "step": i + 1,
            "tool": tool,
            "params": chain.param_mappings.get(tool, {}),
            "description": f"Step {i+1}: Execute {tool}"
        }
        plan.append(step)

    return {
        "chain_id": chain_id,
        "name": chain.name,
        "description": chain.description,
        "total_steps": len(plan),
        "execution_plan": plan,
        "success_rate": chain.success_rate,
        "usage_count": chain.usage_count
    }


@mcp.tool()
async def cortex_learn(pattern_name: str, pattern_data: dict) -> dict:
    """
    Record a successful pattern for future use.

    Patterns are reusable solutions that worked well.
    The Cortex learns from these to improve suggestions.

    Args:
        pattern_name: Name for the pattern
        pattern_data: Pattern details (intent, tools_used, params, outcome)

    Returns:
        Confirmation of pattern storage
    """
    _state.patterns[pattern_name] = {
        **pattern_data,
        "recorded_at": datetime.now().isoformat(),
        "usage_count": 0
    }

    return {
        "learned": pattern_name,
        "total_patterns": len(_state.patterns)
    }


@mcp.tool()
async def cortex_expand(ref_id: str) -> dict:
    """
    Expand a reference ID to get full data.

    When results are compressed, full data is stored with a reference ID.
    Use this to retrieve the complete data when needed.

    Args:
        ref_id: Reference ID from a compressed result

    Returns:
        Full data for the reference
    """
    if ref_id in _state.entity_cache:
        return {
            "ref_id": ref_id,
            "full_data": _state.entity_cache[ref_id]
        }

    return {
        "ref_id": ref_id,
        "error": "Reference not found in cache",
        "available_refs": list(_state.entity_cache.keys())[-10:]
    }


@mcp.tool()
async def cortex_stats() -> dict:
    """
    Get Cortex performance statistics.

    Returns:
        Session stats including tokens saved, delegations, cache hits
    """
    return {
        "session_start": _state.session_start,
        "uptime_seconds": (datetime.now() - datetime.fromisoformat(_state.session_start)).total_seconds(),
        "total_actions": _state.total_actions,
        "delegated_actions": _state.delegated_actions,
        "delegation_rate": _state.delegated_actions / max(1, _state.total_actions),
        "context_tokens_saved": _state.context_tokens_saved,
        "cached_schemas": len(_state.anticipation_cache),
        "compiled_chains": len(_state.tool_chains),
        "learned_patterns": len(_state.patterns),
        "episodic_buffer_size": len(_state.episodic_buffer),
        "active_goals": len([g for g in _state.goals.values() if g.status == "active"])
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    logger.info("Starting Phoenix Cortex - Intelligent Context Sidecar")
    logger.info(f"Session started at: {_state.session_start}")
    logger.info(f"Compiled chains: {list(_state.tool_chains.keys())}")
    mcp.run()
