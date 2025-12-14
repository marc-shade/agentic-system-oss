# Temporal Workflow Describe

Get detailed information about a specific Temporal workflow.

## Usage

```bash
/temporal-describe [workflow-id]
```

## Parameters

- `workflow-id` - The workflow ID to describe

## Implementation

```bash
# Describe workflow with full details
temporal workflow describe --workflow-id "$1" --namespace default

# Show execution history
temporal workflow show --workflow-id "$1" --namespace default

# Get workflow result (if completed)
temporal workflow show --workflow-id "$1" --namespace default --output json | jq '.result'
```

## What This Shows

- Workflow execution details
- Current state and status
- Start/end times
- Input parameters
- Execution history
- Result (if completed)
- Error details (if failed)

## Output Format

```
Workflow ID: claude-learning-20250103-120000
Status: Running
Started: 2025-01-03 12:00:00
Duration: 2h 15m
Type: ClaudeDeepLearning
Task Queue: temporal-workflows

Execution History:
  1. WorkflowExecutionStarted
  2. ActivityTaskScheduled: analyze_patterns
  3. ActivityTaskCompleted: analyze_patterns
  4. ActivityTaskScheduled: optimize_code
  ... (in progress)
```

## Related Commands

- `/temporal-list` - List all workflows
- `/temporal-status` - Get overall status
- `/temporal-health` - Health check

## Notes

- Provides complete workflow details
- Shows execution timeline
- Includes error traces for debugging
