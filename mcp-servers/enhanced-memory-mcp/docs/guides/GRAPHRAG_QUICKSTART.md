# GraphRAG Quick Start Guide

## What is GraphRAG?

GraphRAG (Graph-Enhanced Retrieval-Augmented Generation) adds relationship-aware search to enhanced-memory. Instead of just finding similar content, it also explores connections between entities, providing richer context.

## Key Features

✅ **Graph-Enhanced Search**: Combines vector similarity + relationship traversal
✅ **Automatic Relationship Extraction**: Discovers connections from text
✅ **Causal Reasoning**: Track cause-effect relationships
✅ **Contextual Results**: Each result includes connected entities
✅ **320,265 Relationships**: Already populated from existing memory!

## Current Status

```
Entities: 1,107
Relationships: 320,265
Avg relationships/entity: 289.16 (very well connected!)
Causal relationships: 94,617
Qdrant: Connected
```

## Quick Examples

### 1. Enhanced Search (Most Common Use)

```python
# Regular search + graph context
results = await graph_enhanced_search(
    query="memory consolidation",
    depth=2,  # Explore 2 hops
    include_neighbors=True
)

# Each result includes:
# - Vector similarity score
# - Graph centrality score
# - Connected entities
# - Combined relevance
```

**When to use**: Research queries, exploring concepts, finding related knowledge

### 2. Explore Connections

```python
# What is entity 42 connected to?
neighbors = await get_entity_neighbors(
    entity_id=42,
    depth=1
)

# Find causal relationships
causes = await get_entity_neighbors(
    entity_id=42,
    relation_type="causes",
    direction="outbound"  # What does this cause?
)
```

**When to use**: Understanding relationships, causal analysis, dependency tracking

### 3. Add Manual Relationships

```python
# Document a known relationship
await add_entity_relationship(
    source_id=1,
    target_id=2,
    relation_type="implements",
    weight=0.9,  # Strong relationship
    is_causal=False
)
```

**When to use**: Building knowledge graphs, documenting connections

### 4. Graph Statistics

```python
# Check system health
stats = await get_graph_statistics()

# Returns:
# - Entity/relationship counts
# - Relationship type distribution
# - Average connectivity
# - Qdrant status
```

**When to use**: Monitoring, analytics, health checks

### 5. Auto-Extract Relationships

```python
# Process a single entity
result = await extract_entity_relationships(entity_id=42)

# Or batch process
stats = await extract_all_relationships(limit=100)
```

**When to use**: Initial graph population, enrichment, batch processing

## Relationship Types

| Type | Description | Example |
|------|-------------|---------|
| `relates_to` | General association | "Python relates to programming" |
| `causes` | Causal relationship | "Memory leak causes performance degradation" |
| `part_of` | Hierarchical | "CPU is part of computer" |
| `implements` | Implementation | "TRAP implements reasoning framework" |
| `extends` | Extension | "Python 3.14 extends Python 3.13" |
| `uses` | Dependency | "FastMCP uses asyncio" |
| `depends_on` | Strong dependency | "Build depends on compilation" |

## Search Scoring

GraphRAG uses **hybrid scoring**:

```
combined_score = (vector_weight × vector_score) + (graph_weight × graph_score)
```

Default weights:
- `vector_weight = 0.6` (60% vector similarity)
- `graph_weight = 0.4` (40% graph centrality)

**Graph score considers**:
- Number of connections
- Relationship strength (weight)
- Causal relationships (+bonus)
- Connection depth (closer is better)

## Performance Tips

### Traversal Depth

- **Depth 1**: Fast (10-50ms), immediate neighbors only
- **Depth 2**: Moderate (50-200ms), recommended for most queries
- **Depth 3**: Slower (200-500ms), comprehensive exploration

### Filtering

```python
# Reduce noise with minimum weight
neighbors = await get_entity_neighbors(
    entity_id=42,
    min_weight=0.5,  # Only strong relationships
    limit=20  # Limit results
)
```

### Batch Processing

```python
# For large databases, process in batches
await extract_all_relationships(limit=100)
# Check progress, then continue
await extract_all_relationships(limit=100)
```

## Common Patterns

### Pattern 1: Research with Context

```python
# Find information + related concepts
results = await graph_enhanced_search(
    query="self-improvement algorithms",
    depth=2,
    include_neighbors=True,
    limit=10
)

# Each result includes neighbors for context
for result in results['results']:
    print(f"{result['entity_name']}: {result['combined_score']}")
    print(f"  Connected to: {result['neighbor_count']} entities")
```

### Pattern 2: Causal Chain Discovery

```python
# Find root causes
root_causes = await get_entity_neighbors(
    entity_id=problem_id,
    relation_type="causes",
    direction="inbound",  # What causes this?
    depth=2
)

# Find effects
effects = await get_entity_neighbors(
    entity_id=problem_id,
    relation_type="causes",
    direction="outbound",  # What does this cause?
    depth=2
)
```

### Pattern 3: Knowledge Graph Building

```python
# Step 1: Create core entities (use create_entities)
# Step 2: Add manual relationships
await add_entity_relationship(
    source_id=concept_a,
    target_id=concept_b,
    relation_type="implements",
    weight=0.9
)

# Step 3: Auto-extract additional relationships
stats = await extract_all_relationships(limit=50)

# Step 4: Verify graph health
graph_stats = await get_graph_statistics()
```

### Pattern 4: Context Expansion

```python
# Get initial results
search_results = await graph_enhanced_search(
    query="memory architecture",
    limit=5
)

# Extract entity IDs
entity_ids = [r['entity_id'] for r in search_results['results']]

# Get full subgraph for visualization
subgraph = await build_local_graph(entity_ids=entity_ids)

# subgraph contains nodes and edges
```

## Integration with Claude Code

The GraphRAG tools are now available in Claude Code through the enhanced-memory MCP server:

```python
# In Claude Code, you can use these tools directly:
mcp__enhanced_memory__graph_enhanced_search(
    query="your query",
    depth=2
)

mcp__enhanced_memory__get_entity_neighbors(
    entity_id=42
)

# etc.
```

## Troubleshooting

### Qdrant Not Connected

```python
stats = await get_graph_statistics()
if stats['statistics']['qdrant_connected'] == False:
    # GraphRAG falls back to text search
    # Check: docker ps | grep qdrant
    # Start: docker start qdrant
```

### No Relationships Found

```python
# Check if extraction has been run
stats = await get_graph_statistics()
if stats['statistics']['relationships'] == 0:
    # Run extraction
    result = await extract_all_relationships(limit=100)
```

### Slow Queries

```python
# Reduce depth
results = await graph_enhanced_search(
    query="...",
    depth=1,  # Faster
    limit=10
)

# Filter by weight
neighbors = await get_entity_neighbors(
    entity_id=42,
    min_weight=0.5  # Only strong relationships
)
```

## Next Steps

1. **Explore Existing Graph**: Run `get_graph_statistics()` to see current state
2. **Try Enhanced Search**: Use `graph_enhanced_search()` for research queries
3. **Analyze Relationships**: Use `get_entity_neighbors()` to explore connections
4. **Build Knowledge**: Add manual relationships with `add_entity_relationship()`
5. **Auto-Enrich**: Run `extract_all_relationships()` periodically

## Resources

- **Full Documentation**: `GRAPHRAG_TOOLS_DOCS.md`
- **Test Script**: `test_graphrag_integration.py`
- **GraphRAG Implementation**: `/mnt/agentic-system/scripts/graph-rag.py`
- **README**: `/mnt/agentic-system/scripts/README-GRAPHRAG.md`

---

**Current Graph Stats** (as of integration):
- ✅ 1,107 entities
- ✅ 320,265 relationships (very well connected!)
- ✅ 94,617 causal relationships
- ✅ Qdrant connected
- ✅ All 7 tools registered and tested
