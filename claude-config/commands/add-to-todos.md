# Add a task with full context preservation

Create a persistent task that survives across sessions.

## What this does
1. Creates a task in agent-runtime MCP
2. Captures full context about the task
3. Sets appropriate priority
4. Links to related goals if applicable

## Task structure
- Title: Clear, actionable description
- Description: Full context and requirements
- Priority: 1-10 (10 is highest)
- Dependencies: What must complete first

---

Create a new persistent task for: $ARGUMENTS

Use mcp__agent-runtime-mcp__create_task with:
- title: Clear, actionable title
- description: Capture the full context including:
  - What needs to be done
  - Why it's important
  - Any relevant file paths or context
  - Acceptance criteria if applicable
- priority: Assess priority (1-10, 10 is highest)
- dependencies: List any tasks that must complete first (if known)

Confirm the task was created with its ID.
