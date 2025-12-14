# AutoKitteh View Sessions

View AutoKitteh sessions for a deployment.

## Usage

```bash
/autokitteh-sessions [deployment-id]
```

## Parameters

- `deployment-id` - The deployment ID to view sessions for (optional, shows all if omitted)

## Implementation

```bash
if [ -z "$1" ]; then
    # List sessions for all deployments
    ak session list
else
    # List sessions for specific deployment
    ak session list --deployment "$1"
fi

# Format with details
ak session list --deployment "$1" --format json | jq -r '.[] | "Session: \(.session_id) | Status: \(.status) | Started: \(.started_at) | Duration: \(.duration)"'
```

## What This Shows

- Session IDs
- Session status (running, completed, failed)
- Start times
- Duration
- Trigger events
- Execution details

## Output Format

```
Session: ses_abc123 | Status: completed | Started: 2025-01-03 12:00:00 | Duration: 2m 15s
Session: ses_def456 | Status: running | Started: 2025-01-03 12:15:00 | Duration: 30s
Session: ses_ghi789 | Status: failed | Started: 2025-01-03 12:30:00 | Duration: 1m 5s
```

## Filtering Sessions

```bash
# Show only running sessions
ak session list --deployment "$1" --status running

# Show failed sessions
ak session list --deployment "$1" --status failed

# Show last 10 sessions
ak session list --deployment "$1" --limit 10
```

## Related Commands

- `/autokitteh-list` - List deployments
- `/autokitteh-logs` - View session logs
- `/autokitteh-health` - Health check

## Notes

- Sessions represent individual workflow executions
- Each trigger creates a new session
- Failed sessions include error details
- Running sessions show real-time progress
