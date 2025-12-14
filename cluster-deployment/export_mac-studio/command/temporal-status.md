# Temporal Workflow Status

Get current status of all active Temporal workers and workflows.

## Usage

```bash
/temporal-status
```

## Implementation

```bash
# Show workflow statistics
temporal workflow list --namespace default | wc -l

# Show running workers
ps aux | grep "temporal worker" | grep -v grep

# Check server connectivity
temporal operator cluster health

# Show recent completions
temporal workflow list --namespace default --query "ExecutionStatus='Completed'" --limit 5
```

## What This Shows

- Total workflow count
- Active workers
- Server health status
- Recent completions
- Failed workflows

## Output Format

```
Active Workflows: 12
Running Workers: 4
  - Claude Deep Learning (PID: 1234)
  - Infrastructure Health (PID: 1235)
  - AI Agent Monitoring (PID: 1236)
  - Overnight Automation (PID: 1237)

Server Health: SERVING
Recent Completions: 5
Failed Workflows: 0
```

## Related Commands

- `/temporal-list` - List all workflows
- `/temporal-describe` - Describe specific workflow
- `/temporal-health` - Detailed health check

## Notes

- Shows real-time worker status
- Includes PID for process management
- Health check verifies server connectivity
