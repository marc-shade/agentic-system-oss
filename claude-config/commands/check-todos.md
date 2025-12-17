# Check and resume tasks with full context

Review persistent tasks and continue work from where it was left off.

## What this does
1. Lists pending and in-progress tasks from agent-runtime
2. Shows task dependencies and priorities
3. Provides context for resuming work
4. Suggests next actions

---

Check the task queue and provide status:

1. Use mcp__agent-runtime-mcp__list_tasks to get pending and in-progress tasks
2. For any in-progress tasks, use mcp__agent-runtime-mcp__get_task to get full details
3. Summarize:
   - Tasks in progress (with context)
   - High priority pending tasks
   - Any blocked tasks
4. Recommend which task to work on next

If $ARGUMENTS is provided, filter or focus on that specific area.
