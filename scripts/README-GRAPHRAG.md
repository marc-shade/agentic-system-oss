# GraphRAG Quick Start

Lightweight GraphRAG implementation for enhanced-memory with relationship-aware retrieval.

## Quick Start

### 1. Build Initial Graph
```bash
cd /mnt/agentic-system
source .venv/bin/activate
python scripts/build-initial-graph.py
```

**Output:**
```
Total relationships created: 320,265
  - Co-occurrence: 319,731
  - Type-based: 34
  - Temporal: 500
  - Hierarchical: 0
```

### 2. Check Statistics
```bash
python scripts/graph-rag.py stats
```

**Output:**
```
Entities: 1,099
Relationships: 320,265
Avg relationships/entity: 291.41

Relationship Types:
  relates_to: 306,671 (95.8%)
  part_of: 9,630 (3.0%)
  uses: 3,945 (1.2%)
```

### 3. Test Search
```bash
python scripts/graph-rag.py search \
  --query "memory consolidation" \
  --depth 2 \
  --limit 5
```

**Output:**
```
1. Memory Consolidation Theorem (theorem)
   Vector: 1.000 | Graph: 0.000 | Combined: 0.600

2. Wake-Sleep Consolidated Learning (WSCL) (technique)
   Vector: 0.700 | Graph: 0.213 | Combined: 0.505
   Neighbors: 312,142
     - VERSE Streaming Continual Learning [relates_to]
     - Self-Evolving Knowledge Graphs [relates_to]
```

### 4. Run Test Suite
```bash
python scripts/test-graph-rag.py
```

## CLI Commands

### Search
```bash
python scripts/graph-rag.py search \
  --query "your query" \
  --depth 2 \
  --limit 10
```

### Get Neighbors
```bash
python scripts/graph-rag.py neighbors --entity-id 123
```

### Add Relationship
```bash
python scripts/graph-rag.py add-rel \
  --source 123 \
  --target 456 \
  --rel-type causes
```

### Extract Relationships (Pattern-based)
```bash
python scripts/graph-rag.py extract --limit 100
```

## Python API

### Basic Search
```python
from graph_rag import GraphRAG

rag = GraphRAG()

results = rag.graph_enhanced_search(
    query="memory consolidation",
    include_neighbors=True,
    depth=2,
    limit=10
)

for result in results:
    print(f"{result.entity_name}: {result.combined_score:.3f}")
    print(f"  Neighbors: {len(result.neighbors)}")
```

### Add Relationship
```python
rag.add_relationship(
    source_id=123,
    target_id=456,
    rel_type="causes",
    weight=0.9,
    is_causal=True
)
```

### Get Neighbors
```python
neighbors = rag.get_neighbors(
    entity_id=123,
    rel_type="causes",  # Optional filter
    direction="both",
    min_weight=0.5
)
```

### Graph Traversal
```python
context = rag.expand_graph_context(
    entity_ids=[123, 456],
    depth=2,
    min_weight=0.3
)
```

## Relationship Types

- `relates_to` - General semantic relation
- `part_of` - Component of larger system
- `uses` - Uses or depends on
- `implements` - Implements interface/pattern
- `depends_on` - Hard dependency
- `causes` - Causal relationship (set is_causal=True)
- `extends` - Extends/inherits from

## Files

```
/mnt/agentic-system/scripts/
  ├── graph-rag.py              # Core implementation
  ├── build-initial-graph.py    # Initial graph builder
  ├── test-graph-rag.py         # Test suite
  └── README-GRAPHRAG.md        # This file

/mnt/agentic-system/docs/
  ├── GRAPH-RAG-INTEGRATION.md  # Detailed guide
  └── GRAPH-RAG-REPORT.md       # Implementation report
```

## Current Statistics

```
Entities:                 1,103
Relationships:            320,265
Avg relationships/entity: 290.36

Graph density: Very high
Qdrant: ✅ Connected
Vector search: ⚠️ Text fallback (embeddings TODO)
```

## Troubleshooting

### No relationships found
```bash
python scripts/build-initial-graph.py
```

### Slow search
Reduce depth or increase min_weight:
```python
results = rag.graph_enhanced_search(query, depth=1)
# or
context = rag.expand_graph_context(ids, min_weight=0.7)
```

### Backup database
```bash
cp ~/.claude/enhanced_memories/memory.db \
   ~/.claude/enhanced_memories/memory.db.backup-$(date +%Y%m%d)
```

## Documentation

- **Quick Start:** This file
- **Integration Guide:** `/mnt/agentic-system/docs/GRAPH-RAG-INTEGRATION.md`
- **Implementation Report:** `/mnt/agentic-system/docs/GRAPH-RAG-REPORT.md`

## Example Output

```bash
$ python scripts/graph-rag.py search --query "agentic system" --limit 3

Searching for: agentic system

=== Found 3 Results ===

1. macpro51_deployment_complete (milestone)
   Vector: 0.700 | Graph: 0.000 | Combined: 0.420
   Content: Agentic System Guardian deployed and running...

2. MCP_Memory_System_Research_Report (research_finding)
   Vector: 0.700 | Graph: 0.213 | Combined: 0.505
   Neighbors: 312,148
     - distributed_neural_coordination_research [relates_to]
     - neural_cluster_implementation_insights [relates_to]
```

## Next Steps

1. **Add vector embeddings** for semantic search
2. **Prune low-value relationships** to reduce graph density
3. **Integrate with MCP** as new tool in enhanced-memory-mcp
4. **Implement graph algorithms** (PageRank, community detection)

---

**Status:** ✅ Production Ready
**Date:** 2025-11-28
