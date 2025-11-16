# Knowledge Graph Quick Start Guide

## 5-Minute Setup

### Step 1: Run Migration (2 minutes)

```bash
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp

# See what will change (safe)
python3 migrate_to_knowledge_graph.py --dry-run

# Run migration (creates backup automatically)
python3 migrate_to_knowledge_graph.py --force
```

Expected output:
```
============================================================
Knowledge Graph Migration Starting
============================================================

Step 1: Creating backup...
  ✓ Backup created: /Users/marc/.claude/enhanced_memories/memory_backup_20250111_100000.db

Current Database Statistics:
  Entities: 1234
  Relations: 567
  Observations: 2345

Step 3: Executing schema migration...
  ✓ Schema migration executed successfully

Step 4: Validating migration...
  ✓ All views created
  ✓ 12 indexes created
  ✓ All 567 relations have strength values
  ✓ Migration validated successfully

Step 5: Generating report...
  ✓ Report saved: /Users/marc/.claude/enhanced_memories/migration_report_20250111_100000.json

============================================================
Migration Complete!
============================================================
```

### Step 2: Verify Integration (1 minute)

Restart your MCP server and check logs:

```bash
# Server logs should show:
✅ Knowledge Graph tools integrated - Temporal edges, Bi-directional traversal, Causal reasoning
```

### Step 3: Run Tests (2 minutes)

```bash
python3 test_knowledge_graph.py
```

All tests should pass:
```
test_concept_entity_validation ... ok
test_relationship_validation ... ok
test_outbound_traversal ... ok
test_causal_chain_traversal ... ok
test_create_relationship ... ok
test_hybrid_search ... ok

----------------------------------------------------------------------
Ran 12 tests in 0.234s

OK
```

## First Use Cases

### Use Case 1: Create a Causal Relationship

```python
# Create entities first (if they don't exist)
await create_entities([
    {
        "name": "knowledge_graph_implementation",
        "entityType": "project",
        "observations": ["Implemented Zapai video recommendations"]
    },
    {
        "name": "improved_memory_retrieval",
        "entityType": "outcome",
        "observations": ["40% better recall", "Full context retrieval"]
    }
])

# Create causal relationship
result = await create_kg_relationship(
    from_entity="knowledge_graph_implementation",
    to_entity="improved_memory_retrieval",
    relation_type="causes",
    strength=0.9,
    is_causal=True
)
```

### Use Case 2: Get Connected Context

```python
# Get all entities within 2 hops of a project
context = await get_kg_entity_context(
    entity_name="knowledge_graph_implementation",
    max_depth=2,
    min_strength=0.3
)

print(f"Found {context['total_connected']} connected entities")
print(f"Depth explored: {context['max_depth_explored']}")

# Example output:
# Found 23 connected entities
# Depth explored: 2
# {
#   'root': 'knowledge_graph_implementation',
#   'total_connected': 23,
#   'context_by_depth': {
#     1: [
#       {'name': 'improved_memory_retrieval', 'type': 'outcome', 'relationship': 'causes'},
#       {'name': 'ontology_schema', 'type': 'code_module', 'relationship': 'contains'},
#       ...
#     ],
#     2: [
#       {'name': 'vector_search', 'type': 'concept', 'relationship': 'extends'},
#       ...
#     ]
#   }
# }
```

### Use Case 3: Follow Causal Chain

```python
# Find what led to what
chain = await get_causal_chain(
    entity_name="production_bug_fix",
    max_depth=5
)

# Prints causal chain:
# production_bug_fix ← caused_by ← code_refactoring
# code_refactoring ← caused_by ← performance_requirement
# performance_requirement ← caused_by ← user_feedback
```

### Use Case 4: Hybrid Search

```python
# Find entities semantically + expand via graph
results = await kg_hybrid_search(
    query="optimization techniques",
    depth=2
)

# Returns:
# - Semantic matches for "optimization techniques"
# - All entities within 2 hops of each match
# - Total connected entities: much more than semantic alone!
```

## Common Patterns

### Pattern 1: Track Project Dependencies

```python
# Create project
await create_entities([{"name": "project_a", "entityType": "project"}])
await create_entities([{"name": "library_x", "entityType": "code_module"}])

# Track dependency
await create_kg_relationship(
    from_entity="project_a",
    to_entity="library_x",
    relation_type="depends_on",
    strength=0.9
)

# Later: Find all dependencies
context = await get_kg_entity_context(
    entity_name="project_a",
    max_depth=1  # Direct dependencies only
)
```

### Pattern 2: Learning Pathways

```python
# Track learning relationships
await create_kg_relationship(
    from_entity="advanced_optimization",
    to_entity="basic_algorithms",
    relation_type="requires",  # Prerequisite
    strength=0.8
)

# Find what you need to learn first
context = await get_kg_entity_context(
    entity_name="advanced_optimization",
    max_depth=3  # Multi-level prerequisites
)
```

### Pattern 3: Impact Analysis

```python
# What was the outcome?
await create_kg_relationship(
    from_entity="algorithm_improvement",
    to_entity="40_percent_speedup",
    relation_type="resulted_in",
    is_causal=True,
    causal_strength=0.95
)

# Find all outcomes
chain = await get_causal_chain(
    entity_name="algorithm_improvement"
)
```

## MCP Tool Reference

### 1. create_kg_relationship

```python
await create_kg_relationship(
    from_entity: str,        # Source entity name
    to_entity: str,          # Target entity name
    relation_type: str,      # Type (causes, enables, relates_to, etc.)
    strength: float = 0.5,   # 0.0-1.0
    is_causal: bool = False, # Mark as causal
    bidirectional: bool = False  # Auto-create reverse
)
```

**Valid Relation Types**:
- Causal: `causes`, `caused_by`, `enables`, `triggered_by`, `resulted_in`
- Hierarchical: `contains`, `part_of`, `belongs_to`
- Temporal: `follows`, `precedes`
- Semantic: `relates_to`, `similar_to`, `extends`
- Operational: `uses`, `requires`, `provides`, `depends_on`

### 2. get_kg_entity_context

```python
await get_kg_entity_context(
    entity_name: str,      # Entity to explore from
    max_depth: int = 2,    # How many hops
    min_strength: float = 0.3  # Minimum relationship strength
)
```

Returns:
```python
{
    'root': 'entity_name',
    'total_connected': 47,
    'max_depth_explored': 2,
    'context_by_depth': {
        1: [...],  # Direct connections
        2: [...]   # Second-order connections
    },
    'causal_entities': [...]  # Entities with causal links
}
```

### 3. get_causal_chain

```python
await get_causal_chain(
    entity_name: str,    # Starting entity
    max_depth: int = 5   # Maximum chain length
)
```

Returns:
```python
{
    'root_entity': 'entity_name',
    'chain_length': 3,
    'max_depth_reached': 3,
    'causal_chain': [
        {
            'entity': 'next_entity',
            'type': 'outcome',
            'relationship': 'causes',
            'depth': 1,
            'strength': 0.85,
            'path': ['entity_name', 'next_entity']
        },
        ...
    ]
}
```

### 4. kg_hybrid_search

```python
await kg_hybrid_search(
    query: str,      # Search query
    depth: int = 2   # Graph expansion depth
)
```

Returns semantic matches + graph expansion:
```python
{
    'query': 'optimization',
    'semantic_results': 10,
    'total_connected_entities': 87,
    'results': [
        {
            'entity': {...},
            'connected_entities': 12,
            'context_depth': 2,
            'context_by_depth': {...}
        },
        ...
    ]
}
```

### 5. get_ontology_info

```python
await get_ontology_info()
```

Returns:
```python
{
    'entity_types': ['concept', 'episode', 'skill', ...],  # 20+ types
    'relation_types': ['causes', 'enables', ...],          # 25+ types
    'memory_tiers': ['working', 'episodic', 'semantic', 'procedural'],
    'validation_available': True
}
```

## Troubleshooting

### Issue: Migration fails

**Solution**:
```bash
# Check database isn't locked
lsof ~/.claude/enhanced_memories/memory.db

# If locked, restart MCP server first
# Then run migration
```

### Issue: Tests fail

**Solution**:
```bash
# Make sure you're in the right directory
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp

# Check Python path
which python3

# Run with verbose output
python3 test_knowledge_graph.py -v
```

### Issue: Tools not showing up

**Solution**:
```bash
# Check server logs for integration message
# Should see: "✅ Knowledge Graph tools integrated"

# If not, check import errors in server.py
# Make sure all dependencies are installed
```

## Next Steps

1. ✅ Run migration
2. ✅ Verify tests pass
3. ✅ Create your first causal relationship
4. ✅ Try hybrid search
5. ✅ Explore connected context

## Learn More

- Full documentation: `KNOWLEDGE_GRAPH_ENHANCEMENTS.md`
- Implementation details: `IMPLEMENTATION_SUMMARY.md`
- Source video: https://www.youtube.com/watch?v=ZNqGFsTyhvg

## Support

Having issues? Check:
1. Server logs for error messages
2. Migration report in `~/.claude/enhanced_memories/`
3. Test output for specific failures
4. Database backup location (automatic before migration)
