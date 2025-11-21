# System Verification Script - Usage Guide for Intelligent Agents

**Script Location**: `/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh`
**Last Updated**: 2025-11-06
**Purpose**: Comprehensive system verification baseline for all intelligent agents

---

## Quick Reference

### Human-Readable Output
```bash
/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh
```

### Machine-Readable JSON (For Agents)
```bash
/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh --json
```

### Save Baseline Snapshot
```bash
/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh --save
```

---

## What Gets Checked (34 Total Checks)

### 1. KutiraAI Backend Services (6 checks)
- Frontend Dashboard (3101)
- Agent Registry (4100)
- MCP Orchestrator (4101)
- Port Manager (4102)
- Workflow Engine (4103)
- System Monitor (4104)

### 2. Voice Mode Services (7 checks)
- Whisper STT (2022)
- Kokoro TTS (8880)
- Voice Broker Main (9091)
- Voice Broker Admin (9092)
- Voice Cache (9093)
- Voice Feedback (9050)
- LiveKit Server (7880)

### 3. Arduino Smart Surface (3 checks)
- Arduino Broker (process)
- Arduino Smart Agent (process)
- Arduino Socket (file)

### 4. Ember System (3 checks)
- Ember State (file)
- Ember StatusLine Script (file)
- Ember MCP Server (process)

### 5. Core MCP Servers (5 checks)
- Enhanced Memory MCP
- Agent Runtime MCP
- Sequential Thinking MCP
- Voice Mode MCP
- Chrome DevTools MCP

### 6. Database Services (1 check)
- PostgreSQL (5432)

### 7. Intelligent Agents (5 checks) - **NEW**
- System Health Guardian (process)
- Code Evolution Protector (process)
- Agent SDK (Claude) (file)
- Agent SDK (Codex) (file)
- Agent SDK (Gemini) (file)

### 8. Claude Code Skills (3 checks) - **NEW**
- codex-consultant Skill (file)
- gemini-analyst Skill (file)
- ai-orchestrator Skill (file)

### 9. PM2 Managed Services (1 check)
- PM2 process count

---

## JSON Output Format (For Agent Parsing)

```json
{
  "timestamp": "2025-11-06T14:44:38Z",
  "total_checks": 34,
  "passed_checks": 31,
  "failed_checks": 3,
  "percentage": 91,
  "operational": false,
  "status": "degraded",  // "healthy" | "degraded" | "critical"
  "checks": [
    {
      "name": "Frontend Dashboard",
      "type": "service",  // "service" | "process" | "file" | "pm2"
      "port": 3101,
      "status": "running",  // "running" | "degraded" | "failed" | "exists" | "missing"
      "message": "Service operational"
    },
    // ... more checks
  ],
  "access_urls": {
    "dashboard": "http://localhost:3101",
    "system_monitor": "http://localhost:4104/health",
    // ... more URLs
  }
}
```

---

## Status Interpretation

### System Status Values
- **healthy** (100%): All checks passed
- **degraded** (80-99%): Most services operational, some non-critical failures
- **critical** (<80%): Critical services missing

### Check Status Values
- **running**: Service/process operational
- **degraded**: Port open but no health response
- **failed**: Service/process not running
- **exists**: File found
- **missing**: File not found

---

## Usage Patterns for Intelligent Agents

### Pattern 1: Health Check Before Operations
```python
import subprocess
import json

def verify_system_health():
    result = subprocess.run(
        ["/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh", "--json"],
        capture_output=True,
        text=True
    )

    health = json.loads(result.stdout)

    if health["percentage"] >= 90:
        return True  # System healthy enough
    else:
        return False  # System needs attention
```

### Pattern 2: Identify Specific Service Status
```python
def check_service_status(service_name):
    result = subprocess.run(
        ["/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh", "--json"],
        capture_output=True,
        text=True
    )

    health = json.loads(result.stdout)

    for check in health["checks"]:
        if check["name"] == service_name:
            return check["status"]

    return "not_found"
```

### Pattern 3: Monitor System Over Time
```python
import time
import json

def monitor_system(interval_seconds=300):
    """Monitor system every 5 minutes"""
    while True:
        result = subprocess.run(
            ["/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh", "--json"],
            capture_output=True,
            text=True
        )

        health = json.loads(result.stdout)

        if health["percentage"] < 90:
            alert(f"System degraded: {health['percentage']}%")

        time.sleep(interval_seconds)
```

### Pattern 4: Baseline Comparison
```python
def compare_to_baseline(baseline_file):
    """Compare current state to saved baseline"""

    # Get current state
    result = subprocess.run(
        ["/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh", "--json"],
        capture_output=True,
        text=True
    )
    current = json.loads(result.stdout)

    # Load baseline
    with open(baseline_file) as f:
        baseline = json.load(f)

    # Compare
    current_services = {c["name"]: c["status"] for c in current["checks"]}
    baseline_services = {c["name"]: c["status"] for c in baseline["checks"]}

    changes = []
    for service, status in current_services.items():
        if service in baseline_services:
            if baseline_services[service] != status:
                changes.append({
                    "service": service,
                    "baseline": baseline_services[service],
                    "current": status
                })

    return changes
```

---

## Integration with Enhanced Memory

### Store Verification Results
```python
import subprocess
import json

# Run verification
result = subprocess.run(
    ["/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh", "--json"],
    capture_output=True,
    text=True
)
health = json.loads(result.stdout)

# Store in enhanced memory
mcp__enhanced-memory-mcp__create_entities([{
    "name": f"system-verification-{health['timestamp']}",
    "entityType": "system_health",
    "observations": [
        f"percentage: {health['percentage']}",
        f"status: {health['status']}",
        f"failed_checks: {health['failed_checks']}",
        f"services: {json.dumps(health['checks'])}"
    ]
}])
```

### Query Historical Health
```python
# Search for recent verifications
recent_health = mcp__enhanced-memory-mcp__search_nodes(
    query="system-verification",
    limit=10
)

# Analyze trends
percentages = [
    int(obs.split(":")[1].strip())
    for entity in recent_health
    for obs in entity["observations"]
    if "percentage:" in obs
]

avg_health = sum(percentages) / len(percentages)
```

---

## Expected Operational Thresholds

### 100% Operational (Ideal State)
All 34 checks passing:
- All 6 backend services running
- All 7 voice services running
- All 3 Arduino services running
- All 3 Ember components present
- All 5 MCP servers running
- PostgreSQL responding
- Both intelligent agents running
- All 3 Skills present
- PM2 managing 5 processes

### 90-99% Operational (Acceptable)
30-33 checks passing:
- Core services operational
- Non-critical services may be down:
  - Voice Mode MCP standalone (7 other voice services work)
  - Intelligent agents (can be started on demand)
  - PostgreSQL health endpoint

### 80-89% Operational (Degraded)
27-29 checks passing:
- Major subsystem partially down
- Requires investigation
- Some functionality impaired

### <80% Operational (Critical)
<27 checks passing:
- Critical services missing
- System requires immediate attention
- Major functionality offline

---

## Remediation Guide

### If Backend Services Down (4100-4104)
```bash
cd /Volumes/FILES/code/kutiraai/services
pm2 start ecosystem.config.js
```

### If Intelligent Agents Down
Via menubar app:
1. Open "Agentic Monitor.app"
2. Click "Quick Actions" → "Start Intelligent Agents"

Or manually:
```bash
cd /Volumes/SSDRAID0/agentic-system/intelligent-agents
python3 specialized/system_health_guardian.py /dev/tty.usbmodem8344401 &
python3 specialized/code_evolution_protector.py &
```

### If Voice Services Down
```bash
# Check voice service status
ps aux | grep -E "(whisper|kokoro|voice)"

# Restart voice services (see voice-mode documentation)
```

### If MCP Servers Down
```bash
# Restart Claude Code to reload MCP servers
exit
claude
```

---

## Change History

### 2025-11-06 (v2.0)
- Added Intelligent Agents section (5 checks)
- Added Claude Code Skills section (3 checks)
- Added JSON output for agent consumption (--json)
- Added baseline snapshot capability (--save)
- Increased total checks from 26 to 34
- Added machine-readable status codes
- Added detailed check metadata

### Previous Version (v1.0)
- 26 checks covering core services
- Human-readable output only

---

## Best Practices for Agents

### 1. **Check Before Major Operations**
Always verify system health before starting long-running operations:
```python
if not verify_system_health():
    log("System unhealthy, deferring operation")
    return
```

### 2. **Store Verification Results**
Keep historical record in enhanced-memory for trend analysis:
```python
# After every verification
store_verification_in_memory(health_data)
```

### 3. **Alert on Degradation**
Don't wait for critical failures:
```python
if health["percentage"] < 90:
    notify_user("System health degraded")
```

### 4. **Use Type-Specific Checks**
Different check types have different meanings:
```python
# Service checks: Can be restarted
# Process checks: May need manual intervention
# File checks: Configuration issue if missing
```

### 5. **Baseline Drift Detection**
Monitor for unexpected changes:
```python
changes = compare_to_baseline()
if changes:
    investigate_changes(changes)
```

---

## Integration Examples

### SystemHealthGuardian Agent
```python
async def gather_observations(self):
    # Use verification script as ground truth
    result = subprocess.run(
        ["/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh", "--json"],
        capture_output=True,
        text=True
    )

    health = json.loads(result.stdout)

    return {
        "system_health_percentage": health["percentage"],
        "system_status": health["status"],
        "failed_services": [
            c["name"] for c in health["checks"]
            if c["status"] in ["failed", "missing"]
        ],
        "timestamp": health["timestamp"]
    }
```

### CodeEvolutionProtector Agent
```python
async def validate_system_state(self):
    # Ensure system is healthy before allowing changes
    result = subprocess.run(
        ["/Users/marc/.claude/scripts/verify_kutiraai_dashboard.sh", "--json"],
        capture_output=True,
        text=True
    )

    health = json.loads(result.stdout)

    if health["percentage"] < 90:
        return False, f"System degraded ({health['percentage']}%)"

    return True, "System healthy"
```

---

## Conclusion

This verification script is the **single source of truth** for system health across the entire agentic framework. All intelligent agents should use it as their baseline for decision-making about system state.

**Key Benefits**:
- ✅ Comprehensive (34 checks across all subsystems)
- ✅ Machine-readable (JSON output)
- ✅ Baseline snapshots (--save)
- ✅ Trend analysis ready (timestamps + enhanced-memory integration)
- ✅ Remediation guidance (built-in)
- ✅ Agent-friendly (structured data)

**Recommended Usage Frequency**:
- Before major operations: Always
- During monitoring loops: Every 5 minutes
- For trend analysis: Store every check in enhanced-memory
- For baseline comparison: Daily snapshot

---

**Script Version**: 2.0
**Total Checks**: 34
**Output Formats**: Human-readable, JSON
**Status**: ✅ Production Ready
