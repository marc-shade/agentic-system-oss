# AutoKitteh View Logs

View logs for an AutoKitteh session.

## Usage

```bash
/autokitteh-logs [session-id] [lines]
```

## Parameters

- `session-id` - The session ID to view logs for
- `lines` - Number of lines to show (optional, default: all)

## Implementation

```bash
if [ -z "$2" ]; then
    # Show all logs
    ak session logs "$1"
else
    # Show last N lines
    ak session logs "$1" | tail -n "$2"
fi

# With timestamps and formatting
ak session logs "$1" | while read line; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"
done
```

## What This Shows

- Session execution logs
- Activity outputs
- Error messages
- Workflow state transitions
- Trigger events
- Return values

## Output Format

```
[2025-01-03 12:00:00] Starting session ses_abc123
[2025-01-03 12:00:01] Trigger: schedule:15min
[2025-01-03 12:00:01] Executing activity: check_tool_usage
[2025-01-03 12:00:02] Tool usage patterns analyzed
[2025-01-03 12:00:02] Executing activity: calculate_metrics
[2025-01-03 12:00:03] Metrics calculated: error_rate=0.05
[2025-01-03 12:00:03] Session completed successfully
```

## Follow Logs in Real-Time

```bash
# Follow logs for running session
ak session logs "$1" --follow

# With grep filter
ak session logs "$1" --follow | grep -i error
```

## Related Commands

- `/autokitteh-list` - List deployments
- `/autokitteh-sessions` - View sessions
- `/autokitteh-health` - Health check

## Notes

- Logs are immutable once session completes
- Running sessions show real-time updates with --follow
- Error logs include stack traces
- Large sessions may have truncated logs
