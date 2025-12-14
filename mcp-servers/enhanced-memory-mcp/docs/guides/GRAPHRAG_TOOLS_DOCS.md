# GraphRAG Tools for Enhanced-Memory MCP

## Overview

GraphRAG (Graph-Enhanced Retrieval-Augmented Generation) tools integrate relationship-aware search capabilities into the enhanced-memory MCP server. This implementation combines vector similarity search with graph traversal to provide richer, more contextual results.

## Architecture

### Components

1. **GraphRAG Core** (`/mnt/agentic-system/scripts/graph-rag.py`)
   - SQLite-based relationship storage (extends existing `relations` table)
   - Qdrant vector search integration (when available)
   - Graph traversal algorithms
   - Automatic relationship extraction

2. **MCP Tools** (`graphrag_tools.py`)
   - FastMCP tool registration
   - Async API wrappers
   - Error handling and validation
   - Integration with enhanced-memory database

3. **Database Schema**
   - **relations table**: Enhanced with `weight`, `is_causal`, `context` columns
   - **relationship_extraction_log**: Tracks automatic extraction runs
   - Indexes on `from_entity_id`, `to_entity_id`, `relation_type` for fast traversal

## Research Basis

- **Microsoft GraphRAG**: Knowledge graph-based retrieval augmentation
- **"You're Doing Memory All Wrong" (Zapai)**: Graph traversal patterns for memory systems
- **Anthropic Contextual Retrieval**: Context-aware chunk enhancement

## Available Tools

### 1. graph_enhanced_search

**Purpose**: Hybrid vector + graph search with relationship expansion

**Signature**:
```python
async def graph_enhanced_search(
    query: str,
    depth: int = 2,
    limit: int = 10,
    include_neighbors: bool = True,
    vector_weight: float = 0.6,
    graph_weight: float = 0.4
) -> Dict[str, Any]
```

**Process**:
1. Vector search in Qdrant (or fallback text search)
2. Expand context via graph traversal (up to `depth` hops)
3. Calculate graph centrality scores
4. Re-rank by combined `(vector_weight × vector_score) + (graph_weight × graph_score)`

**Parameters**:
- `query`: Search query string
- `depth`: Graph traversal depth (1-3, clamped)
- `limit`: Maximum results to return
- `include_neighbors`: Whether to include connected entities
- `vector_weight`: Weight for vector similarity (0.0-1.0)
- `graph_weight`: Weight for graph centrality (0.0-1.0)

**Returns**:
```json
{
  "success": true,
  "query": "TRAP framework",
  "result_count": 5,
  "results": [
    {
      "entity_id": 42,
      "entity_name": "TRAP Framework",
      "entity_type": "concept",
      "content": "Think-Reason-Act-Plan framework...",
      "vector_score": 0.85,
      "graph_score": 0.72,
      "combined_score": 0.79,
      "neighbors": [
        {
          "entity_id": 43,
          "name": "Sequential Thinking",
          "relation": "implements",
          "weight": 0.9,
          "depth": 1
        }
      ],
      "neighbor_count": 3
    }
  ],
  "search_params": {
    "depth": 2,
    "vector_weight": 0.6,
    "graph_weight": 0.4
  }
}
```

**Use Cases**:
- Research queries requiring contextual understanding
- Finding related concepts and their connections
- Discovering causal chains and dependencies
- Exploring knowledge clusters

---

### 2. get_entity_neighbors

**Purpose**: Explore connections from a specific entity

**Signature**:
```python
async def get_entity_neighbors(
    entity_id: int,
    relation_type: Optional[str] = None,
    direction: str = "both",
    depth: int = 1,
    limit: int = 50,
    min_weight: float = 0.0
) -> Dict[str, Any]
```

**Parameters**:
- `entity_id`: Source entity ID
- `relation_type`: Filter by type (`relates_to`, `causes`, `part_of`, `implements`, `extends`, `uses`, `depends_on`)
- `direction`: Traversal direction:
  - `"outbound"`: entity → others
  - `"inbound"`: others → entity
  - `"both"`: bidirectional
- `depth`: How many hops to traverse (1-3)
- `limit`: Max neighbors to return
- `min_weight`: Minimum relationship strength (0.0-1.0)

**Returns**:
```json
{
  "success": true,
  "entity_id": 42,
  "neighbor_count": 12,
  "neighbors": [
    {
      "neighbor_id": 43,
      "neighbor_name": "Sequential Thinking",
      "entity_type": "pattern",
      "relation_type": "implements",
      "weight": 0.9,
      "is_causal": false,
      "direction": "outbound"
    }
  ],
  "search_params": {
    "relation_type": null,
    "direction": "both",
    "depth": 1,
    "min_weight": 0.0
  }
}
```

**Use Cases**:
- Understanding entity relationships
- Finding causal chains
- Dependency analysis
- Context exploration

---

### 3. add_entity_relationship

**Purpose**: Manually create relationship edges

**Signature**:
```python
async def add_entity_relationship(
    source_id: int,
    target_id: int,
    relation_type: str,
    weight: float = 1.0,
    is_causal: bool = False,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Relationship Types**:
- `relates_to`: General association
- `causes`: Causal relationship (A causes B)
- `part_of`: Hierarchical (A is part of B)
- `implements`: Implementation (A implements B)
- `extends`: Extension (A extends B)
- `uses`: Dependency (A uses B)
- `depends_on`: Strong dependency (A depends on B)

**Parameters**:
- `source_id`: Source entity ID
- `target_id`: Target entity ID
- `relation_type`: Relationship type (see above)
- `weight`: Relationship strength (0.0-1.0)
- `is_causal`: Flag for causal relationships
- `context`: Optional metadata (stored as JSON)

**Returns**:
```json
{
  "success": true,
  "relationship_id": 123,
  "source_id": 1,
  "target_id": 2,
  "relation_type": "implements",
  "weight": 0.9,
  "is_causal": false
}
```

**Use Cases**:
- Explicit knowledge graph construction
- Documenting dependencies
- Marking causal relationships
- Building hierarchies

---

### 4. get_graph_statistics

**Purpose**: Get knowledge graph overview and health metrics

**Signature**:
```python
async def get_graph_statistics() -> Dict[str, Any]
```

**Returns**:
```json
{
  "success": true,
  "statistics": {
    "entities": 1547,
    "relationships": 3892,
    "relationship_types": [
      {"relation_type": "relates_to", "count": 1203},
      {"relation_type": "causes", "count": 421},
      {"relation_type": "implements", "count": 389}
    ],
    "avg_relationships_per_entity": 2.52,
    "causal_relationships": 421,
    "qdrant_available": true,
    "qdrant_connected": true
  },
  "health": {
    "entities": 1547,
    "relationships": 3892,
    "avg_relationships_per_entity": 2.52,
    "causal_relationships": 421,
    "qdrant_status": "connected"
  }
}
```

**Use Cases**:
- System health monitoring
- Graph density analysis
- Relationship distribution insights
- Qdrant connectivity verification

---

### 5. extract_entity_relationships

**Purpose**: Auto-discover relationships from entity observations

**Signature**:
```python
async def extract_entity_relationships(
    entity_id: int
) -> Dict[str, Any]
```

**Extraction Patterns**:
- `"X causes Y"` → causes
- `"X implements Y"` → implements
- `"X relates to Y"` → relates_to
- `"X is part of Y"` → part_of
- `"X extends Y"` → extends
- `"X uses Y"` → uses
- `"X depends on Y"` → depends_on

**Returns**:
```json
{
  "success": true,
  "entity_id": 42,
  "relationships_found": 7
}
```

**Use Cases**:
- Automatic graph building
- Pattern discovery
- Relationship mining from text
- Knowledge graph enrichment

---

### 6. extract_all_relationships

**Purpose**: Batch relationship extraction across entire database

**Signature**:
```python
async def extract_all_relationships(
    limit: Optional[int] = None
) -> Dict[str, Any]
```

**Parameters**:
- `limit`: Max entities to process (None = all unprocessed)

**Returns**:
```json
{
  "success": true,
  "statistics": {
    "total_processed": 234,
    "total_relationships": 892,
    "entities_with_relationships": 187
  },
  "summary": "Processed 234 entities, found 892 relationships in 187 entities"
}
```

**Use Cases**:
- Initial graph population
- Periodic enrichment runs
- Batch processing for new entities
- Graph maintenance

---

### 7. build_local_graph

**Purpose**: Extract subgraph for visualization/analysis

**Signature**:
```python
async def build_local_graph(
    entity_ids: List[int]
) -> Dict[str, Any]
```

**Parameters**:
- `entity_ids`: List of entity IDs to include

**Returns**:
```json
{
  "success": true,
  "graph": {
    "nodes": [
      {
        "id": 1,
        "name": "TRAP Framework",
        "entity_type": "concept",
        "tier": "core",
        "salience_score": 0.85
      }
    ],
    "edges": [
      {
        "id": 10,
        "from_entity_id": 1,
        "to_entity_id": 2,
        "relation_type": "implements",
        "weight": 0.9,
        "is_causal": false
      }
    ],
    "node_count": 5,
    "edge_count": 8
  }
}
```

**Use Cases**:
- Graph visualization
- Relationship analysis
- Subgraph extraction
- Context mapping

---

## Integration Details

### Server Integration

Added to `/mnt/agentic-system/mcp-servers/enhanced-memory-mcp/server.py`:

```python
# Register GraphRAG tools (Relationship-aware retrieval)
# Based on Microsoft GraphRAG + Zapai memory patterns
try:
    from graphrag_tools import register_graphrag_tools
    register_graphrag_tools(app, DB_PATH)
    logger.info("✅ GraphRAG tools integrated - Graph-enhanced search with relationship traversal")
except Exception as e:
    logger.warning(f"⚠️  GraphRAG integration skipped: {e}")
```

### Database Schema Upgrades

The GraphRAG initialization automatically upgrades the `relations` table:

```sql
-- New columns added if missing
ALTER TABLE relations ADD COLUMN weight REAL DEFAULT 1.0;
ALTER TABLE relations ADD COLUMN is_causal BOOLEAN DEFAULT 0;
ALTER TABLE relations ADD COLUMN context TEXT;  -- JSON

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_entity_id);
CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);

-- Extraction tracking
CREATE TABLE IF NOT EXISTS relationship_extraction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER,
    relationships_found INTEGER,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (entity_id) REFERENCES entities (id)
);
```

## Performance Considerations

### Graph Traversal Depth

- **Depth 1**: Fast, single-hop neighbors (~10-50ms)
- **Depth 2**: Moderate, two-hop expansion (~50-200ms)
- **Depth 3**: Slower, three-hop expansion (~200-500ms)

**Recommendation**: Use depth 2 for most queries, depth 3 only for comprehensive exploration.

### Relationship Weights

- Use `min_weight` parameter to filter low-quality relationships
- Typical threshold: 0.3 for noise reduction
- Auto-extracted relationships default to 0.5 weight

### Batch Processing

For large databases:
```python
# Process in batches
await extract_all_relationships(limit=100)
# Check progress, then continue
await extract_all_relationships(limit=100)
```

### Qdrant Integration

- **Available**: Uses vector search for initial retrieval
- **Unavailable**: Falls back to SQLite text search (LIKE queries)
- Check status: `get_graph_statistics()` → `qdrant_status`

## Usage Examples

### Example 1: Enhanced Research Query

```python
# Search with graph expansion
results = await graph_enhanced_search(
    query="memory consolidation patterns",
    depth=2,
    include_neighbors=True,
    vector_weight=0.6,
    graph_weight=0.4
)

# Results include:
# - Vector similarity matches
# - Connected concepts (depth 2)
# - Combined relevance score
# - Graph centrality bonus
```

### Example 2: Explore Causal Chains

```python
# Find what causes a specific issue
causes = await get_entity_neighbors(
    entity_id=42,  # "Memory fragmentation"
    relation_type="causes",
    direction="inbound",  # What causes this?
    depth=2
)

# Find what this issue causes
effects = await get_entity_neighbors(
    entity_id=42,
    relation_type="causes",
    direction="outbound",  # What does this cause?
    depth=2
)
```

### Example 3: Build Knowledge Graph

```python
# Step 1: Add manual relationships
await add_entity_relationship(
    source_id=1,
    target_id=2,
    relation_type="implements",
    weight=0.9,
    context={"discovered_by": "code_review", "date": "2025-11-28"}
)

# Step 2: Auto-extract from text
stats = await extract_all_relationships(limit=100)

# Step 3: Check graph health
graph_stats = await get_graph_statistics()
print(f"Graph has {graph_stats['statistics']['relationships']} relationships")
```

### Example 4: Visualize Knowledge Cluster

```python
# Get top entities for a topic
search_results = await graph_enhanced_search(
    query="self-improvement algorithms",
    limit=5
)

entity_ids = [r['entity_id'] for r in search_results['results']]

# Build subgraph
subgraph = await build_local_graph(entity_ids=entity_ids)

# subgraph contains nodes and edges for visualization
```

## Troubleshooting

### Import Errors

```bash
# Verify GraphRAG script exists
ls -la /mnt/agentic-system/scripts/graph-rag.py

# Check Python syntax
python3 -m py_compile /mnt/agentic-system/scripts/graph-rag.py
```

### Database Issues

```bash
# Check database schema
sqlite3 ~/.claude/enhanced_memories/memory.db ".schema relations"

# Verify indexes
sqlite3 ~/.claude/enhanced_memories/memory.db ".indexes relations"
```

### Qdrant Connection

```python
stats = await get_graph_statistics()
if stats['statistics']['qdrant_connected'] == False:
    print("Qdrant not connected - using text search fallback")
    # Check if Qdrant is running: docker ps | grep qdrant
```

### Performance Issues

```python
# For large graphs, use depth limits
results = await graph_enhanced_search(
    query="...",
    depth=1,  # Reduce from default 2
    limit=10
)

# Filter by weight
neighbors = await get_entity_neighbors(
    entity_id=42,
    min_weight=0.5,  # Only strong relationships
    limit=20
)
```

## Future Enhancements

### Planned Features

1. **Graph Centrality Metrics**
   - PageRank for entity importance
   - Betweenness centrality for key connectors
   - Degree centrality for hub detection

2. **Path Finding**
   - Shortest path between entities
   - All paths with max depth
   - Weighted pathfinding

3. **Community Detection**
   - Clustering related entities
   - Topic identification
   - Knowledge domain mapping

4. **Vector Search Integration**
   - Full sentence-transformers embedding
   - Hybrid BM25 + vector + graph search
   - Re-ranking with cross-encoder

5. **Relationship Quality**
   - Confidence scoring
   - Automatic weight adjustment
   - Relationship pruning

## References

- Microsoft GraphRAG: https://github.com/microsoft/graphrag
- "You're Doing Memory All Wrong" (Zapai): Graph memory patterns
- Anthropic Contextual Retrieval: https://www.anthropic.com/news/contextual-retrieval

## Changelog

### 2025-11-28 - Initial Integration
- Added 7 GraphRAG tools to enhanced-memory MCP
- Integrated with existing database schema
- Added automatic relationship extraction
- Implemented hybrid vector + graph search
- Created comprehensive documentation
