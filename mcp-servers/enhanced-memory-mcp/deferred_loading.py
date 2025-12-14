#!/usr/bin/env python3
"""
Deferred Tool Loading Configuration

Based on Anthropic's Advanced Tool Use Pattern (Nov 2025)

This module configures which tools are loaded immediately vs deferred:
- HOT tools: Always loaded (essential for every session)
- WARM tools: Loaded when category is accessed
- COLD tools: Loaded only on explicit search/request

Benefits:
- Reduces initial context window usage by ~89%
- Allows 100+ tools without token bloat
- Enables on-demand capability expansion
"""

from typing import Dict, List, Set, Any
from dataclasses import dataclass
from enum import Enum

class LoadingStrategy(Enum):
    IMMEDIATE = "immediate"     # Load at server startup
    ON_CATEGORY = "on_category" # Load when category accessed
    ON_DEMAND = "on_demand"     # Load only on explicit request

@dataclass
class ModuleConfig:
    """Configuration for a tool module"""
    module_name: str
    loading_strategy: LoadingStrategy
    tools_count: int
    estimated_tokens: int
    description: str

# =============================================================================
# MODULE LOADING CONFIGURATION
# =============================================================================

MODULE_CONFIGS: Dict[str, ModuleConfig] = {
    # IMMEDIATE (HOT) - Always loaded
    "server": ModuleConfig(
        module_name="server",
        loading_strategy=LoadingStrategy.IMMEDIATE,
        tools_count=9,
        estimated_tokens=1800,
        description="Core memory operations: create, search, version control"
    ),
    "tool_search": ModuleConfig(
        module_name="tool_search",
        loading_strategy=LoadingStrategy.IMMEDIATE,
        tools_count=3,
        estimated_tokens=600,
        description="Meta-tools for discovering other tools"
    ),
    "nmf_core": ModuleConfig(
        module_name="nmf_tools",
        loading_strategy=LoadingStrategy.IMMEDIATE,
        tools_count=3,  # Just nmf_recall, nmf_remember, nmf_get_status
        estimated_tokens=600,
        description="Neural Memory Fabric core operations"
    ),
    "cluster_status": ModuleConfig(
        module_name="cluster_brain_tools",
        loading_strategy=LoadingStrategy.IMMEDIATE,
        tools_count=1,  # Just cluster_brain_status
        estimated_tokens=200,
        description="Cluster health and status"
    ),

    # ON_CATEGORY (WARM) - Loaded when category accessed
    "agi_core": ModuleConfig(
        module_name="agi_tools",
        loading_strategy=LoadingStrategy.ON_CATEGORY,
        tools_count=15,
        estimated_tokens=3000,
        description="Core AGI: memory tiers, sessions, action tracking"
    ),
    "cluster_full": ModuleConfig(
        module_name="cluster_brain_tools",
        loading_strategy=LoadingStrategy.ON_CATEGORY,
        tools_count=10,
        estimated_tokens=2000,
        description="Full cluster operations: knowledge, goals, learning"
    ),
    "rag_tools": ModuleConfig(
        module_name="reranking_tools",
        loading_strategy=LoadingStrategy.ON_CATEGORY,
        tools_count=6,
        estimated_tokens=1200,
        description="RAG optimization: reranking, hybrid search, query expansion"
    ),

    # ON_DEMAND (COLD) - Loaded only on explicit request
    "agi_phase2": ModuleConfig(
        module_name="agi_tools_phase2",
        loading_strategy=LoadingStrategy.ON_DEMAND,
        tools_count=12,
        estimated_tokens=2400,
        description="Belief tracking, counterfactual testing"
    ),
    "agi_phase3": ModuleConfig(
        module_name="agi_tools_phase3",
        loading_strategy=LoadingStrategy.ON_DEMAND,
        tools_count=15,
        estimated_tokens=3000,
        description="Causal reasoning, emotional tagging, associations"
    ),
    "agi_phase4": ModuleConfig(
        module_name="agi_tools_phase4",
        loading_strategy=LoadingStrategy.ON_DEMAND,
        tools_count=12,
        estimated_tokens=2400,
        description="Metacognition, self-improvement cycles"
    ),
    "pysr": ModuleConfig(
        module_name="pysr_tools",
        loading_strategy=LoadingStrategy.ON_DEMAND,
        tools_count=15,
        estimated_tokens=3000,
        description="Symbolic regression for equation discovery"
    ),
    "letta": ModuleConfig(
        module_name="letta_tools",
        loading_strategy=LoadingStrategy.ON_DEMAND,
        tools_count=11,
        estimated_tokens=2200,
        description="Letta-style memory blocks"
    ),
    "safla": ModuleConfig(
        module_name="safla_tools",
        loading_strategy=LoadingStrategy.ON_DEMAND,
        tools_count=11,
        estimated_tokens=2200,
        description="SAFLA hybrid memory architecture"
    ),
    "mirror_mind": ModuleConfig(
        module_name="mirror_mind_enhancements",
        loading_strategy=LoadingStrategy.ON_DEMAND,
        tools_count=8,
        estimated_tokens=1600,
        description="Knowledge graph centrality, dual manifold"
    ),
    "sleeptime": ModuleConfig(
        module_name="sleeptime_tools",
        loading_strategy=LoadingStrategy.ON_DEMAND,
        tools_count=4,
        estimated_tokens=800,
        description="Sleep-time consolidation and compression"
    ),
}

# =============================================================================
# LOADING STATISTICS
# =============================================================================

def get_loading_stats() -> Dict[str, Any]:
    """Get statistics about tool loading configuration"""
    immediate = [m for m in MODULE_CONFIGS.values() if m.loading_strategy == LoadingStrategy.IMMEDIATE]
    on_category = [m for m in MODULE_CONFIGS.values() if m.loading_strategy == LoadingStrategy.ON_CATEGORY]
    on_demand = [m for m in MODULE_CONFIGS.values() if m.loading_strategy == LoadingStrategy.ON_DEMAND]

    immediate_tokens = sum(m.estimated_tokens for m in immediate)
    on_category_tokens = sum(m.estimated_tokens for m in on_category)
    on_demand_tokens = sum(m.estimated_tokens for m in on_demand)
    total_tokens = immediate_tokens + on_category_tokens + on_demand_tokens

    return {
        "immediate": {
            "modules": len(immediate),
            "tools": sum(m.tools_count for m in immediate),
            "tokens": immediate_tokens,
        },
        "on_category": {
            "modules": len(on_category),
            "tools": sum(m.tools_count for m in on_category),
            "tokens": on_category_tokens,
        },
        "on_demand": {
            "modules": len(on_demand),
            "tools": sum(m.tools_count for m in on_demand),
            "tokens": on_demand_tokens,
        },
        "total_tools": sum(m.tools_count for m in MODULE_CONFIGS.values()),
        "total_tokens_if_all_loaded": total_tokens,
        "tokens_with_deferred": immediate_tokens,
        "token_reduction": f"{((total_tokens - immediate_tokens) / total_tokens * 100):.1f}%",
    }

def get_modules_by_strategy(strategy: LoadingStrategy) -> List[str]:
    """Get list of module names for a loading strategy"""
    return [
        name for name, config in MODULE_CONFIGS.items()
        if config.loading_strategy == strategy
    ]

def should_load_module(module_name: str, accessed_categories: Set[str]) -> bool:
    """Determine if a module should be loaded based on current context"""
    if module_name not in MODULE_CONFIGS:
        return True  # Unknown modules load immediately

    config = MODULE_CONFIGS[module_name]

    if config.loading_strategy == LoadingStrategy.IMMEDIATE:
        return True

    if config.loading_strategy == LoadingStrategy.ON_CATEGORY:
        # Map modules to categories
        category_map = {
            "agi_core": {"memory", "agent", "learning"},
            "cluster_full": {"cluster"},
            "rag_tools": {"memory", "retrieval"},
        }
        required_cats = category_map.get(module_name, set())
        return bool(required_cats & accessed_categories)

    return False  # ON_DEMAND requires explicit request

# =============================================================================
# HOT TOOL DEFINITIONS (always in context)
# =============================================================================

HOT_TOOL_DEFINITIONS = """
## Always-Available Tools (HOT Tier)

### create_entities
Create entities with compression, versioning, and contextual enrichment.
Parameters: entities (list of {name, entityType, observations})

### search_nodes
Search for entities by name or type with version history.
Parameters: query (string), limit (int, default 10)

### execute_code
Execute Python code in secure sandbox with API access.
Parameters: code (string), context_vars (optional dict)
APIs: search_nodes, create_entities, filter_by_confidence, summarize_results

### nmf_recall
Retrieve memories with semantic, graph, temporal, or hybrid modes.
Parameters: query (string), mode (semantic|graph|temporal|hybrid), limit

### nmf_remember
Store new memory in Neural Memory Fabric.
Parameters: content (string), tags (list), metadata (dict)

### cluster_brain_status
Get cluster-wide status: knowledge, goals, learnings across all nodes.
Parameters: none

### record_action_outcome
Record action and outcome for learning.
Parameters: action_type, action_description, expected_result, actual_result, success_score

### tool_search
Find relevant tools based on what you want to accomplish.
Parameters: query (string), limit (int), category (optional)

### tool_info
Get detailed info about a specific tool.
Parameters: tool_name (string)

### list_tool_categories
List all tool categories and subcategories.
Parameters: none
"""

if __name__ == "__main__":
    stats = get_loading_stats()
    print("Deferred Loading Configuration\n" + "="*50)
    print(f"\nIMMEDIATE (always loaded):")
    print(f"  Modules: {stats['immediate']['modules']}")
    print(f"  Tools: {stats['immediate']['tools']}")
    print(f"  Tokens: {stats['immediate']['tokens']}")

    print(f"\nON_CATEGORY (loaded on access):")
    print(f"  Modules: {stats['on_category']['modules']}")
    print(f"  Tools: {stats['on_category']['tools']}")
    print(f"  Tokens: {stats['on_category']['tokens']}")

    print(f"\nON_DEMAND (loaded explicitly):")
    print(f"  Modules: {stats['on_demand']['modules']}")
    print(f"  Tools: {stats['on_demand']['tools']}")
    print(f"  Tokens: {stats['on_demand']['tokens']}")

    print(f"\n" + "="*50)
    print(f"TOTAL TOOLS: {stats['total_tools']}")
    print(f"ALL TOKENS: {stats['total_tokens_if_all_loaded']}")
    print(f"DEFERRED TOKENS: {stats['tokens_with_deferred']}")
    print(f"TOKEN REDUCTION: {stats['token_reduction']}")
