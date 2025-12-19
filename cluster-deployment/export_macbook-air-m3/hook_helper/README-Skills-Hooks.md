# Skills Coordination Hooks

These hooks enable automatic Skills suggestions and optimization guidance.

## Hooks

### 1. skills-coordinator.py
**Event**: PreToolUse
**Purpose**: Suggest relevant Skills before tool execution
**Behavior**: Non-blocking (provides suggestions via stderr)

**Triggers**:
- Read/Grep/Glob → Suggests Explore Integration
- Project/pattern keywords → Suggests Memory Orchestration
- Claude Code terms → Suggests Claude Docs Query
- Task tool → Suggests Agentic Orchestration

**Output**: Suggestions printed to stderr, doesn't block execution

### 2. skills-activation.py
**Event**: SessionStart
**Purpose**: Provide Skills guidance at session start
**Behavior**: Non-blocking (provides suggestions via stderr)

**Detects**:
- Keyword matches for each Skill
- Task type (research, implementation, large-scale, help)
- Recommends top 3 relevant Skills

**Output**: Skills recommendations and usage tips

## Installation

Hooks are automatically discovered from `.claude/hooks/` directory if they:
1. Have `.py` extension
2. Are executable (`chmod +x`)
3. Are configured in settings.json

### Settings Configuration

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "command": "python3",
        "args": ["/Users/marc/.claude/hooks/skills-coordinator.py"]
      }
    ],
    "SessionStart": [
      {
        "command": "python3",
        "args": ["/Users/marc/.claude/hooks/skills-activation.py"]
      }
    ]
  }
}
```

## Skills Covered

1. **Agentic Orchestration** - Multi-agent coordination
2. **Context Optimization** - Context management and Explore
3. **Memory Orchestration** - Cross-session knowledge
4. **Explore Integration** - Efficient codebase searching
5. **Claude Docs Query** - Documentation reference

## Hook Behavior

### Non-Blocking
- All suggestions sent to stderr
- Tool execution proceeds normally
- No performance impact

### Contextual
- Analyzes tool parameters
- Detects user intent
- Provides relevant suggestions only

### Educational
- Teaches Skills usage patterns
- Shows alternative approaches
- Provides implementation examples

## Examples

### Example 1: Grep Trigger
```
User runs: Grep(pattern="auth", path="src/")

Hook suggests:
# Skills Coordinator Suggestions:
#   - Explore Integration: Consider using Explore subagent for context-efficient searching
#     Alternative: Task(subagent_type='Explore', prompt='Find auth-related files')
```

### Example 2: Session Start
```
User starts session: "Find all authentication code in the codebase"

Hook suggests:
# Agent Skills Available:
#   Explore Integration: Efficiently search codebase without loading files
#   Use when: Searching for code patterns or understanding structure

# Recommended Skills for this task:
#   Research task detected
#   Consider: Explore Integration, Memory Orchestration, Claude Docs Query
#   Why: Research tasks benefit from efficient searching and knowledge retrieval
```

### Example 3: Documentation Query
```
User message includes: "how to create a subagent"

Hook suggests:
# Skills Coordinator Suggestions:
#   - Claude Docs Query: Check indexed documentation for official guidance
#     Alternative: mcp__enhanced-memory-mcp__search_nodes(query='subagent configuration', entity_types=['documentation'])
```

## Disabling Hooks

To disable temporarily:
1. Remove from settings.json hooks configuration
2. Or rename file to add `.disabled` extension
3. Or make non-executable: `chmod -x hook.py`

## Development

Hooks receive JSON input via stdin:
```json
{
  "event": "PreToolUse",
  "toolName": "Read",
  "params": {"file_path": "/path/to/file"},
  "session": {...}
}
```

Exit codes:
- 0: Allow execution (normal)
- Non-zero: Block execution (use with caution)

## Performance

- Minimal overhead (~10ms per hook)
- No network calls
- No file I/O in critical path
- Safe for production use

## Integration

Works with:
- All 5 Agent Skills
- Enhanced Memory MCP
- Task tool and subagents
- Context optimization system

## Future Enhancements

Potential additions:
- Skills usage analytics
- Learning from user feedback
- Custom trigger patterns
- Performance monitoring
