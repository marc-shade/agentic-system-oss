# Task Management

Lightweight task management using native TodoWrite tool and agent-runtime-mcp for persistent multi-session tasks.

**Category**: productivity

---

## Quick Task Operations

### Current Session Tasks (TodoWrite)

Use the native TodoWrite tool for tasks within a single session:

**Create Tasks**:
```json
[
  {"content": "Fix auth bug", "status": "pending", "activeForm": "Fixing auth bug"},
  {"content": "Write tests", "status": "pending", "activeForm": "Writing tests"},
  {"content": "Update docs", "status": "pending", "activeForm": "Updating documentation"}
]
```

**Update Task Status**:
- `pending` - Task not yet started
- `in_progress` - Currently working on (only one at a time)
- `completed` - Task finished

**Best Practices**:
- Mark tasks completed immediately after finishing
- Keep exactly ONE task in_progress at any time
- Use descriptive activeForm for progress tracking
- Clean up stale todos when starting new work

---

## Persistent Tasks (Agent Runtime)

For complex multi-day projects that survive across sessions:

### Create Persistent Goal

```python
goal = mcp__agent-runtime-mcp__create_goal({
    "name": "Complex Feature Implementation",
    "description": "Detailed requirements for the feature"
})
```

### Auto-Decompose Into Tasks

```python
tasks = mcp__agent-runtime-mcp__decompose_goal({
    "goalId": goal.goalId,
    "strategy": "hierarchical"  # or "sequential", "parallel"
})
```

### Check Task Status

```python
status = mcp__agent-runtime-mcp__get_task_status({
    "taskId": "task_123"
})
```

### Update Task Progress

```python
mcp__agent-runtime-mcp__update_task({
    "taskId": "task_123",
    "status": "completed",
    "result": "Implementation completed successfully"
})
```

---

## When to Use Which

### Use TodoWrite When:
- ✅ Single session work
- ✅ Simple task tracking
- ✅ No persistence needed
- ✅ Quick status updates
- ✅ 3-10 tasks maximum

**Example**: Code review, bug fix, documentation update

### Use Agent Runtime When:
- ✅ Multi-day projects
- ✅ Complex task hierarchies
- ✅ Automatic task decomposition
- ✅ Persistent across sessions
- ✅ Goal-based planning

**Example**: Feature implementation, system refactoring, multi-phase projects

---

## Durable Workflows (AutoKitteh)

For truly long-running autonomous tasks (hours/days), use AutoKitteh via router:

```python
# Access via router when needed
mcp__autokitteh-mcp__deploy_workflow({
    "name": "multi_day_research",
    "triggers": ["schedule:daily", "event:completion"],
    "autonomous_hours": 48
})
```

**Use AutoKitteh for**:
- Scheduled recurring tasks
- Event-driven workflows
- Multi-day autonomous operations
- Integration with external systems

---

## Task Prioritization

### Priority Levels
1. **Critical** - Blockers, production issues
2. **High** - Important features, deadlines
3. **Medium** - Regular work items
4. **Low** - Nice-to-have, future work

### Prioritization Strategy

**TodoWrite** (manual):
- Order tasks by priority in array
- Move high-priority to top
- Work through sequentially

**Agent Runtime** (automatic):
```python
mcp__agent-runtime-mcp__prioritize_tasks({
    "goalId": "goal_123",
    "criteria": ["urgency", "dependencies", "impact"]
})
```

---

## Task Dependencies

### Simple Dependencies (TodoWrite)
- List tasks in execution order
- Complete blockers before dependent tasks
- Use clear task descriptions

### Complex Dependencies (Agent Runtime)
```python
mcp__agent-runtime-mcp__add_task_dependency({
    "taskId": "task_456",
    "dependsOn": ["task_123", "task_234"]
})
```

Agent Runtime automatically orders tasks respecting dependencies.

---

## Task Estimation

### Time Estimates
- **Quick** - < 30 minutes
- **Short** - 30 min - 2 hours
- **Medium** - 2-4 hours
- **Long** - 4-8 hours
- **Extended** - > 1 day (use Agent Runtime)

### Complexity Estimates
- **Simple** - Single file, straightforward
- **Moderate** - Multiple files, some complexity
- **Complex** - Architecture changes, testing needed
- **Very Complex** - Multi-day, requires planning

---

## Progress Tracking

### TodoWrite Progress
```python
# View current todos
# They're displayed in Claude Code's UI automatically
# Update status as you work
```

### Agent Runtime Progress
```python
progress = mcp__agent-runtime-mcp__get_goal_progress({
    "goalId": "goal_123"
})

# Returns:
# - Total tasks
# - Completed tasks
# - In-progress tasks
# - Blocked tasks
# - Overall completion percentage
```

---

## Task Organization

### Categories
- **Development** - Code, testing, debugging
- **Documentation** - README, guides, comments
- **Research** - Investigation, learning, analysis
- **Maintenance** - Refactoring, cleanup, optimization
- **Operations** - Deployment, monitoring, support

### Tags (Agent Runtime)
```python
mcp__agent-runtime-mcp__tag_task({
    "taskId": "task_123",
    "tags": ["frontend", "urgent", "user-facing"]
})
```

---

## Examples

### Example 1: Single Session Bug Fix

```python
TodoWrite([
    {"content": "Reproduce bug with test case", "status": "in_progress", "activeForm": "Reproducing bug"},
    {"content": "Identify root cause", "status": "pending", "activeForm": "Finding root cause"},
    {"content": "Implement fix", "status": "pending", "activeForm": "Implementing fix"},
    {"content": "Verify fix with tests", "status": "pending", "activeForm": "Verifying fix"}
])
```

### Example 2: Multi-Day Feature

```python
# Create goal
goal = mcp__agent-runtime-mcp__create_goal({
    "name": "User Authentication System",
    "description": "Implement OAuth2 authentication with JWT tokens"
})

# Decompose automatically
tasks = mcp__agent-runtime-mcp__decompose_goal({
    "goalId": goal.goalId,
    "strategy": "hierarchical"
})

# Result: Auto-created tasks like:
# 1. Design authentication flow
# 2. Implement OAuth2 provider integration
# 3. Create JWT token service
# 4. Add authentication middleware
# 5. Write integration tests
# 6. Update documentation
```

### Example 3: Recurring Maintenance

```python
# Use AutoKitteh for scheduled maintenance
mcp__autokitteh-mcp__deploy_workflow({
    "name": "daily_backup_check",
    "triggers": ["schedule:0 2 * * *"],  # 2 AM daily
    "workflow_def": {
        "steps": [
            {"action": "check_backup_status"},
            {"action": "verify_integrity"},
            {"action": "send_report"}
        ]
    }
})
```

---

## Tips for Effective Task Management

1. **Break Down Large Tasks** - Use Agent Runtime's decomposition
2. **One Task at a Time** - Keep only one in_progress
3. **Immediate Updates** - Mark completed right away
4. **Clear Descriptions** - Be specific about what needs doing
5. **Use Right Tool** - TodoWrite for simple, Agent Runtime for complex
6. **Track Progress** - Regular status checks on multi-day work
7. **Clean Up** - Remove stale or irrelevant tasks
8. **Prioritize Ruthlessly** - Focus on high-impact work
9. **Document Blockers** - Note dependencies and obstacles
10. **Celebrate Wins** - Mark completions, acknowledge progress

---

## Integration with Other Skills

**Works With**:
- **Memory Management** - Store task patterns and learnings
- **Apple Ecosystem** - Sync with Reminders app
- **Advanced System Capabilities** - Monitor task execution
- **Business Strategy** - Align tasks with business goals

**Access via router when needed**:
- `learning-orchestrator` - Learn from task patterns
- `autokitteh-mcp` - Durable workflow automation
- `agentic-flow-router` - Multi-agent task coordination
