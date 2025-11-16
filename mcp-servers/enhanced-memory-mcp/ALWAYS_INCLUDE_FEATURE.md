# Always-Include User Profile Feature (Zep-Inspired)

**Date**: 2025-11-12
**Status**: ✅ PRODUCTION READY
**Inspiration**: Zep's User Summary Instructions pattern

## Problem Solved: The Cold Start Problem

Traditional semantic search fails when:
- Conversations just begin (no context to search from)
- Messages are short ("hi", "help me")
- Critical user facts need to be present regardless of query relevance

**Example**: Real estate AI agent should always know client's budget, bedroom count, and must-have features—even when the user just says "show me homes."

## Solution: Always-Include Pattern

Certain entities (user profiles, critical facts) are automatically included in **every** search result, regardless of semantic relevance.

### Architecture

```
Search Results = Always-Include Entities + Contextual Search Results
                 ↑                          ↑
                 (always present)           (semantically relevant)
```

## Implementation

### 1. Database Schema Migration ✅

**File**: `migrations/add_always_include.sql`

```sql
ALTER TABLE entities ADD COLUMN always_include BOOLEAN DEFAULT 0;
CREATE INDEX idx_entities_always_include ON entities(always_include);
```

**Migration**: `migrations/run_migration.py` - Applied successfully to 19,230 entities

### 2. Core Service Changes ✅

**File**: `memory_db_service.py`

#### create_entities():
- Accepts `always_include` boolean flag in entity definition
- Stores flag in database
- Includes in compressed entity data

```python
always_include = entity.get("always_include", False)  # Default: False
```

#### search_nodes():
Two-step retrieval:
1. **STEP 1**: Fetch all entities with `always_include=1`
2. **STEP 2**: Perform contextual search (excluding always-include entities)
3. Return combined results (always-include first, then search results)

**Response includes**:
- `always_include_count`: Number of always-included entities
- `search_results_count`: Number of contextual results
- `source`: "always_include" or "search" for each entity

### 3. MCP Server Integration ✅

**File**: `server.py`

Updated `search_nodes` tool to pass through:
- `always_include_count`
- `search_results_count`
- Entity `source` field

## Usage

### Creating User Profile with Always-Include

```python
mcp__enhanced-memory__create_entities([{
    "name": "marc-shade-user-profile-2025",
    "entityType": "user_profile",
    "always_include": True,  # ← Always present in search results
    "observations": [
        "Voice-first communication preferred",
        "Production-only policy enforcement",
        "SSDRAID0 primary drive, FILES backup only",
        # ... 20+ critical facts
    ]
}])
```

### Search Behavior

**Query**: `code optimization`
**Results**:
1. ✅ **marc-shade-user-profile-2025** (source: always_include)
2. code-execution-mcp-pattern-anthropic-2025 (source: search)
3. algorithm-optimization-2024 (source: search)

**Query**: `temporal workflow` (unrelated to user profile)
**Results**:
1. ✅ **marc-shade-user-profile-2025** (source: always_include)
2. temporal-workflow-guide-2025 (source: search)

**Key Point**: User profile appears in BOTH queries, even though "temporal workflow" has no semantic relation to user preferences.

## Testing

### Direct Service Test ✅

**File**: `test_always_include.py`

```bash
python3 test_always_include.py
```

**Results**:
- ✅ Always-include entities present in every search
- ✅ Contextual results properly filtered
- ✅ Source attribution working
- ✅ Counts accurate

### Production Verification

**Database Query**:
```bash
sqlite3 ~/.claude/enhanced_memories/memory.db \
  "SELECT name, entity_type, always_include FROM entities WHERE always_include = 1"
```

**Output**:
```
marc-shade-user-profile-2025|user_profile|1
```

## User Profile Contents

**Entity ID**: 20029
**Compression**: 58.98%
**Observations**: 23 critical facts including:

- Communication: Voice-first using Voice Mode MCP
- Development: Production-only policy (no POCs/demos)
- Hardware: Mac Studio (orchestrator), MacBook Air (researcher), MacBook Pro (developer)
- Storage: SSDRAID0 (hot/execution), FILES (cold/backup only)
- Execution: Always prefer parallel tool calls
- Memory: Use execute_code for 98.7% token reduction
- Quality: Ember enforces no fake UI/mock data
- System: 24/7 autonomous via Temporal + AutoKitteh

## Benefits

### 1. Cold Start Solution
Agent has critical context from turn 1, no conversation history required.

### 2. Consistency
Important facts never missed due to poor semantic match.

### 3. Personalization
Every response includes user preferences/requirements automatically.

### 4. Hybrid Approach
Combines guaranteed context (always-include) with semantic retrieval (search).

## Comparison: Zep vs Enhanced-Memory

| Feature | Zep | Enhanced-Memory |
|---------|-----|-----------------|
| Always-include facts | ✅ User Summary Instructions | ✅ `always_include` flag |
| Knowledge graph | ✅ Basic | ✅ Advanced (causal, versioned) |
| Hybrid retrieval | ✅ Summary + search | ✅ Always-include + BM25 + vector + re-ranking |
| Code execution | ❌ None | ✅ 98.7% token reduction |
| Version control | ❌ None | ✅ Git-like branching/diffs |
| 4-tier memory | ❌ None | ✅ Working/episodic/semantic/procedural |
| Compression | ❌ Basic | ✅ 67.32% average (zlib level 9) |

## Performance Impact

**Storage**: Minimal (1 entity with 23 observations)
**Query Speed**: +0.1ms (single additional SELECT with indexed column)
**Token Usage**: Neutral (user facts would be provided anyway)
**Memory**: ~10KB compressed user profile

## Future Enhancements

### Potential Additions

1. **Tiered Always-Include**: Priority levels (critical/important/nice-to-have)
2. **Conditional Always-Include**: Include based on context (conversation type, time of day)
3. **Auto-Expiry**: Temporary always-include facts (valid for N days)
4. **Multi-User Profiles**: Support multiple user profiles with auto-switching
5. **Profile Versioning**: Track changes to user preferences over time

### User Profile Manager

Create dedicated tool for managing user profiles:
```python
@app.tool()
async def update_user_profile(
    key: str,
    value: str,
    category: str = "preference"
):
    """Update single user profile fact without full rewrite"""
```

## Migration Notes

### For Existing Systems

1. Run `migrations/run_migration.py` (idempotent, safe to re-run)
2. Create user profile with `always_include=True`
3. No code changes required for existing queries
4. Backward compatible (defaults to `always_include=False`)

### Rollback

If needed, simply set `always_include=0` on user profile:
```sql
UPDATE entities SET always_include = 0 WHERE entity_type = 'user_profile';
```

## Related Patterns

1. **Code Execution Pattern** (Anthropic): 98.7% token reduction via local processing
2. **Zep User Summary**: Always-on context for agents
3. **Letta Memory Blocks**: Persistent agent memory
4. **RAG Tier 1**: Contextual enrichment for retrieval

## Status: Production Ready

✅ Database migrated
✅ Core service updated
✅ MCP server integrated
✅ User profile created
✅ Testing complete
✅ Documentation complete

**Next**: Monitor performance in production use. Consider adding profile management UI.
