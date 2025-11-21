"""
Lazy-Load Tool Definition Caching

Instead of loading all 37+ MCP server tool definitions upfront,
this module enables on-demand loading with intelligent caching.

Token Savings:
- Upfront: ~15,000 tokens for all tool definitions
- Lazy: ~200 tokens per actually-used tool
- Typical session uses 5-10 tools = 1,000-2,000 tokens (90%+ reduction)

Architecture:
- Tool definitions stored in filesystem
- LRU cache for frequently used tools
- TTL expiration for staleness prevention
- Preloading hints for common workflows
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from collections import OrderedDict
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


@dataclass
class CachedTool:
    """Cached tool definition with metadata"""
    server: str
    name: str
    schema: Dict[str, Any]
    loaded_at: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)


class LRUToolCache:
    """
    LRU cache for tool definitions with TTL expiration.

    Implements intelligent caching to minimize token usage:
    - Most recently used tools stay in cache
    - Stale definitions auto-expire
    - Access patterns tracked for preloading
    """

    def __init__(self, max_size: int = 50, ttl_seconds: int = 3600):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CachedTool] = OrderedDict()
        self._access_history: List[str] = []
        self._hit_count = 0
        self._miss_count = 0

    def _make_key(self, server: str, tool: str) -> str:
        """Create cache key from server and tool name"""
        return f"{server}/{tool}"

    def get(self, server: str, tool: str) -> Optional[Dict[str, Any]]:
        """Get tool definition from cache"""
        key = self._make_key(server, tool)

        if key in self._cache:
            cached = self._cache[key]

            # Check TTL
            if time.time() - cached.loaded_at > self.ttl_seconds:
                del self._cache[key]
                self._miss_count += 1
                return None

            # Move to end (most recently used)
            self._cache.move_to_end(key)
            cached.access_count += 1
            cached.last_accessed = time.time()

            self._hit_count += 1
            self._access_history.append(key)

            return cached.schema

        self._miss_count += 1
        return None

    def put(self, server: str, tool: str, schema: Dict[str, Any]):
        """Store tool definition in cache"""
        key = self._make_key(server, tool)

        # Evict if at capacity
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)  # Remove oldest

        self._cache[key] = CachedTool(
            server=server,
            name=tool,
            schema=schema,
            loaded_at=time.time()
        )

    def invalidate(self, server: str, tool: Optional[str] = None):
        """Invalidate cached entries"""
        if tool:
            key = self._make_key(server, tool)
            if key in self._cache:
                del self._cache[key]
        else:
            # Invalidate all tools for server
            keys_to_remove = [k for k in self._cache if k.startswith(f"{server}/")]
            for key in keys_to_remove:
                del self._cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._hit_count + self._miss_count
        hit_rate = self._hit_count / total if total > 0 else 0

        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": f"{hit_rate:.1%}",
            "ttl_seconds": self.ttl_seconds
        }

    def get_frequent_tools(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """Get most frequently accessed tools"""
        sorted_tools = sorted(
            self._cache.values(),
            key=lambda t: t.access_count,
            reverse=True
        )[:top_n]

        return [
            {"server": t.server, "tool": t.name, "access_count": t.access_count}
            for t in sorted_tools
        ]


class LazyToolLoader:
    """
    Lazy loader for MCP tool definitions.

    Loads tool definitions on-demand and caches them intelligently.
    """

    def __init__(self, cache_size: int = 50, ttl_seconds: int = 3600):
        self.cache = LRUToolCache(max_size=cache_size, ttl_seconds=ttl_seconds)
        self._tool_registry_dir = Path(__file__).parent.parent / "tool_registry"

        # Workflow preloading hints
        self._workflow_tools: Dict[str, List[str]] = {
            "memory_operations": [
                "enhanced-memory/search_nodes",
                "enhanced-memory/create_entities",
                "enhanced-memory/execute_code",
            ],
            "voice_interaction": [
                "voice-mode/converse",
                "voice-mode/voice_registry",
            ],
            "task_management": [
                "agent-runtime/create_goal",
                "agent-runtime/create_task",
                "agent-runtime/get_next_task",
            ],
            "analysis": [
                "safla-enhanced/analyze_text",
                "safla-enhanced/detect_patterns",
                "enhanced-memory/detect_memory_conflicts",
            ],
        }

    def get_tool_schema(self, server: str, tool: str) -> Optional[Dict[str, Any]]:
        """
        Get tool schema with lazy loading.

        First checks cache, then loads from filesystem if needed.
        """
        # Check cache first
        cached = self.cache.get(server, tool)
        if cached:
            logger.debug(f"Cache hit: {server}/{tool}")
            return cached

        # Load from filesystem
        schema = self._load_from_registry(server, tool)
        if schema:
            self.cache.put(server, tool, schema)
            logger.debug(f"Loaded and cached: {server}/{tool}")

        return schema

    def _load_from_registry(self, server: str, tool: str) -> Optional[Dict[str, Any]]:
        """Load tool schema from registry filesystem"""
        tool_file = self._tool_registry_dir / server / f"{tool}.json"

        if tool_file.exists():
            try:
                return json.loads(tool_file.read_text())
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse {tool_file}: {e}")

        return None

    def preload_workflow(self, workflow_name: str):
        """
        Preload tools for a specific workflow.

        Use when you know which tools will be needed.
        """
        tools = self._workflow_tools.get(workflow_name, [])

        for tool_path in tools:
            parts = tool_path.split("/")
            if len(parts) == 2:
                server, tool = parts
                self.get_tool_schema(server, tool)

        logger.info(f"Preloaded {len(tools)} tools for workflow: {workflow_name}")

    def get_minimal_schema(self, server: str, tool: str) -> Optional[Dict[str, str]]:
        """
        Get minimal schema (name + description only).

        Use for progressive disclosure - first show minimal info,
        then load full schema only if needed.
        """
        full = self.get_tool_schema(server, tool)
        if full:
            return {
                "name": full.get("name", tool),
                "description": full.get("description", "")[:100]
            }
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get loader statistics"""
        return {
            "cache": self.cache.get_stats(),
            "frequent_tools": self.cache.get_frequent_tools(5),
            "available_workflows": list(self._workflow_tools.keys())
        }


# Global loader instance
_loader: Optional[LazyToolLoader] = None


def get_loader() -> LazyToolLoader:
    """Get or create the global lazy loader"""
    global _loader
    if _loader is None:
        _loader = LazyToolLoader()
    return _loader


def lazy_get_schema(server: str, tool: str) -> Optional[Dict[str, Any]]:
    """Convenience function for lazy schema loading"""
    return get_loader().get_tool_schema(server, tool)


def preload_for_workflow(workflow: str):
    """Convenience function for workflow preloading"""
    get_loader().preload_workflow(workflow)


def create_lazy_context() -> Dict[str, Any]:
    """Create lazy loading context for code execution"""
    loader = get_loader()

    return {
        "get_tool_schema": loader.get_tool_schema,
        "get_minimal_schema": loader.get_minimal_schema,
        "preload_workflow": loader.preload_workflow,
        "loader_stats": loader.get_stats,
    }


# Token estimation utilities
def estimate_schema_tokens(schema: Dict[str, Any]) -> int:
    """Estimate tokens for a tool schema"""
    # Rough estimation: 4 chars per token
    json_str = json.dumps(schema)
    return len(json_str) // 4


def estimate_savings(loaded_tools: int, total_tools: int = 150) -> Dict[str, Any]:
    """
    Estimate token savings from lazy loading.

    Args:
        loaded_tools: Number of actually loaded tools
        total_tools: Total available tools (default 150)

    Returns:
        Savings statistics
    """
    avg_tokens_per_tool = 100  # Estimated average

    upfront_cost = total_tools * avg_tokens_per_tool
    lazy_cost = loaded_tools * avg_tokens_per_tool

    saved = upfront_cost - lazy_cost
    percent = (saved / upfront_cost) * 100 if upfront_cost > 0 else 0

    return {
        "upfront_tokens": upfront_cost,
        "lazy_tokens": lazy_cost,
        "tokens_saved": saved,
        "percent_saved": f"{percent:.1f}%",
        "tools_loaded": loaded_tools,
        "tools_available": total_tools
    }
