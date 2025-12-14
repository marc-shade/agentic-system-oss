# Temporal Workflow List

List all Temporal workflows with their current status.

## Usage

```bash
/temporal-list
```

## Implementation

```bash
# List all workflows in default namespace
temporal workflow list --namespace default

# Format output for readability
temporal workflow list --namespace default --format json | jq -r '.[] | "ID: \(.WorkflowId) | Status: \(.Status.Name) | Started: \(.StartTime)"'
```

## What This Shows

- Workflow IDs
- Current status (Running, Completed, Failed)
- Start times
- Execution counts

## Related Commands

- `/temporal-status` - Get detailed workflow status
- `/temporal-describe` - Describe specific workflow
- `/temporal-health` - Health check for Temporal server

## Notes

- Requires Temporal server running on port 7233
- Uses default namespace (can be customized)
- Shows real-time workflow state
