# Ember MCP Enhanced - Version 2.0

## Overview

Enhanced Ember MCP with improved violation detection, context-aware scoring, learning capabilities, and better user experience.

## What's New

### 1. **Inline Suggestions with Better Messages**

**Before:**
```
Production policy violation detected (score: 5.0)
Violation type: smart_violation_detected
Severity: moderate
```

**After:**
```
⚠️  CAUTION (5.0/10): Writing to hooks directory

Issue: Hooks execute on every tool use - bugs could break system
Impact: Could crash Claude Code or create infinite loops
Suggestion: Create utility in project directory instead
Safe alternative: Use /Volumes/SSDRAID0/.../intelligent-self-healing/ or /tools/

Proceed with caution. This will be logged.
```

### 2. **Context-Aware Scoring**

Violations are now scored based on:
- **Action type**: Write vs Edit vs Read
- **Task context**: development, testing, monitoring, refactoring
- **Recent actions**: Pattern detection
- **Learned patterns**: From user corrections

**Example:**
- Writing to `/hooks/` during monitoring task: 3.0/10 (was 5.0)
- Same action during unknown task: 5.0/10
- Same action for system modification: 7.0/10

### 3. **Progressive Warnings**

- **0-4.9**: No warning (clean)
- **5.0-7.9**: ⚠️  Warning but allow (logged)
- **8.0-10.0**: 🚫 BLOCKED (prevents action)

### 4. **Learning from Corrections**

New tool: `ember_learn_from_correction`

When you override Ember's assessment:
```javascript
ember_learn_from_correction({
  originalViolationType: "system_interference",
  userCorrection: "This is a utility tool, not a hook",
  wasCorrect: false,  // Ember was wrong
  context: "statusline development"
})
```

Ember learns and adjusts future scores for similar patterns (-2.0 adjustment).

### 5. **Session Context Awareness**

Feed context to improve scoring:
```javascript
ember_feed_context({
  context: {
    task: "Building statusline monitoring",
    taskType: "monitoring",  // or 'development', 'testing', 'refactoring'
    goal: "Add token usage tracking"
  }
})
```

Ember adjusts violation scores based on task type.

### 6. **Enhanced Violation Patterns**

Six detailed patterns with full explanations:
1. Mock/fake data (8.0/10)
2. Hardcoded credentials (7.0/10)
3. POC code (8.0/10)
4. Incomplete work markers (3.0/10)
5. Placeholder content (8.0/10)
6. System interference (5.0/10 base, context-aware)

## New Tools

### `ember_learn_from_correction`
Tell Ember when it was wrong, helping it learn and improve.

**Parameters:**
- `originalViolationType`: What was flagged
- `userCorrection`: Why you proceeded
- `wasCorrect`: Was Ember right? (false = Ember learns)
- `context`: What was the actual situation

### `ember_get_learning_stats`
View Ember's learning progress and pattern adjustments.

**Returns:**
```json
{
  "totalLearnings": 5,
  "patterns": {
    "system_interference": {
      "count": 3,
      "totalAdjustment": -6.0
    }
  },
  "sessionContext": {...},
  "recentLearnings": [...]
}
```

## Enhanced Existing Tools

### `ember_feed_context` (Enhanced)
Now supports `taskType` for context-aware scoring:
- `development`: Building new features
- `testing`: Writing tests
- `monitoring`: System monitoring tools
- `refactoring`: Code cleanup
- `unknown`: Default

### `ember_check_violation` (Enhanced)
Returns richer information:
```json
{
  "hasViolations": true,
  "violations": [{
    "type": "system_interference",
    "baseScore": 5.0,
    "contextScore": 3.0,  // Adjusted for context
    "reason": "Writing to hooks directory",
    "suggestion": "Create utility in project directory instead",
    "risk": "Hooks execute on every tool use - bugs could break system",
    "impact": "Could crash Claude Code or create infinite loops",
    "safeAlternative": "Use project directory",
    "shouldBlock": false  // 3.0 < 8.0
  }],
  "highestScore": 3.0,
  "shouldBlock": false,
  "message": "..."
}
```

## File Locations

### Code
- **Source**: `/Volumes/SSDRAID0/agentic-system/mcp-servers/ember-mcp/src/index.ts`
- **Compiled**: `/Volumes/SSDRAID0/agentic-system/mcp-servers/ember-mcp/dist/index.js`
- **Backup**: `/Volumes/SSDRAID0/agentic-system/mcp-servers/ember-mcp/src/index-original-backup.ts`

### Data Files
- **Session context**: `~/.claude/pets/ember-session-context.json`
- **Learning log**: `~/.claude/pets/ember-learning.jsonl`
- **Feedback log**: `~/.claude/pets/ember-feedback.jsonl`

### Tests
- **Test script**: `/Volumes/SSDRAID0/agentic-system/mcp-servers/ember-mcp/tests/test-enhanced-ember.sh`
- **Test session**: `tmux attach -t ember-enhanced-test`

## Testing

### Run Test Suite
```bash
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/ember-mcp/tests
./test-enhanced-ember.sh
```

### Attach to Test Session
```bash
tmux attach -t ember-enhanced-test
```

### Test Cases
1. **Context-aware scoring**: Compare hooks vs project directory
2. **Inline suggestions**: Verify rich error messages
3. **Progressive warnings**: Test 5.0 (warn) vs 8.0+ (block)
4. **Learning**: Correct Ember and verify adjustment
5. **Session context**: Set taskType and verify score changes

## Migration from V1

The enhanced version is **backward compatible**. All existing tools still work.

**No breaking changes:**
- `ember_chat` - Same
- `ember_check_violation` - Enhanced but compatible
- `ember_consult` - Same
- `ember_get_feedback` - Same
- `ember_learn_from_outcome` - Same
- `ember_get_mood` - Same
- `ember_feed_context` - Enhanced but compatible

**New tools:**
- `ember_learn_from_correction` (optional)
- `ember_get_learning_stats` (optional)

## Performance

- **No latency impact**: Scoring is instant (no LLM calls for violations)
- **Learning storage**: JSONL append-only (fast)
- **Session context**: Single JSON file read/write
- **Memory footprint**: ~100KB for typical session

## Benefits

1. **Better UX**: Clear explanations instead of cryptic errors
2. **Smarter**: Learns from your corrections
3. **Context-aware**: Understands what you're building
4. **Progressive**: Warns before blocking
5. **Informative**: Tells you WHY and suggests HOW

## Example Workflow

```javascript
// 1. Start session - set context
ember_feed_context({
  context: {
    task: "Building token usage tracker",
    taskType: "monitoring"
  }
})

// 2. Phoenix tries to write file
// Ember checks with context-aware scoring
// Score: 3.0/10 (reduced from 5.0 due to 'monitoring' task)
// Result: ⚠️  Warning but allowed

// 3. User proceeds successfully
// Phoenix can optionally teach Ember:
ember_learn_from_correction({
  originalViolationType: "system_interference",
  userCorrection: "This was safe - metadata only, no content reading",
  wasCorrect: false,
  context: "statusline monitoring tool"
})

// 4. Ember learns: -2.0 adjustment for similar patterns
// 5. Next time: score drops from 3.0 to 1.0 for similar actions
```

## Status

✅ **Production Ready**
- All improvements implemented
- Backward compatible
- Tested and compiled
- Documentation complete

## Next Steps

1. Restart Claude Code to load enhanced Ember
2. Try the test cases in tmux session
3. Use `ember_feed_context` at session start
4. Teach Ember when it's wrong with `ember_learn_from_correction`
5. Monitor learning with `ember_get_learning_stats`

---

**Version**: 2.0.0
**Date**: 2025-11-08
**Status**: Production Ready ✅
