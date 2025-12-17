# Skill Creator Guide

Complete guide for creating effective Claude Code skills following the compositional framework.

## Core Principle

**Skills compose slash commands - they do NOT replace them.**

Skills are the highest level of abstraction. They orchestrate multiple slash commands and sub-agents for complex workflows.

## When to Create a Skill

Create a skill when:
- A workflow spans multiple operations
- Domain-specific expertise is needed
- Automatic behavior should recur across projects
- Complex workflows benefit from composition

Do NOT create a skill for:
- Simple one-off tasks (use slash command)
- Single operations (use slash command)
- Parallelization only (use sub-agent)

## Skill Structure

```
~/.claude/skills/
└── my-skill/
    └── SKILL.md
```

The SKILL.md file contains:
1. Skill name and purpose
2. When to invoke (trigger conditions)
3. What it composes (slash commands, sub-agents)
4. Workflow steps
5. Output format

## Template

```markdown
# [Skill Name]

[Brief description of what the skill does]

## When to Use

Invoke this skill when:
- [Trigger condition 1]
- [Trigger condition 2]
- [Trigger condition 3]

## Composes

This skill orchestrates:
- `/command-1` - [what it does]
- `/command-2` - [what it does]
- Sub-agent: [agent-name] - [what it does]

## Workflow

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Output Format

[Expected output structure]
```

## Example: System Monitor Skill

```markdown
# Autonomous System Monitor

Comprehensive monitoring for 24/7 autonomous systems.

## When to Use

Invoke when:
- User asks "system status"
- User says "is everything okay?"
- Need complete system health report

## Composes

- `/temporal-health` - Check Temporal workflows
- `/autokitteh-health` - Check AutoKitteh deployments
- `/memory-status` - Check enhanced-memory
- Sub-agent: diagnostics - Deep analysis if issues found

## Workflow

1. Run `/temporal-health` for workflow status
2. Run `/autokitteh-health` for deployment status
3. Run `/memory-status` for memory health
4. If issues found, spawn diagnostics agent
5. Compile comprehensive report

## Output Format

## System Health Report

### Temporal Workflows
[status]

### AutoKitteh Deployments
[status]

### Memory System
[status]

### Issues Detected
[issues or "None"]

### Recommendations
[actions if needed]
```

## Compositional Hierarchy

```
Skills (Compose commands and agents)
  ├─ Slash Commands (Primitive operations)
  ├─ Sub-Agents (Parallel execution)
  └─ Other Skills (Multi-level composition)
```

## Best Practices

1. **Single Responsibility**: Each skill has one clear purpose
2. **Compose, Don't Replace**: Build on primitives
3. **Clear Triggers**: Document when to invoke
4. **Structured Output**: Consistent format
5. **Graceful Degradation**: Handle component failures
