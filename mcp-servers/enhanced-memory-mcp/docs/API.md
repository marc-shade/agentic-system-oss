# Enhanced Memory MCP - API Reference

## Overview

Enhanced Memory MCP provides persistent semantic memory with Git-like version control, compression, and intelligent tiering for agentic AI systems.

## Core Tools

### Entity Management

#### `create_entities`
Create entities with compression, storage, automatic versioning, and contextual enrichment.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| entities | List[Object] | Yes | List of entity objects |

**Entity Object Schema:**
```json
{
  "name": "string (required)",
  "entityType": "string (required)",
  "observations": ["array of strings (required)"]
}
```

**Returns:**
```json
{
  "created": 3,
  "failed": 0,
  "results": [
    {"name": "entity-name", "id": 123, "compression_ratio": "65.2%"}
  ]
}
```

#### `search_nodes`
Search for entities by name or type with automatic version history.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| query | string | Yes | - | Search query string |
| limit | integer | No | 10 | Maximum number of results |

**Returns:**
```json
{
  "results": [
    {"id": 123, "name": "entity", "score": 0.95, "observations": [...]}
  ]
}
```

### Version Control

#### `memory_diff`
Get diff between two versions of a memory.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| entity_name | string | Yes | - | Name of the entity |
| version1 | integer | No | current-1 | First version number |
| version2 | integer | No | current | Second version number |

#### `memory_revert`
Revert a memory to a specific version.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity_name | string | Yes | Name of the entity |
| version | integer | Yes | Version number to revert to |

#### `memory_branch`
Create a branch of a memory for experimentation.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity_name | string | Yes | Name of entity to branch |
| branch_name | string | Yes | Name for the new branch |
| description | string | No | Purpose of the branch |

### Conflict Detection

#### `detect_memory_conflicts`
Detect duplicate or conflicting memories.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| threshold | float | No | 0.85 | Similarity threshold (0.0-1.0) |

**Returns:**
```json
{
  "conflicts": [
    {
      "entity1": "name1",
      "entity2": "name2",
      "similarity": 0.92,
      "conflict_type": "potential_duplicate"
    }
  ]
}
```

### System Status

#### `get_memory_status`
Get overall memory system status and statistics.

**Returns:**
```json
{
  "total_entities": 1659,
  "total_versions": 3421,
  "storage_used_mb": 245.6,
  "compression_stats": {...},
  "tier_distribution": {...}
}
```

## Neural Memory Fabric (NMF) Tools

### `nmf_remember`
Store a new memory in the Neural Memory Fabric.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| content | string | Yes | - | Memory content to store |
| agent_id | string | No | "default" | Agent identifier |
| tags | List[string] | No | null | Optional tags |
| metadata | Object | No | null | Additional metadata |

### `nmf_recall`
Retrieve memories from the Neural Memory Fabric.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| query | string | Yes | - | Search query |
| mode | string | No | "hybrid" | Retrieval mode: semantic, graph, temporal, hybrid |
| agent_id | string | No | null | Filter by agent |
| limit | integer | No | 10 | Maximum results |

### `nmf_open_block` / `nmf_edit_block` / `nmf_close_block`
Letta-style memory block management for structured agent memory.

## SAFLA Integration

### `safla_generate_embeddings`
Generate embeddings using SAFLA's extreme-optimized engine (1.75M+ ops/sec).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| texts | List[string] | Yes | Texts to embed |

### `safla_store_memory` / `safla_retrieve_memories`
Store and retrieve from SAFLA's hybrid memory system with episodic, semantic, and procedural memory types.

## Semantic Cache

### `semantic_cache_get`
Check semantic cache for similar query (>= 0.90 threshold).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | Query to search for |
| context | string | No | Optional context |

### `agi_cached_reasoning`
AGI-optimized cache check with domain-specific thresholds.

**Domains:**
- `reasoning`: 0.92 threshold, 24h TTL
- `consolidation`: 0.90 threshold, 7d TTL
- `research`: 0.88 threshold, 3d TTL
- `api_calls`: 0.90 threshold, 24h TTL
- `embeddings`: 0.95 threshold, 7d TTL

## FACT (Fast Accelerated Cache Technology)

### `fact_search`
FACT-accelerated memory search with cache-first retrieval.

**Performance:** <48ms on cache hit, <140ms on miss.

### `unified_search`
Unified search with FACT cache and Qdrant fallback.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| query | string | Yes | - | Search query |
| limit | integer | No | 10 | Maximum results |
| backend | string | No | "fact_cache" | Backend: fact_cache, qdrant, hybrid, semantic |

## ReasoningBank

### `rb_retrieve`
Retrieve relevant reasoning memories for a query using MMR for diversity.

### `rb_learn`
Learn from task outcomes by distilling memories.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| task_id | string | Yes | Unique task identifier |
| query | string | Yes | Original task query |
| outcome | string | Yes | "success", "failure", or "partial" |
| trajectory | string | No | Execution trajectory (JSON) |
| domain | string | No | Memory domain |

### `rb_consolidate`
Consolidate reasoning memories (deduplication, contradiction detection, pruning).

## Code Execution

### `execute_code`
Execute Python code in secure sandbox with API access.

**Token Savings:** 96.6% average reduction through progressive disclosure.

**Available APIs in Code:**
- Memory: `create_entities`, `search_nodes`, `get_status`, `update_entity`
- Versioning: `diff`, `revert`, `branch`, `history`, `commit`
- Analysis: `detect_conflicts`, `analyze_patterns`, `classify_content`
- Filesystem: `workspace`, `list_files`, `read_file`, `write_file`
- Skills: `save_skill`, `load_skill`, `list_skills`

## Error Handling

All tools return consistent error responses:

```json
{
  "success": false,
  "error": "Error message",
  "error_code": "ERROR_CODE"
}
```

## Rate Limits

- Default: 1000 requests/minute
- Bulk operations: 100 requests/minute
- Code execution: 10 concurrent sandboxes
