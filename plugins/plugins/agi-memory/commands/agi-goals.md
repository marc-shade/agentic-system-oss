---
description: View and manage AGI goals and tasks
---

# AGI Goals & Tasks

## Current Goals

Let me check your active goals and pending tasks.

## Goal Management Commands

### View Goals
```
# List all active goals
mcp__agent-runtime__list_goals

# Get specific goal details
mcp__agent-runtime__get_goal --goal_id <id>
```

### Create Goals
```
# Create a new goal
mcp__agent-runtime__create_goal --name "Goal name" --description "What to achieve"

# Decompose goal into tasks
mcp__agent-runtime__decompose_goal --goal_id <id> --strategy sequential
```

### Task Management
```
# List tasks
mcp__agent-runtime__list_tasks

# Get next task
mcp__agent-runtime__get_next_task

# Update task status
mcp__agent-runtime__update_task_status --task_id <id> --status completed
```

## Quick Actions

Would you like me to:
1. **Show active goals** - List all current goals with progress
2. **Show pending tasks** - List tasks ready for execution
3. **Create a goal** - Define a new goal to work toward
4. **Get next task** - Pull the next priority task from queue

Just tell me what you'd like to do, or describe a goal you want to achieve and I'll help structure it.

---

*Goal management powered by agent-runtime-mcp*
