# Claude Code Async Background Agents

**Source**: YouTube video by [Creator] - Async Background Agents in Claude Code
**Date Analyzed**: 2025-12-19

## Overview

Claude Code now supports async background agents that allow you to run multiple AI tasks in parallel while continuing to work. This enables powerful workflows for code review, research, and parallel development.

## Core Features

### 1. Background Agent Execution (Ctrl+B)

Push any running agent to the background:
- Press `Ctrl+B` while an agent is running
- Agent continues execution asynchronously
- You regain control of the terminal immediately
- Check status with `/tasks` command

### 2. Git Worktrees Integration

**Why Worktrees?**: Allows working on multiple branches simultaneously in separate directories without switching branches.

```bash
# Create a worktree for parallel work
git worktree add ../feature-branch feature-branch

# List all worktrees
git worktree list

# Remove when done
git worktree remove ../feature-branch
```

**Use with background agents**: Each background agent can work in its own worktree, enabling true parallel development without conflicts.

### 3. Instant Autocompact

- Context compaction is now nearly instant (previously 2-3 minutes)
- Enables smoother long-running sessions
- Less interruption when hitting context limits

### 4. Session Forking (Escape x2)

Press **Escape twice** to fork current session:
- Creates a new session branch from current context
- Original session preserved
- Use `--resume` flag to continue forked sessions

### 5. Agent Flag (--agent)

Run Claude as a specific agent defined in your project:
```bash
claude --agent security-reviewer
claude --agent performance-analyst
```

## Use Cases

### Parallel Code Reviews

Run multiple specialized reviews simultaneously:

```bash
# Terminal 1: Security review
claude "Review this codebase for security vulnerabilities"
# Press Ctrl+B to background

# Terminal 2: Performance review
claude "Analyze performance bottlenecks in this code"
# Press Ctrl+B to background

# Terminal 3: Refactoring suggestions
claude "Suggest refactoring improvements for maintainability"
# Press Ctrl+B to background

# Check all tasks
/tasks
```

### Research While Coding

```bash
# Background: Research best practices
claude "Research current best practices for React state management"
# Press Ctrl+B

# Foreground: Continue implementation work
# Research results available when ready
```

### Simultaneous Component Updates

Update multiple related components in parallel:

```bash
# Create worktrees for isolation
git worktree add ../auth-update feature/auth
git worktree add ../api-update feature/api

# Run agents in each worktree
cd ../auth-update && claude "Update authentication module" &
cd ../api-update && claude "Update API endpoints" &
```

## Best Practices

### DO:

1. **Use for isolated tasks** - Tasks that don't need immediate feedback
2. **Provide descriptive names** - Clear agent names help track parallel work
3. **Monitor token usage** - Background agents still consume tokens
4. **Use worktrees** - Prevent file conflicts between parallel agents
5. **Check status regularly** - Use `/tasks` to monitor progress

### DON'T:

1. **Don't background tasks requiring input** - Agent will hang waiting for approval
2. **Don't background dependent tasks** - Tasks that need results from other tasks
3. **Don't run too many parallel agents** - Resource and token limits apply
4. **Don't forget to check results** - Background agents complete silently

## Workflow Patterns

### Pattern 1: Review Swarm

```
┌─────────────────────────────────────────────────┐
│                 Code Change                      │
└─────────────────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Security   │ │ Performance │ │   Quality   │
│   Review    │ │   Review    │ │   Review    │
│  (Ctrl+B)   │ │  (Ctrl+B)   │ │  (Ctrl+B)   │
└─────────────┘ └─────────────┘ └─────────────┘
       │               │               │
       └───────────────┼───────────────┘
                       ▼
┌─────────────────────────────────────────────────┐
│           Consolidated Report (/tasks)           │
└─────────────────────────────────────────────────┘
```

### Pattern 2: Research-Implement Pipeline

```
┌─────────────────────────────────────────────────┐
│ Background: Research best practices (Ctrl+B)     │
└─────────────────────────────────────────────────┘
                       │
                       ▼ (async)
┌─────────────────────────────────────────────────┐
│ Foreground: Implement based on existing knowledge│
└─────────────────────────────────────────────────┘
                       │
                       ▼ (when research completes)
┌─────────────────────────────────────────────────┐
│ Refine implementation with research findings     │
└─────────────────────────────────────────────────┘
```

### Pattern 3: Parallel Feature Development

```
┌──────────────────────────────────────────────────┐
│               Main Branch                         │
└──────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Worktree A  │    │  Worktree B  │    │  Worktree C  │
│  Feature 1   │    │  Feature 2   │    │  Feature 3   │
│  (Agent 1)   │    │  (Agent 2)   │    │  (Agent 3)   │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             ▼
┌──────────────────────────────────────────────────┐
│          Merge to Main (git merge)                │
└──────────────────────────────────────────────────┘
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `Ctrl+B` | Push current agent to background |
| `/tasks` | List all running/completed background tasks |
| `Escape x2` | Fork current session |
| `--agent NAME` | Run as specific agent |
| `--resume ID` | Resume a forked/backgrounded session |

## Integration with Existing Workflows

### With Git Worktrees

```bash
# Setup script for parallel development
#!/bin/bash
BRANCHES=("feature/auth" "feature/api" "feature/ui")

for branch in "${BRANCHES[@]}"; do
    git worktree add "../${branch##*/}" "$branch"
done

echo "Worktrees created. Run agents in each directory."
```

### With TodoWrite Tool

```python
# Track background agent tasks
todos = [
    {"content": "Security review (background)", "status": "in_progress"},
    {"content": "Performance review (background)", "status": "in_progress"},
    {"content": "Quality review (background)", "status": "in_progress"},
]
TodoWrite(todos=todos)
```

### With Agent Runtime MCP

```python
# Create persistent goals for background work
mcp__agent-runtime-mcp__create_goal({
    "name": "Parallel Code Review",
    "description": "Run security, performance, and quality reviews in parallel"
})
```

## Token Considerations

- Background agents consume tokens like foreground agents
- Multiple parallel agents multiply token usage
- Use `/cost` to monitor spending
- Consider batching related work instead of many small agents

## Limitations

1. **No real-time interaction** - Can't approve/reject in background
2. **Resource bounds** - System limits on parallel processes
3. **Context isolation** - Each agent has separate context
4. **No auto-merge** - Manual integration of parallel work required

## Related Features

- **Kenny's Parallel Agent Pattern**: Spawn multiple sub-agents with Task tool
- **Swarm Orchestration**: Full multi-agent coordination
- **AutoKitteh Workflows**: Event-driven parallel execution

---

*This document was generated from video transcript analysis. Patterns and features may evolve with Claude Code updates.*
