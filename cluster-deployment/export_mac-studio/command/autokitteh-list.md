# AutoKitteh List Deployments

List all AutoKitteh deployments and their status.

## Usage

```bash
/autokitteh-list
```

## Implementation

```bash
# List all deployments
ak deployment list

# Format with detailed status
ak deployment list --format json | jq -r '.[] | "ID: \(.deployment_id) | Name: \(.name) | Status: \(.status) | Created: \(.created_at)"'
```

## What This Shows

- Deployment IDs
- Deployment names
- Current status (active/inactive)
- Creation timestamps
- Associated workflows

## Output Format

```
Deployment ID: dep_abc123 | Name: claude_performance_monitor | Status: active
Deployment ID: dep_def456 | Name: self_healing | Status: active
Deployment ID: dep_ghi789 | Name: ember_monitoring | Status: active
Deployment ID: dep_jkl012 | Name: overnight_automation | Status: active
```

## Related Commands

- `/autokitteh-sessions` - View deployment sessions
- `/autokitteh-logs` - View session logs
- `/autokitteh-health` - Health check for AutoKitteh

## Notes

- Requires AutoKitteh server running on port 9980
- Shows all deployments from `.kitteh` files
- Real-time deployment state
