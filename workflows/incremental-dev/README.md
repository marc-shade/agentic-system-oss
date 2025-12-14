# Incremental Development Workflow

Context-aware incremental development workflow based on Anthropic's agent workflow research. Designed to prevent context exhaustion and ensure proper testing.

## Problem Solved

1. **Context Window Exhaustion** - Large tasks cause repeated compaction, losing progress
2. **Premature Completion** - Features marked done without proper verification

## How It Works

### Two-Phase Approach

**Phase 1: Initialization**
- Create structured feature list with test criteria
- Set up progress tracking
- Establish git checkpoint discipline

**Phase 2: Incremental Coding**
- Implement one feature at a time
- Test each feature before marking complete
- Commit after each verified feature
- Update progress tracking

## Quick Start

```bash
# Initialize a new project with incremental workflow
/incremental-init <project-description>

# Continue implementing next feature
/incremental-next

# Check progress status
/incremental-status
```

## Files Created

| File | Purpose |
|------|---------|
| `features.json` | Feature list with test criteria and completion status |
| `progress.md` | Human-readable progress tracking |
| `CLAUDE.md` | Project context for Claude Code |
| `.incremental/config.json` | Workflow configuration |

## Features.json Schema

```json
{
  "project": "Project Name",
  "created": "2024-01-01T00:00:00Z",
  "features": [
    {
      "id": "feature-1",
      "name": "Feature Name",
      "description": "What this feature does",
      "priority": 1,
      "tests": [
        {
          "id": "test-1",
          "description": "Test description",
          "type": "unit|integration|e2e|manual",
          "passed": false
        }
      ],
      "implemented": false,
      "committed": false,
      "commit_hash": null
    }
  ]
}
```

## Guidelines

### Must Do
- Update `progress.md` after each implementation run
- Test each feature before marking `implemented: true`
- Commit after each verified feature
- Never change feature list beyond marking completion

### Context Efficiency
- JSON format uses fewer tokens than markdown
- Progress file provides resumability
- Git logs provide implementation history
- Each feature is independently committable

## Integration with Agentic System

This workflow integrates with:
- **Enhanced Memory MCP** - Stores feature progress in episodic memory
- **Agent Runtime MCP** - Persists task state across sessions
- **Git hooks** - Auto-update progress on commits

## Comparison

| Approach | Context Efficiency | Resumability | Testing |
|----------|-------------------|--------------|---------|
| One-shot | Poor (~150%) | None | Optional |
| BMAD | Moderate (~120%) | Good | Story-based |
| Incremental | Excellent (~84%) | Excellent | Mandatory |
