# MCP Integration Test Plan

## Test Sequence

### Test 1: Auto-Extract Facts
- Input: Sample conversation with preferences
- Expected: Facts extracted and stored with source attribution
- Verification: Entity IDs returned, database updated

### Test 2: Detect Conflicts
- Input: Similar entity data to Test 1 results
- Expected: Conflicts detected with overlap ratios
- Verification: Conflict type identified (duplicate/update)

### Test 3: Resolve Conflict
- Input: Conflict data from Test 2
- Expected: Entities merged/updated based on strategy
- Verification: Conflict logged in conflicts table

## Test Data

**Conversation Text**:
```
User: I prefer using voice communication for all interactions.
Assistant: Understood, I'll prioritize voice mode.
User: I always use parallel tool execution when possible.
Assistant: Got it, parallel execution preferred.
User: I need production-ready code only, no POCs.
Assistant: Production-only policy noted.
```

**Expected Extractions**:
- "I prefer using voice communication for all interactions."
- "I always use parallel tool execution when possible."
- "I need production-ready code only, no POCs."

## Execution Log

Test execution results will be appended below.

---
