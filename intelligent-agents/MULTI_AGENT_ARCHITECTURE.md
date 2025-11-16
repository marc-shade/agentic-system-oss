# Multi-Agent System Architecture

**Date:** November 7, 2025
**Status:** ✅ ACTIVE - Observer-Actor Pattern

## Overview

The system health management uses a **multi-agent architecture** with specialized agents, each focused on a single responsibility:

```
┌─────────────────────────────────────────────────────────┐
│              System Health Management                    │
│                                                           │
│  ┌──────────────────┐          ┌────────────────────┐   │
│  │  Health Guardian │          │ Remediation Agent  │   │
│  │    (Observer)    │          │     (Actor)        │   │
│  │                  │          │                    │   │
│  │  • Monitors      │ ─────>   │  • Reads           │   │
│  │  • Detects       │  JSON    │  • Executes        │   │
│  │  • Recommends    │  File    │  • Audits          │   │
│  │                  │          │                    │   │
│  │  Every 30s       │          │  Every 60s         │   │
│  └──────────────────┘          └────────────────────┘   │
│           │                             │                │
│           │                             │                │
│           v                             v                │
│  /tmp/health_guardian_     /tmp/remediation_            │
│  recommendations.json       agent_actions.log           │
│                                                           │
│  ┌──────────────────┐                                    │
│  │ Arduino Display  │                                    │
│  │  LCD + LED       │<──────────────────────────────────┤
│  └──────────────────┘                                    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Agent 1: System Health Guardian (Observer)

### Responsibilities
- ✅ Monitor system health (CPU, memory, disk)
- ✅ Check service status (Temporal, AutoKitteh, PM2, Qdrant)
- ✅ Detect issues and failures
- ✅ Write recommendations for remediation
- ✅ Update Arduino display
- ✅ Track quality metrics

### Does NOT
- ❌ Execute fixes
- ❌ Restart services
- ❌ Modify system state

### Configuration
- **File:** `specialized/system_health_guardian.py`
- **Check Interval:** 30 seconds
- **Output:** `/tmp/health_guardian_recommendations.json`
- **Audit Log:** `/tmp/health_guardian_actions.log`
- **LaunchAgent:** `com.2acrestudios.system-health-guardian`

### Example Recommendation
```json
{
  "timestamp": "2025-11-07T06:45:00.123456",
  "service": "temporal",
  "action": "restart",
  "reason": "temporal detected as down",
  "confidence": 0.8
}
```

## Agent 2: System Remediation Agent (Actor)

### Responsibilities
- ✅ Read recommendations from Health Guardian
- ✅ Verify fix is safe to execute
- ✅ Check crash history (prevent loops)
- ✅ Execute service restarts
- ✅ Investigate chronic failures
- ✅ Log all actions

### Does NOT
- ❌ Monitor system health
- ❌ Make decisions about what needs fixing
- ❌ Update displays

### Configuration
- **File:** `specialized/system_remediation_agent.py`
- **Check Interval:** 60 seconds
- **Input:** `/tmp/health_guardian_recommendations.json`
- **Audit Log:** `/tmp/remediation_agent_actions.log`
- **Crash Limit:** 3 restarts/hour per service

### Safety Features
1. **Crash Loop Detection**
   - Tracks restart history per service
   - If >3 crashes/hour → Investigate, don't restart
   - Prevents infinite restart loops

2. **Root Cause Investigation**
   - Scans logs for error patterns
   - Reports findings for human review
   - Escalates chronic issues

## Communication Protocol

### Step 1: Health Guardian Detects Issue
```python
# In gather_observations()
services = self._check_service_status()
for service_name, status in services.items():
    if not status.get("running", False):
        self._write_recommendation(
            service_name=service_name,
            action="restart",
            reason=f"{service_name} detected as down"
        )
```

### Step 2: Remediation Agent Reads Recommendation
```python
# In gather_observations()
if os.path.exists(self.recommendations_file):
    with open(self.recommendations_file, 'r') as f:
        data = json.load(f)
        observations["pending_recommendations"] = data.get("recommendations", [])
```

### Step 3: Remediation Agent Executes
```python
# In execute_decision()
if self._should_restart_service(service):
    restart_result = self._restart_service(service)
    self._audit_log(f"AUTO-RESTART: {service}")
else:
    investigation = self._investigate_service_failure(service)
    self._audit_log(f"INVESTIGATION: {service} - {investigation}")
```

## Benefits of Multi-Agent Pattern

### 1. Separation of Concerns
- Each agent has ONE job
- Health Guardian: Detection
- Remediation Agent: Execution
- Clear boundaries

### 2. Safety & Control
- Easy to disable auto-remediation (stop remediation agent)
- Health Guardian continues monitoring
- Human can review recommendations before execution
- Can test each agent independently

### 3. Auditability
- Separate logs for detection vs execution
- Clear timeline of events
- Easy to trace "what happened when"

### 4. Scalability
- Can add more specialized agents:
  - **Investigation Agent** - Deep log analysis
  - **Alert Agent** - Notify humans
  - **Reporting Agent** - Generate reports
  - **Optimization Agent** - Tune system parameters

### 5. Testability
- Mock the recommendations file
- Test detection logic separately
- Test remediation logic separately
- No complex mocking of entire system

## Example Scenario: Temporal Crash Loop

### Cycle 1 (06:00)
```
Guardian: "Temporal down"
Guardian: Write recommendation → restart temporal
Remediation: Read recommendation
Remediation: Check crash history → 0 crashes
Remediation: Execute restart → SUCCESS
Remediation: Log "AUTO-RESTART: temporal"
```

### Cycle 2 (06:10)
```
Guardian: "Temporal down again"
Guardian: Write recommendation → restart temporal
Remediation: Read recommendation
Remediation: Check crash history → 1 crash
Remediation: Execute restart → SUCCESS
Remediation: Log "AUTO-RESTART: temporal (crash #2)"
```

### Cycle 3 (06:20)
```
Guardian: "Temporal down AGAIN"
Guardian: Write recommendation → restart temporal
Remediation: Read recommendation
Remediation: Check crash history → 2 crashes
Remediation: Execute restart → SUCCESS
Remediation: Log "AUTO-RESTART: temporal (crash #3)"
```

### Cycle 4 (06:30)
```
Guardian: "Temporal down REPEATEDLY"
Guardian: Write recommendation → restart temporal
Remediation: Read recommendation
Remediation: Check crash history → 3 crashes (THRESHOLD!)
Remediation: SKIP RESTART
Remediation: Investigate logs → "PORT CONFLICT: Port 7233 already in use"
Remediation: Log "INVESTIGATION: temporal - PORT CONFLICT"
```

**Result:** Prevented infinite restart loop, identified root cause!

## Monitored Services

Both agents work together to maintain:

1. **Temporal** (ports 7233, 8233)
2. **AutoKitteh** (port 9980)
3. **PM2** (Node.js process manager)
4. **Qdrant** (port 6333)

## Management Commands

### Start Both Agents
```bash
# Health Guardian (auto-starts via LaunchAgent)
launchctl load ~/Library/LaunchAgents/com.2acrestudios.system-health-guardian.plist

# Remediation Agent (manual start for now)
python3 /Volumes/SSDRAID0/agentic-system/intelligent-agents/specialized/system_remediation_agent.py
```

### View Live Activity
```bash
# Watch Health Guardian detecting issues
tail -f /tmp/system_health_guardian.log

# Watch Remediation Agent executing fixes
tail -f /tmp/remediation_agent_actions.log

# View recommendations queue
cat /tmp/health_guardian_recommendations.json | jq .
```

### Stop Auto-Remediation
```bash
# Stop remediation agent only
pkill -f system_remediation_agent

# Health Guardian continues monitoring and writing recommendations
# But no automatic fixes are executed
```

## File Locations

```
/Volumes/SSDRAID0/agentic-system/intelligent-agents/
├── specialized/
│   ├── system_health_guardian.py          # Observer
│   ├── system_remediation_agent.py        # Actor
│   └── code_evolution_protector.py        # (not yet deployed)
├── sdk_agents/
│   └── cli_agent.py                       # Base class
├── AUTONOMOUS_REMEDIATION.md
├── MULTI_AGENT_ARCHITECTURE.md (this file)
└── CLI_AGENT_MIGRATION.md

/tmp/
├── health_guardian_recommendations.json   # Communication file
├── health_guardian_actions.log           # Guardian audit log
└── remediation_agent_actions.log         # Remediation audit log
```

## Future Enhancements

### Investigation Agent
Dedicated agent for deep log analysis:
- Use AI to analyze logs
- Identify patterns across multiple services
- Suggest permanent fixes (not just restarts)
- Generate incident reports

### Alert Agent
Notify humans when needed:
- Send notifications on critical issues
- Escalate when remediation fails
- Daily summaries of actions taken
- Integration with monitoring systems

### Reporting Agent
Generate insights and reports:
- Service uptime statistics
- Crash frequency analysis
- Remediation success rates
- Cost of downtime

## Summary

✅ **Multi-agent architecture implemented**
✅ **Clear separation: Observer vs Actor**
✅ **Communication via JSON file**
✅ **Crash loop prevention**
✅ **Complete audit trails**
✅ **Easy to extend with more agents**

This pattern follows best practices for agent systems:
- Single Responsibility Principle
- Separation of Concerns
- Observable behavior
- Auditable actions
- Testable components

🎯 **Mission Accomplished!**
