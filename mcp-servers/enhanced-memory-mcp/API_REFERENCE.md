# Enhanced Memory System - API Reference

**Version**: 2.0
**Protocol**: MCP (Model Context Protocol)
**Total Tools**: 12
**Date**: 2025-11-12

## Table of Contents

1. [Core Operations](#core-operations)
2. [Automatic Extraction](#automatic-extraction)
3. [Conflict Management](#conflict-management)
4. [Version Control](#version-control)
5. [Code Execution](#code-execution)
6. [System Management](#system-management)

---

## Core Operations

### 1. create_entities

Create or update memory entities with compression and source tracking.

**Signature**:
```python
async def create_entities(entities: List[Dict]) -> Dict
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| entities | List[Dict] | Yes | List of entity objects |

**Entity Object**:
```json
{
  "name": "unique-entity-name",
  "entityType": "type_category",
  "observations": ["fact 1", "fact 2", "fact 3"],
  "always_include": false,
  "source_session": "session-id",
  "extraction_method": "manual",
  "relevance_score": 1.0
}
```

**Returns**:
```json
{
  "success": true,
  "results": [
    {
      "id": 12345,
      "name": "unique-entity-name",
      "action": "created",
      "compression": 0.67
    }
  ],
  "errors": []
}
```

**Example**:
```python
result = await create_entities([
    {
        "name": "user-preferences-2025",
        "entityType": "preference",
        "observations": [
            "Prefers voice communication",
            "Uses parallel tool execution",
            "Production-only policy"
        ],
        "always_include": true
    }
])

print(f"Entity ID: {result['results'][0]['id']}")
print(f"Compression: {result['results'][0]['compression']:.2%}")
```

**Performance**:
- Single entity: ~25ms
- Batch of 10: ~80ms
- Batch of 100: ~500ms

**Notes**:
- If entity with same name exists, it's updated (version incremented)
- Observations automatically compressed (avg 67% reduction)
- Checksum calculated for integrity verification

---

### 2. search_nodes

Search for entities by name or type with fuzzy matching.

**Signature**:
```python
async def search_nodes(query: str, limit: int = 10) -> Dict
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | str | Yes | - | Search string (name or type) |
| limit | int | No | 10 | Maximum results to return |

**Returns**:
```json
{
  "query": "preference",
  "count": 5,
  "results": [
    {
      "id": 12345,
      "name": "user-preferences-2025",
      "type": "preference",
      "observations": ["fact 1", "fact 2"],
      "compression": 0.67,
      "version": 1,
      "branch": "main",
      "created": "2025-11-12T10:00:00",
      "accessed": "2025-11-12T15:30:00",
      "access_count": 5
    }
  ]
}
```

**Example**:
```python
# Search by type
results = await search_nodes("preference", limit=50)
print(f"Found {results['count']} preferences")

# Search by name
results = await search_nodes("user-", limit=10)

# Get all entities (with limit)
results = await search_nodes("", limit=1000)
```

**Search Behavior**:
- Matches against both `name` and `entity_type` fields
- Uses SQL `LIKE %query%` (case-insensitive)
- Orders by access_count DESC, then last_accessed DESC
- Always-include entities returned first

**Performance**:
- 10 results: ~15ms
- 100 results: ~45ms
- 1000 results: ~200ms (with compression overhead)

---

## Automatic Extraction

### 3. auto_extract_facts

Automatically extract facts from conversation text using pattern matching.

**Signature**:
```python
async def auto_extract_facts(
    conversation_text: str,
    session_id: Optional[str] = None,
    auto_store: bool = True,
    extraction_context: Optional[str] = None
) -> Dict
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| conversation_text | str | Yes | - | Conversation to analyze |
| session_id | str | No | None | Session identifier |
| auto_store | bool | No | True | Whether to store extracted facts |
| extraction_context | str | No | None | Additional context for extraction |

**Returns**:
```json
{
  "success": true,
  "facts": [
    {
      "name": "auto-extracted-session-001-20251112",
      "entityType": "auto_extracted",
      "observations": [
        "User prefers voice communication",
        "User always uses parallel execution"
      ],
      "source_session": "session-001",
      "extraction_method": "auto"
    }
  ],
  "stored": true,
  "count": 1,
  "entity_ids": [12346],
  "session_id": "session-001"
}
```

**Example**:
```python
conversation = """
User: I prefer using voice communication for all interactions.
Assistant: Understood.
User: I always use parallel tool execution when possible.
Assistant: Got it.
User: I need production-ready code only, no POCs.
"""

result = await auto_extract_facts(
    conversation_text=conversation,
    session_id="session-2025-11-12",
    auto_store=True
)

print(f"Extracted {result['count']} facts")
print(f"Entity ID: {result['entity_ids'][0]}")
```

**Extraction Pattern**:

Keywords detected:
- Preferences: `prefer`, `like`, `love`, `hate`, `dislike`
- Requirements: `need`, `want`, `require`, `must`
- Always/Never: `always`, `never`, `every time`
- Usage: `use`, `utilize`, `employ`

**Performance**:
- Typical conversation (100 lines): ~50ms
- Large conversation (1000 lines): ~200ms

**Future Enhancement** (Phase 2):
- LLM-powered extraction (90%+ accuracy)
- Semantic fact extraction
- Entity relationship extraction

---

## Conflict Management

### 4. detect_conflicts

Detect if an entity conflicts with existing entities using observation overlap.

**Signature**:
```python
async def detect_conflicts(
    entity_name: str = None,
    entity_data: Optional[Dict] = None,
    threshold: float = 0.85
) -> Dict
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| entity_name | str | No | None | Existing entity to check |
| entity_data | Dict | No | None | New entity data to check |
| threshold | float | No | 0.85 | Overlap threshold (0.0-1.0) |

**Returns**:
```json
{
  "success": true,
  "conflicts": [
    {
      "existing_entity": "user-preferences-2024",
      "existing_id": 12340,
      "conflict_type": "duplicate",
      "confidence": 0.87,
      "suggested_action": "merge",
      "details": "3 overlapping observations out of 4"
    }
  ],
  "conflict_count": 1,
  "entity_name": "user-preferences-2025"
}
```

**Conflict Types**:

| Overlap Ratio | Type | Suggested Action | Description |
|---------------|------|------------------|-------------|
| > 0.85 | duplicate | merge | High overlap, likely same entity |
| 0.30 - 0.85 | update | update | Partial overlap, possible newer version |
| < 0.30 | different | ignore | Low overlap, distinct entities |

**Example**:
```python
# Check new entity before storing
new_entity = {
    "name": "user-prefs-v2",
    "entityType": "preference",
    "observations": [
        "Prefers voice",
        "Uses parallel execution"
    ]
}

conflicts = await detect_conflicts(
    entity_data=new_entity,
    threshold=0.50  # Lower threshold to catch more
)

if conflicts["conflict_count"] > 0:
    print(f"Found {conflicts['conflict_count']} conflicts")
    for conflict in conflicts["conflicts"]:
        print(f"  - {conflict['existing_entity']}: {conflict['conflict_type']}")
```

**Performance**:
- Single entity check: ~80ms
- With 100 similar entities: ~180ms
- With 1000 similar entities: ~350ms

**Algorithm**:
```
overlap_ratio = |intersection(obs1, obs2)| / max(|obs1|, |obs2|)
```

---

### 5. resolve_conflict

Resolve detected conflicts using merge, update, or branch strategies.

**Signature**:
```python
async def resolve_conflict(
    conflict_data: Dict,
    strategy: str = "auto"
) -> Dict
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| conflict_data | Dict | Yes | - | Conflict information from detect_conflicts |
| strategy | str | No | "auto" | Resolution strategy: merge/update/branch/auto |

**Conflict Data Format**:
```json
{
  "entity_id": 12346,
  "existing_id": 12340,
  "conflict_type": "duplicate",
  "confidence": 0.87
}
```

**Strategies**:

**1. Merge** (Combine entities):
```python
# Combines observations from both entities
# Marks secondary entity as merged (soft delete)
# Updates primary entity with combined data
```

**2. Update** (Adjust relevance):
```python
# Newer entity: relevance_score = 1.0
# Older entity: relevance_score = 0.7
# Both remain in database
```

**3. Branch** (Create version):
```python
# Creates new branch for experimental changes
# Preserves both versions separately
# Allows switching between branches
```

**4. Auto** (System decides):
```python
# Duplicate → merge
# Update → update scores
# Other → branch
```

**Returns**:
```json
{
  "success": true,
  "action_taken": "Merged user-prefs-v2 into user-preferences-2024",
  "strategy": "merge",
  "updated_entities": ["user-prefs-v2", "user-preferences-2024"],
  "details": "Combined 6 observations total"
}
```

**Example**:
```python
# Detect conflicts first
conflicts = await detect_conflicts(entity_data=new_entity)

if conflicts["conflict_count"] > 0:
    # Resolve first conflict
    conflict = conflicts["conflicts"][0]

    resolution = await resolve_conflict(
        conflict_data={
            "entity_id": new_entity_id,
            "existing_id": conflict["existing_id"],
            "conflict_type": conflict["conflict_type"],
            "confidence": conflict["confidence"]
        },
        strategy="auto"  # Let system decide
    )

    print(f"Resolution: {resolution['action_taken']}")
```

**Performance**:
- Merge: ~100ms (includes database updates)
- Update: ~50ms (updates relevance scores)
- Branch: ~80ms (creates branch record)

---

## Version Control

### 6. memory_diff

Show differences between two versions of an entity (like git diff).

**Signature**:
```python
async def memory_diff(
    entity_name: str,
    version1: int = None,
    version2: int = None
) -> Dict
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| entity_name | str | Yes | - | Entity to diff |
| version1 | int | No | current-1 | First version number |
| version2 | int | No | current | Second version number |

**Returns**:
```json
{
  "entity": "user-preferences-2025",
  "version1": {
    "version": 1,
    "observations": ["fact 1", "fact 2"],
    "created": "2025-11-01T10:00:00"
  },
  "version2": {
    "version": 2,
    "observations": ["fact 1", "fact 2", "fact 3"],
    "created": "2025-11-12T10:00:00"
  },
  "differences": {
    "added_observations": ["fact 3"],
    "removed_observations": [],
    "modified_metadata": {}
  }
}
```

**Example**:
```python
# Compare last two versions
diff = await memory_diff("user-preferences-2025")

print(f"Added: {len(diff['differences']['added_observations'])} observations")
print(f"Removed: {len(diff['differences']['removed_observations'])} observations")

# Compare specific versions
diff = await memory_diff("user-preferences-2025", version1=1, version2=5)
```

**Performance**: ~30ms per diff

---

### 7. memory_revert

Restore entity to a specific version (like git checkout).

**Signature**:
```python
async def memory_revert(entity_name: str, version: int) -> Dict
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| entity_name | str | Yes | Entity to revert |
| version | int | Yes | Version number to restore |

**Returns**:
```json
{
  "success": true,
  "entity": "user-preferences-2025",
  "reverted_to": 3,
  "new_version": 6,
  "details": "Reverted to version 3, created new version 6"
}
```

**Example**:
```python
# Revert to version 3
result = await memory_revert("user-preferences-2025", version=3)

print(f"Reverted to version {result['reverted_to']}")
print(f"New version: {result['new_version']}")
```

**Note**: Revert creates a new version (doesn't delete history).

**Performance**: ~50ms

---

### 8. memory_branch

Create an experimental branch for an entity (like git branch).

**Signature**:
```python
async def memory_branch(
    entity_name: str,
    branch_name: str,
    description: str = None
) -> Dict
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| entity_name | str | Yes | Entity to branch |
| branch_name | str | Yes | Branch name |
| description | str | No | Branch description |

**Returns**:
```json
{
  "success": true,
  "entity": "user-preferences-2025",
  "branch_name": "experiment-voice-only",
  "branch_id": 42,
  "created_from_version": 5
}
```

**Example**:
```python
# Create experimental branch
result = await memory_branch(
    entity_name="user-preferences-2025",
    branch_name="experiment-voice-only",
    description="Testing voice-only communication"
)

# Make changes to branch
# ... changes happen ...

# Switch back to main
# ... (not yet implemented, coming in Phase 2)
```

**Use Cases**:
- A/B testing different memory configurations
- Experimental changes without affecting main
- Rollback-safe modifications

**Performance**: ~30ms

---

## Code Execution

### 9. execute_code

Execute Python code in a restricted sandbox for bulk operations.

**Signature**:
```python
async def execute_code(
    code: str,
    context_vars: Optional[Dict] = None
) -> Dict
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| code | str | Yes | - | Python code to execute |
| context_vars | Dict | No | None | Additional variables |

**Available APIs in Sandbox**:

```python
# Memory Operations
create_entities(entities)
search_nodes(query, limit)
update_entity(id, data)
get_status()

# Versioning
diff(entity_name, v1, v2)
revert(entity_name, version)
branch(entity_name, branch_name)

# Analysis Utils
filter_by_confidence(results, threshold)
summarize_results(results)
aggregate_stats(results)

# Filesystem (workspace only)
workspace  # Path object
read_file(filename)
write_file(filename, content)
delete_file(filename)

# Skills
save_skill(name, code, description)
load_skill(name)
list_skills()

# Python Builtins (safe subset)
len, sum, min, max, sorted, set, list, dict
str, int, float, bool
enumerate, zip, range
json  # JSON module
```

**Returns**:
```json
{
  "success": true,
  "result": {
    "total": 1234,
    "high_quality": 456,
    "avg_compression": 0.67
  },
  "execution_time_ms": 234,
  "memory_used_mb": 12.5
}
```

**Example 1: Bulk Analysis**
```python
code = """
# Search all preferences
results = search_nodes("preference", limit=1000)

# Filter high quality
high_quality = [r for r in results if r.get('relevance_score', 0) > 0.8]

# Group by type
by_type = {}
for r in high_quality:
    type_name = r.get('type', 'unknown')
    by_type.setdefault(type_name, []).append(r)

# Return summary (not full data)
result = {
    'total': len(results),
    'high_quality': len(high_quality),
    'types': {k: len(v) for k, v in by_type.items()}
}
"""

output = await execute_code(code)
print(output["result"])
# {'total': 1234, 'high_quality': 456, 'types': {...}}
```

**Example 2: Save Reusable Skill**
```python
code = """
def analyze_by_type(query, threshold=0.8):
    '''Analyze and group entities by type with quality filter'''
    results = search_nodes(query, limit=1000)
    filtered = [r for r in results if r.get('relevance_score', 0) > threshold]

    by_type = {}
    for r in filtered:
        by_type.setdefault(r['type'], []).append(r)

    return {
        'total': len(results),
        'filtered': len(filtered),
        'by_type': {k: len(v) for k, v in by_type.items()}
    }

# Save for reuse
save_skill('analyze_by_type', analyze_by_type, 'Group by type with quality filter')

# Use it
result = analyze_by_type('system', 0.9)
"""

output = await execute_code(code)
```

**Security**:
- RestrictedPython compilation (no unsafe operations)
- 30-second timeout
- 500MB memory limit
- No network access
- Filesystem access limited to /tmp/memory-workspace

**Performance**:
- Simple operations: ~50ms
- Complex analysis: ~500ms
- Very large datasets (10k+ entities): ~5s

**Token Savings**: 98.7% reduction (50,000 → 500 tokens)

---

## System Management

### 10. get_memory_status

Get comprehensive system statistics and health information.

**Signature**:
```python
async def get_memory_status() -> Dict
```

**Returns**:
```json
{
  "total_entities": 19789,
  "by_type": {
    "agent_observation": 18386,
    "service_event": 153,
    "claude_code_documentation": 48
  },
  "by_tier": {
    "working": 18434,
    "episodic": 57,
    "semantic": 1263,
    "procedural": 35
  },
  "compression": {
    "avg_ratio": 0.67,
    "total_original_mb": 45.2,
    "total_compressed_mb": 15.2,
    "savings_mb": 30.0,
    "savings_pct": 67
  },
  "versioning": {
    "total_versions": 1234,
    "total_branches": 15,
    "avg_versions_per_entity": 1.2
  },
  "database_size_mb": 15.2,
  "always_include_count": 1,
  "auto_extracted_count": 2
}
```

**Example**:
```python
status = await get_memory_status()

print(f"Total entities: {status['total_entities']:,}")
print(f"Compression: {status['compression']['avg_ratio']:.2%}")
print(f"Storage savings: {status['compression']['savings_mb']:.1f} MB")
print(f"Database size: {status['database_size_mb']:.1f} MB")

# By type
print("\nTop 5 entity types:")
for entity_type, count in list(status['by_type'].items())[:5]:
    print(f"  {entity_type}: {count:,}")
```

**Performance**: ~50ms

---

### 11. detect_memory_conflicts

Detect all conflicts across the entire memory system.

**Signature**:
```python
async def detect_memory_conflicts(threshold: float = 0.85) -> Dict
```

**Parameters**:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| threshold | float | No | 0.85 | Overlap threshold |

**Returns**:
```json
{
  "success": true,
  "conflicts": [
    {
      "entity1": "user-prefs-2024",
      "entity2": "user-prefs-2025",
      "entity1_id": 100,
      "entity2_id": 200,
      "conflict_type": "duplicate",
      "confidence": 0.89,
      "suggested_action": "merge"
    }
  ],
  "total_conflicts": 15,
  "by_type": {
    "duplicate": 10,
    "update": 5
  }
}
```

**Example**:
```python
# Find all conflicts
conflicts = await detect_memory_conflicts(threshold=0.50)

print(f"Found {conflicts['total_conflicts']} conflicts")
print(f"Duplicates: {conflicts['by_type']['duplicate']}")
print(f"Updates: {conflicts['by_type']['update']}")

# Resolve all duplicates
for conflict in conflicts['conflicts']:
    if conflict['conflict_type'] == 'duplicate':
        await resolve_conflict(conflict, strategy='merge')
```

**Performance**:
- 1,000 entities: ~5s
- 10,000 entities: ~30s
- 100,000 entities: ~5min

**Note**: Run periodically (e.g., daily) for system maintenance.

---

### 12. save_implementation_plan

Save structured implementation plans for complex projects.

**Signature**:
```python
async def save_implementation_plan(
    name: str,
    steps: List[Dict],
    description: str = None
) -> Dict
```

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| name | str | Yes | Plan name |
| steps | List[Dict] | Yes | Implementation steps |
| description | str | No | Plan description |

**Step Format**:
```json
{
  "step": 1,
  "title": "Database Setup",
  "description": "Create database schema",
  "estimated_time": "2 hours",
  "dependencies": [],
  "status": "pending"
}
```

**Returns**:
```json
{
  "success": true,
  "plan_id": 12347,
  "name": "feature-implementation-2025",
  "total_steps": 5,
  "estimated_time": "10 hours"
}
```

**Example**:
```python
plan = await save_implementation_plan(
    name="add-user-authentication",
    description="Implement user authentication system",
    steps=[
        {
            "step": 1,
            "title": "Database Schema",
            "description": "Add users and sessions tables",
            "estimated_time": "2 hours",
            "status": "pending"
        },
        {
            "step": 2,
            "title": "Authentication Logic",
            "description": "Implement JWT tokens",
            "estimated_time": "4 hours",
            "dependencies": [1],
            "status": "pending"
        },
        {
            "step": 3,
            "title": "API Endpoints",
            "description": "Create login/logout endpoints",
            "estimated_time": "3 hours",
            "dependencies": [2],
            "status": "pending"
        }
    ]
)

print(f"Plan saved: {plan['plan_id']}")
print(f"Total time: {plan['estimated_time']}")
```

**Performance**: ~50ms

---

## Error Handling

### Standard Error Format

All tools return errors in this format:

```json
{
  "success": false,
  "error": "Error description",
  "error_type": "ValueError",
  "details": "Additional error details"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Entity not found" | Invalid entity name | Check entity exists |
| "Database locked" | Concurrent access | Retry after 1s |
| "Compression failed" | Invalid data | Check data format |
| "Timeout exceeded" | Operation too slow | Reduce batch size |
| "Socket unavailable" | Service not running | Start memory-db service |

### Error Handling Example

```python
try:
    result = await create_entities([entity])

    if not result["success"]:
        print(f"Error: {result['error']}")
        # Handle error
    else:
        print(f"Created: {result['results'][0]['id']}")

except Exception as e:
    print(f"Unexpected error: {e}")
```

---

## Performance Summary

| Operation | Latency (p50) | Latency (p95) | Throughput |
|-----------|---------------|---------------|------------|
| create_entities (1) | 25ms | 45ms | 40 req/s |
| create_entities (10) | 80ms | 150ms | 12 req/s |
| search_nodes (10) | 15ms | 30ms | 66 req/s |
| search_nodes (100) | 45ms | 90ms | 22 req/s |
| auto_extract_facts | 50ms | 100ms | 20 req/s |
| detect_conflicts | 80ms | 180ms | 12 req/s |
| resolve_conflict | 100ms | 200ms | 10 req/s |
| memory_diff | 30ms | 60ms | 33 req/s |
| execute_code (simple) | 50ms | 100ms | 20 req/s |
| get_memory_status | 50ms | 100ms | 20 req/s |

---

## Best Practices

### 1. Batch Operations

```python
# ✅ GOOD: Batch create
await create_entities([entity1, entity2, entity3, ...])

# ❌ BAD: Individual creates
await create_entities([entity1])
await create_entities([entity2])
await create_entities([entity3])
```

### 2. Use Code Execution for Bulk

```python
# ✅ GOOD: Execute code locally
await execute_code("""
results = []
for i in range(1000):
    results.append(search_nodes(f"query-{i}"))
result = summarize_results(results)
""")

# ❌ BAD: 1000 individual tool calls
for i in range(1000):
    await search_nodes(f"query-{i}")
```

### 3. Check Conflicts Before Storing

```python
# ✅ GOOD: Check first
conflicts = await detect_conflicts(entity_data=new_entity)
if conflicts["conflict_count"] > 0:
    await resolve_conflict(conflicts["conflicts"][0])
else:
    await create_entities([new_entity])

# ❌ BAD: Store directly
await create_entities([new_entity])  # Might create duplicate
```

### 4. Error Handling

```python
# ✅ GOOD: Check success
result = await create_entities([entity])
if result["success"]:
    process_result(result)
else:
    handle_error(result["error"])

# ❌ BAD: Assume success
result = await create_entities([entity])
entity_id = result["results"][0]["id"]  # Might crash
```

---

**End of API Reference**

For more information:
- Technical Specification: MEMORY_SYSTEM_TECHNICAL_SPEC.md
- Implementation Guide: MEMORY_SYSTEM_IMPLEMENTATION_GUIDE.md
- Executive Summary: MEMORY_SYSTEM_EXECUTIVE_SUMMARY.md
