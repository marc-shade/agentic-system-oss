# Autonomous Remediation System

**Date:** November 7, 2025
**Status:** ✅ ACTIVE AND RUNNING
**Agent PID:** 56798

## Overview

System Health Guardian now has **autonomous remediation** - it doesn't just monitor and recommend, it **automatically fixes** system issues.

## What Changed

### Before: Recommendation Only
```
Agent: "Temporal is down, should start it"
Action: Update LCD display, flash LED
Result: Human needs to manually start Temporal
```

### After: Autonomous Remediation
```
Agent: "Temporal is down, restarting..."
Action: Execute `temporal server start-dev`
Result: Service automatically restored
Audit: Log action to /tmp/health_guardian_actions.log
```

## Intelligence: Crash Loop Detection

The agent is **smart about crash loops**:

### Safe Restart (First 3 crashes/hour)
```
Service down → Check crash history → <3 crashes/hour → Restart automatically
```

### Escalation (>3 crashes/hour)
```
Service down → Check crash history → ≥3 crashes/hour → INVESTIGATE, DON'T RESTART
   ↓
Check logs for: Port conflicts, permission errors, OOM, timeouts
   ↓
Report findings and stop restart loop
```

**Why:** If a server is constantly restarting, something needs to be fixed at the root level, not just restarted in a loop.

## Monitored Services

The agent monitors and can auto-restart:

1. **Temporal** (ports 7233, 8233)
   - Command: `temporal server start-dev --db-filename /tmp/temporal.db --ui-port 8233`
   - Log: `/tmp/temporal_server.log`

2. **AutoKitteh** (port 9980)
   - Command: `ak up --mode dev`
   - Log: `/tmp/autokitteh.log`
   - Working directory: `/Volumes/SSDRAID0/agentic-system`

3. **PM2** (Node.js process manager)
   - Command: `pm2 resurrect`
   - Detects: Number of online processes

4. **Qdrant** (port 6333)
   - Command: `/Volumes/SSDRAID0/agentic-system/scripts/qdrant-monitor.sh start`
   - Log: `/Volumes/SSDRAID0/agentic-system/logs/qdrant-error.log`

## New Agent Capabilities

### Tool: `restart_service`
```python
{
    "name": "restart_service",
    "description": "Restart a failed service (with crash detection to prevent restart loops)",
    "input_schema": {
        "service_name": ["temporal", "autokitteh", "pm2", "qdrant"],
        "reason": "Why the restart is needed"
    }
}
```

### Tool: `investigate_root_cause`
```python
{
    "name": "investigate_root_cause",
    "description": "Investigate why a service keeps crashing instead of restarting it",
    "input_schema": {
        "service_name": "Name of service with chronic issues",
        "crash_count": "Number of crashes in recent period"
    }
}
```

## Crash History Tracking

### Data Structure
```python
self.crash_history = {
    "temporal": [timestamp1, timestamp2, timestamp3],
    "autokitteh": [timestamp4],
    "pm2": [],
    "qdrant": []
}
```

### Cleanup
- Timestamps older than 1 hour are automatically removed
- Only recent crashes count toward the 3-crash threshold

## Investigation Logic

When a service crash-loops, the agent:

1. **Checks service-specific logs**
2. **Scans for common error patterns:**
   - `port already in use` → PORT CONFLICT
   - `permission denied` → PERMISSION ERROR
   - `out of memory` / `oom` → MEMORY ERROR
   - `connection refused` → CONNECTION ERROR
   - `timeout` → TIMEOUT ERROR

3. **Reports findings** instead of blindly restarting

## Audit Logging

**Location:** `/tmp/health_guardian_actions.log`

**Format:**
```
2025-11-07T06:28:00.123456 | AUTO-RESTART: temporal - Service detected as down, restarting for availability
2025-11-07T06:32:00.456789 | RESTART-FAILED: autokitteh - Error: Port 9980 already in use
2025-11-07T06:45:00.789012 | ESCALATED: temporal crashed 3 times/hour - needs investigation
2025-11-07T06:50:00.123456 | INVESTIGATION: temporal - PORT CONFLICT: Service port already in use
```

## Startup Message

When agent starts, you'll see:

```
============================================================
🔥 System Health Guardian Starting 🔥
============================================================
CLI Tool: codex
Arduino: /dev/tty.usbmodem8344401
Base interval: 30s (will adapt)
Audit log: /tmp/health_guardian_actions.log

🚀 AUTONOMOUS REMEDIATION ENABLED
   • Auto-restart failed services (Temporal, AutoKitteh, PM2, Qdrant)
   • Crash detection: Max 3 restarts/hour per service
   • If service crash-loops, escalate to investigation instead
   • All actions logged to audit trail

✓ Connected to Arduino
✓ Ready to monitor AND FIX with intelligent reasoning
```

## Configuration

### Crash Threshold (Default: 3 per hour)
```python
self.max_restarts_per_hour = 3
```

To change: Edit `/Volumes/SSDRAID0/agentic-system/intelligent-agents/specialized/system_health_guardian.py` line 72

### Audit Log Path
```python
self.audit_log_path = "/tmp/health_guardian_actions.log"
```

## Example Scenarios

### Scenario 1: Temporal Crashes Once
```
06:00 - Temporal detected down
06:00 - Crash history check: 0 recent crashes
06:00 - ✅ AUTO-RESTART: temporal
06:00 - Temporal starts successfully
06:01 - Service monitoring shows Temporal running
```

### Scenario 2: AutoKitteh Crash Loop
```
06:00 - AutoKitteh detected down
06:00 - Crash history check: 0 crashes → Restart (crash #1)
06:10 - AutoKitteh detected down again
06:10 - Crash history check: 1 crash → Restart (crash #2)
06:20 - AutoKitteh detected down again
06:20 - Crash history check: 2 crashes → Restart (crash #3)
06:30 - AutoKitteh detected down AGAIN
06:30 - Crash history check: 3 crashes → ⚠️  ESCALATE
06:30 - 🔍 INVESTIGATION: Check /tmp/autokitteh.log
06:30 - Finding: PORT CONFLICT - Port 9980 already in use
06:30 - Decision: Report issue, DO NOT restart again
```

## Code Location

**File:** `/Volumes/SSDRAID0/agentic-system/intelligent-agents/specialized/system_health_guardian.py`

**Key Methods:**
- `_check_service_status()` - Lines 214-273 - Monitor service health
- `_should_restart_service()` - Lines 405-431 - Crash loop detection
- `_restart_service()` - Lines 433-494 - Execute service restart
- `_investigate_service_failure()` - Lines 496-545 - Root cause analysis
- `_audit_log()` - Lines 547-556 - Log all actions

## Management

### Restart Agent
```bash
launchctl unload ~/Library/LaunchAgents/com.2acrestudios.system-health-guardian.plist
launchctl load ~/Library/LaunchAgents/com.2acrestudios.system-health-guardian.plist
```

### View Live Monitoring
```bash
tail -f /tmp/system_health_guardian.log
```

### View Autonomous Actions
```bash
tail -f /tmp/health_guardian_actions.log
```

### Check Agent Status
```bash
ps aux | grep system_health_guardian | grep -v grep
launchctl list | grep system-health-guardian
```

## Future Enhancements

Potential improvements:

1. **Notification Integration**
   - Send notifications on autonomous fixes
   - Alert human if escalation happens

2. **More Services**
   - Add n8n monitoring (port 5678)
   - Add Chatterbox server monitoring
   - Add MCP server monitoring

3. **Smarter Investigation**
   - Use AI to analyze logs (currently pattern matching)
   - Suggest specific fixes based on error patterns
   - Automatically fix simple issues (clear cache, fix permissions)

4. **Dashboard Integration**
   - Real-time view of autonomous actions
   - Crash history graphs
   - Service uptime tracking

## Summary

✅ **Autonomous remediation implemented**
✅ **Crash loop detection prevents infinite restart loops**
✅ **Root cause investigation for chronic issues**
✅ **Complete audit trail of all actions**
✅ **Agent running and monitoring 4 critical services**

The System Health Guardian is now a **self-healing system** that not only monitors but automatically maintains system health - with intelligence to know when to restart vs when to investigate deeper issues.

🎯 **Mission Accomplished!**
