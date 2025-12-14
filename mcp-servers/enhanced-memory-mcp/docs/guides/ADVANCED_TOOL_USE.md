# Advanced Tool Use Implementation

Based on Anthropic's Advanced Tool Use patterns (November 2025).

## Overview

This implementation reduces context window usage by **88%** through:

1. **Tool Search Tool**: On-demand discovery instead of loading all 100+ tools upfront
2. **Deferred Loading**: HOT/WARM/COLD tier system for tool loading
3. **Programmatic Calling**: Batch operations via secure `execute_code` sandbox
4. **Tool Examples**: Realistic examples for better model understanding

## Token Savings

| Configuration | Tokens | % of Context |
|--------------|--------|--------------|
| All tools loaded | ~27,000 | 27% of 100k |
| With deferred loading | ~3,200 | 3.2% of 100k |
| **Reduction** | **88.1%** | **24% saved** |

## Components

### 1. Tool Catalog (`tool_catalog.py`)

Complete registry of all 61+ enhanced-memory tools with:
- Tier assignment (HOT/WARM/COLD)
- Category/subcategory organization
- Searchable keywords
- Usage examples

```python
from tool_catalog import TOOL_CATALOG, get_tools_by_tier, ToolTier

# Get always-loaded tools
hot_tools = get_tools_by_tier(ToolTier.HOT)
```

### 2. Tool Search (`tool_search.py`)

Meta-tool for discovering relevant tools on demand:

```python
# Instead of loading 100+ tools, use search:
results = await tool_search(
    query="store a new memory about Python patterns",
    limit=5,
    category="memory"
)
# Returns: [create_entities, nmf_remember, add_concept, ...]
```

### 3. Deferred Loading (`deferred_loading.py`)

Configuration for which modules load when:

| Strategy | When Loaded | Example Modules |
|----------|-------------|-----------------|
| IMMEDIATE | Server startup | server, tool_search, nmf_core |
| ON_CATEGORY | Category accessed | agi_core, rag_tools |
| ON_DEMAND | Explicit request | pysr, letta, safla, mirror_mind |

### 4. Execute Code Sandbox

For programmatic batch operations:

```python
# Instead of 10 separate tool calls:
await execute_code("""
results = search_nodes("optimization", limit=100)
high_conf = filter_by_confidence(results, 0.8)
for item in high_conf:
    update_salience(item['id'], 0.1, "high relevance")
result = summarize_results(high_conf)
""")
# Returns: Single JSON result
```

## Usage Patterns

### Pattern 1: Tool Discovery

```
User: "I want to track how my beliefs change over time"

Model: [Uses tool_search("track beliefs changes")]
       → Finds: record_belief_state, update_belief_probability,
                get_belief_revision_history

Model: [Uses specific tools found]
```

### Pattern 2: Category Loading

```
User: "Help me with cluster coordination"

Model: [Uses list_tool_categories()]
       → Sees cluster category with 11 tools

Model: [Uses tool_search(category="cluster")]
       → Loads only cluster-related tools
```

### Pattern 3: Batch Operations

```
User: "Search all memories about APIs and update their importance"

Model: [Uses execute_code for batch processing]
       → Single sandbox execution instead of N tool calls
       → Returns summarized result
```

## Always-Available Tools (HOT Tier)

These 10 tools are always loaded:

1. `create_entities` - Store new memories
2. `search_nodes` - Search memories
3. `get_memory_status` - System health
4. `execute_code` - Batch operations
5. `nmf_recall` - Neural memory retrieval
6. `nmf_remember` - Neural memory storage
7. `cluster_brain_status` - Cluster health
8. `record_action_outcome` - Learning from actions
9. `search_with_reranking` - Precision search
10. `add_episode` - Episodic memory

Plus 3 meta-tools:
- `tool_search` - Find relevant tools
- `tool_info` - Get tool details
- `list_tool_categories` - Browse categories

## Security

The `execute_code` sandbox provides:

- **RestrictedPython** compilation
- **30-second timeout** limits
- **500MB memory** limits
- **Safe built-ins** only
- **Blocked dangerous imports** (os, subprocess, etc.)
- **Full stdout/stderr** capture

## Testing

```bash
cd /mnt/agentic-system/mcp-servers/enhanced-memory-mcp
python3 test_advanced_tool_use.py
```

## Files

| File | Purpose |
|------|---------|
| `tool_catalog.py` | Complete tool registry with tiers |
| `tool_search.py` | Search meta-tool implementation |
| `deferred_loading.py` | Loading strategy configuration |
| `sandbox/executor.py` | Secure code execution |
| `sandbox/security.py` | Safety checks |
| `test_advanced_tool_use.py` | Validation tests |

## References

- Anthropic Advanced Tool Use (Nov 2025)
- Agency Swarm MCP implementation
- RestrictedPython documentation
