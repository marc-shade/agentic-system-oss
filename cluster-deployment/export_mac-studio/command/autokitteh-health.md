# AutoKitteh Health Check

Comprehensive health check for AutoKitteh server and deployments.

## Usage

```bash
/autokitteh-health
```

## Implementation

```bash
# Check AutoKitteh server health
echo "=== AutoKitteh Server Health ==="
curl -s http://localhost:9980/health 2>&1 && echo "✅ Server responding" || echo "❌ Server not responding"

# Check if server is running
echo -e "\n=== Server Process ==="
ps aux | grep "ak up" | grep -v grep || echo "⚠️  AutoKitteh server not running"

# Check port availability
echo -e "\n=== Port Status ==="
lsof -i :9980 > /dev/null && echo "✅ Port 9980: LISTENING" || echo "❌ Port 9980: NOT LISTENING"

# Check deployments
echo -e "\n=== Deployments ==="
ak deployment list | wc -l | xargs echo "Total deployments:"
ak deployment list --format json | jq -r 'map(select(.status == "active")) | length' | xargs echo "Active deployments:"

# Check recent sessions
echo -e "\n=== Recent Sessions ==="
ak session list --limit 10 --format json | jq -r 'group_by(.status) | map({status: .[0].status, count: length}) | .[]'

# Check for failed sessions in last hour
echo -e "\n=== Recent Failures ==="
ak session list --status failed --limit 5 | wc -l | xargs echo "Failed sessions (last 5):"

# Check .kitteh files
echo -e "\n=== Workflow Files ==="
find /Volumes/SSDRAID0/agentic-system -name "*.kitteh" -type f | wc -l | xargs echo ".kitteh files found:"
find /Volumes/SSDRAID0/agentic-system -name "*.kitteh" -type f -exec echo "  - {}" \;

# Check log files
echo -e "\n=== Log Files ==="
ls -lh /tmp/autokitteh.log 2>/dev/null && echo "✅ Main log exists" || echo "⚠️  No main log file"

# Overall status summary
echo -e "\n=== Summary ==="
if lsof -i :9980 > /dev/null; then
    echo "✅ AutoKitteh system is HEALTHY"
else
    echo "❌ AutoKitteh system has ISSUES - run recovery procedures"
fi
```

## What This Shows

- Server health status (responding/not responding)
- Server process status (running/not running)
- Port availability (9980)
- Deployment count (total and active)
- Recent session statistics by status
- Recent failures
- Available .kitteh workflow files
- Log file status
- Overall system health summary

## Output Format

```
=== AutoKitteh Server Health ===
✅ Server responding

=== Server Process ===
12345   ak up --mode dev

=== Port Status ===
✅ Port 9980: LISTENING

=== Deployments ===
Total deployments: 4
Active deployments: 4

=== Recent Sessions ===
{"status":"completed","count":8}
{"status":"running","count":1}
{"status":"failed","count":1}

=== Recent Failures ===
Failed sessions (last 5): 1

=== Workflow Files ===
.kitteh files found: 4
  - /Volumes/SSDRAID0/agentic-system/claude_performance_monitor.kitteh
  - /Volumes/SSDRAID0/agentic-system/self_healing.kitteh
  - /Volumes/SSDRAID0/agentic-system/ember_monitoring.kitteh
  - /Volumes/SSDRAID0/agentic-system/overnight_automation.kitteh

=== Log Files ===
✅ Main log exists: /tmp/autokitteh.log (2.3MB)

=== Summary ===
✅ AutoKitteh system is HEALTHY
```

## Recovery Actions

If health check fails:

1. **Server not running**:
   ```bash
   pkill -f "ak up"
   cd /Volumes/SSDRAID0/agentic-system
   nohup ak up --mode dev > /tmp/autokitteh.log 2>&1 &
   ```

2. **Deployments inactive**:
   ```bash
   # Redeploy all .kitteh files
   find /Volumes/SSDRAID0/agentic-system -name "*.kitteh" -type f -exec ak deploy {} \;
   ```

3. **Port conflict**:
   ```bash
   # Kill process using port 9980
   lsof -ti :9980 | xargs kill -9
   # Restart server
   ```

## Related Commands

- `/autokitteh-list` - List deployments
- `/autokitteh-sessions` - View sessions
- `/autokitteh-logs` - View session logs

## Notes

- Comprehensive diagnostic tool
- Provides recovery instructions
- Safe to run frequently
- No destructive actions
- Checks both server and deployments
