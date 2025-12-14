# Temporal Health Check

Comprehensive health check for Temporal server and workers.

## Usage

```bash
/temporal-health
```

## Implementation

```bash
# Check Temporal server health
echo "=== Temporal Server Health ==="
temporal operator cluster health 2>&1

# Check if server is running
echo -e "\n=== Server Process ==="
ps aux | grep "temporal server" | grep -v grep || echo "⚠️  Temporal server not running"

# Check port availability
echo -e "\n=== Port Status ==="
lsof -i :7233 > /dev/null && echo "✅ gRPC port 7233: LISTENING" || echo "❌ gRPC port 7233: NOT LISTENING"
lsof -i :8233 > /dev/null && echo "✅ UI port 8233: LISTENING" || echo "❌ UI port 8233: NOT LISTENING"

# Check worker processes
echo -e "\n=== Active Workers ==="
ps aux | grep -E "claude_learning|infrastructure_health|ai_agent_monitoring|overnight_automation" | grep -v grep | awk '{print $2, $11, $12, $13}'

# Check logs for recent errors
echo -e "\n=== Recent Errors (last 10) ==="
find /Volumes/FILES/agentic-system/temporal-workflows -name "*.log" -exec tail -100 {} \; | grep -i error | tail -10 || echo "No recent errors"

# Database check
echo -e "\n=== Database ==="
ls -lh /tmp/temporal.db && echo "✅ Database exists" || echo "❌ Database missing"

# Overall status summary
echo -e "\n=== Summary ==="
if lsof -i :7233 > /dev/null; then
    echo "✅ Temporal system is HEALTHY"
else
    echo "❌ Temporal system has ISSUES - run recovery procedures"
fi
```

## What This Shows

- Server health status (SERVING/NOT_SERVING)
- Server process status (running/not running)
- Port availability (7233 gRPC, 8233 UI)
- Active worker processes with PIDs
- Recent error logs
- Database status
- Overall system health summary

## Output Format

```
=== Temporal Server Health ===
SERVING

=== Server Process ===
12345   temporal server start-dev

=== Port Status ===
✅ gRPC port 7233: LISTENING
✅ UI port 8233: LISTENING

=== Active Workers ===
12346 python3 claude_learning.py
12347 python3 infrastructure_health.py
12348 python3 ai_agent_monitoring.py
12349 python3 overnight_automation.py

=== Recent Errors ===
No recent errors

=== Database ===
✅ Database exists: /tmp/temporal.db (156MB)

=== Summary ===
✅ Temporal system is HEALTHY
```

## Recovery Actions

If health check fails:

1. **Server not running**:
   ```bash
   cd /Volumes/FILES/agentic-system/temporal-workflows
   nohup temporal server start-dev --db-filename /tmp/temporal.db --ui-port 8233 > temporal_server.log 2>&1 &
   ```

2. **Workers not running**:
   ```bash
   ./start_claude_learning.sh
   ./start_overnight_automation.sh
   python3 ai_agent_monitoring.py &
   python3 infrastructure_health.py &
   ```

3. **Database corrupted**:
   ```bash
   rm /tmp/temporal.db
   # Restart server (creates new DB)
   ```

## Related Commands

- `/temporal-list` - List workflows
- `/temporal-status` - Get workflow status
- `/temporal-describe` - Describe specific workflow

## Notes

- Comprehensive diagnostic tool
- Provides recovery instructions
- Safe to run frequently
- No destructive actions
