# Post-Restart Integration Test

Run this immediately after restarting Claude Code to verify the new MCP tools.

## Test Sequence

### Test 1: Auto-Extract Facts
```python
result = mcp__enhanced-memory__auto_extract_facts(
    conversation_text="""
User: I prefer using voice communication for all interactions.
Assistant: Understood, I'll prioritize voice mode.
User: I always use parallel tool execution when possible.
Assistant: Got it, parallel execution preferred.
User: I need production-ready code only, no POCs.
Assistant: Production-only policy noted.
""",
    session_id="post-restart-test-001",
    auto_store=True
)

# Expected output:
# {
#   "success": True,
#   "count": 3,
#   "stored": True,
#   "entity_ids": [20XXX],
#   "facts": [{"name": "auto-extracted-...", "entityType": "auto_extracted", "observations": [...]}]
# }
```

### Test 2: Detect Conflicts
```python
result = mcp__enhanced-memory__detect_conflicts(
    entity_data={
        "name": "test-duplicate-check",
        "entityType": "auto_extracted",
        "observations": [
            "I prefer using voice communication for all interactions.",
            "I always use parallel tool execution when possible."
        ]
    },
    threshold=0.50
)

# Expected output:
# {
#   "success": True,
#   "conflict_count": 1+,
#   "conflicts": [
#     {
#       "existing_entity": "auto-extracted-post-restart-test-001-...",
#       "conflict_type": "duplicate",
#       "confidence": 0.85+,
#       "suggested_action": "merge"
#     }
#   ]
# }
```

### Test 3: Resolve Conflict
```python
# Use entity_id from Test 1 and existing_id from Test 2
result = mcp__enhanced-memory__resolve_conflict(
    conflict_data={
        "entity_id": 20XXX,  # From Test 1
        "existing_id": 20YYY,  # From Test 2 conflicts
        "conflict_type": "duplicate",
        "confidence": 0.87
    },
    strategy="merge"
)

# Expected output:
# {
#   "success": True,
#   "action_taken": "Merged ... into ...",
#   "strategy": "merge",
#   "updated_entities": [...]
# }
```

### Test 4: Verify in Database
```bash
sqlite3 /Users/marc/.claude/enhanced_memories/memory.db <<EOF
-- Check auto-extracted entities
SELECT COUNT(*) FROM entities WHERE source_session = 'post-restart-test-001';

-- Check conflicts logged
SELECT COUNT(*) FROM conflicts WHERE resolution_status = 'resolved';

-- View recent auto-extracted
SELECT name, source_session, extraction_method, relevance_score
FROM entities
WHERE entity_type = 'auto_extracted'
ORDER BY created_at DESC
LIMIT 5;
EOF
```

## Success Criteria

- ✅ Test 1: 3+ observations extracted, entity created
- ✅ Test 2: 1+ conflicts detected with overlap > 50%
- ✅ Test 3: Entities merged, conflict logged
- ✅ Test 4: Database shows new entities and conflicts

## If Tests Fail

1. Check MCP server is running:
   ```bash
   ps aux | grep enhanced-memory-mcp | grep -v grep
   ```

2. Check tool registration:
   ```bash
   grep "async def auto_extract_facts" /Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp/server.py
   ```

3. View MCP logs:
   ```bash
   tail -50 ~/.claude/logs/mcp-enhanced-memory.log
   ```

4. Verify database schema:
   ```bash
   sqlite3 /Users/marc/.claude/enhanced_memories/memory.db "PRAGMA table_info(conflicts)"
   ```
