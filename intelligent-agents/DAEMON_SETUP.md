# Autonomous Improvement Daemon - Setup Guide

**Created**: 2025-01-19
**Status**: Phase 2 Integration Complete
**Purpose**: Configure and run the autonomous improvement daemon with Claude API integration

---

## Overview

The autonomous improvement daemon now has **bidirectional integration** with Claude API, enabling true recursive self-improvement:

```
Daemon → Detects patterns → Claude API → Analyzes → Proposes improvements
         ↑                                                    ↓
         └─────── Meta-learning records ← Applies ← Darwin Gödel validates
```

---

## Prerequisites

### 1. Install Anthropic SDK

```bash
pip3 install anthropic
```

### 2. Get Anthropic API Key

1. Go to https://console.anthropic.com/
2. Create API key
3. Copy the key (starts with `sk-ant-`)

### 3. Set Environment Variable

**Option 1: Shell Configuration** (Recommended for manual runs)
```bash
# Add to ~/.zshrc or ~/.bashrc
export ANTHROPIC_API_KEY="sk-ant-api03-..."
```

**Option 2: Daemon Service** (For launchd/systemd)

For launchd (macOS):
```xml
<!-- Add to plist file -->
<key>EnvironmentVariables</key>
<dict>
    <key>ANTHROPIC_API_KEY</key>
    <string>sk-ant-api03-...</string>
</dict>
```

For systemd (Linux):
```ini
# Add to service file
[Service]
Environment="ANTHROPIC_API_KEY=sk-ant-api03-..."
```

---

## Running the Daemon

### Manual Test Run

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Navigate to directory
cd /Volumes/SSDRAID0/agentic-system/intelligent-agents

# Run daemon (cycles every 60 minutes by default)
python3 autonomous_improvement_daemon.py
```

### Background Process

```bash
# Run in background with nohup
nohup python3 autonomous_improvement_daemon.py > /tmp/improvement_daemon.log 2>&1 &

# Check process
ps aux | grep autonomous_improvement_daemon

# View logs
tail -f /tmp/improvement_daemon.log
tail -f /Volumes/SSDRAID0/agentic-system/logs/autonomous_improvement.log
```

### Check Current Daemon

```bash
# Find existing daemon process
ps aux | grep autonomous_improvement_daemon

# Current daemon PID: 38188 (started Nov 11)
# Kill old daemon before starting new one:
kill 38188

# Start new daemon with Claude integration
python3 autonomous_improvement_daemon.py
```

---

## What Changed (Phase 2 Integration)

### New Methods Added

#### 1. `call_claude_for_analysis()`
- Calls Claude API with detected patterns
- Gets improvement proposals in structured JSON
- Handles API errors gracefully
- Falls back if API unavailable

#### 2. `execute_via_claude()`
- Validates and logs improvement proposals
- Saves proposals to `/logs/improvement_proposals/`
- Records execution results
- Returns metrics for meta-learning

#### 3. Modified `run_improvement_cycle()`
- Extracts patterns from meta-learning
- Calls Claude for analysis
- Darwin Gödel validates proposals
- Executes validated improvements
- Feeds outcomes back to meta-learning

### New Log Directories

```bash
/Volumes/SSDRAID0/agentic-system/logs/
├── autonomous_improvement.log          # Main daemon log
├── improvement_cycles/                 # Cycle reports (existing)
│   └── cycle_0203.json
└── improvement_proposals/              # NEW: Claude proposals
    └── proposal_20250119_160000.json
```

---

## Verification

### 1. Check API Configuration

```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Should output: sk-ant-api03-...
# If empty, the daemon will skip Claude integration
```

### 2. Check Logs

```bash
# Watch daemon logs
tail -f /Volumes/SSDRAID0/agentic-system/logs/autonomous_improvement.log

# Look for these log messages:
# "Initiating Claude-powered improvement analysis..."
# "Claude proposed improvement: <type>"
# "Proposal validated by Darwin Gödel"
# "Improvement executed successfully"
# "Outcome recorded to meta-learning"
```

### 3. Check Improvement Proposals

```bash
# View latest proposal
ls -lt /Volumes/SSDRAID0/agentic-system/logs/improvement_proposals/ | head -1

# Read proposal
cat /Volumes/SSDRAID0/agentic-system/logs/improvement_proposals/proposal_*.json
```

Expected format:
```json
{
  "timestamp": "2025-01-19T16:00:00",
  "cycle": 203,
  "proposal": {
    "improvement_type": "agent_selection",
    "description": "Optimize agent selection based on task complexity",
    "expected_impact": "15% faster task routing",
    "code_change": "Update MultiAgentCoordinator.assign_agent() logic",
    "test_criteria": "Measure average task assignment time",
    "risk_level": "low",
    "rollback_plan": "Revert to previous assignment logic"
  },
  "result": {
    "success": true,
    "execution_method": "simulated",
    "message": "Improvement validated and logged for manual review"
  }
}
```

### 4. Check Meta-Learning Integration

```bash
# Check meta-learning database for improvement cycle outcomes
sqlite3 /Volumes/SSDRAID0/agentic-system/databases/meta_learning.db

# Query for recursive improvement outcomes
SELECT * FROM task_outcomes
WHERE task_type = 'recursive_improvement'
ORDER BY timestamp DESC
LIMIT 5;
```

---

## Cycle Interval Configuration

The daemon runs improvement cycles at a configurable interval:

**Default**: 60 minutes

**Change interval**: Edit line 264 in `autonomous_improvement_daemon.py`:
```python
daemon = AutonomousImprovementDaemon(cycle_interval_minutes=60)
```

**Recommended intervals**:
- Development/testing: 15 minutes
- Production: 60 minutes (default)
- Conservative: 180 minutes (3 hours)

---

## Safety Features

### 1. Darwin Gödel Validation
- All proposals validated before execution
- Formal proof verification (when implemented)
- Automatic rollback on regression

### 2. Rate Limiting
- Max 1 improvement per cycle
- Cycles run hourly by default
- Prevents API cost explosion

### 3. Graceful Degradation
- Continues monitoring if API unavailable
- Logs warnings instead of crashing
- Falls back to pattern detection only

### 4. Human Review
- All proposals saved to improvement_proposals/
- Execution currently "simulated" (logged but not auto-applied)
- Manual review before production application

---

## Next Steps (Phase 3)

From ACTIVATION_PLAN.md:

### Task 3.1: Post-Execution Hook
- Create `~/.claude/hooks/post-tool-use.py`
- Feed all Claude tool executions to meta-learning
- Accumulate patterns from actual usage

### Task 3.2: Pre-Execution Hook
- Create `~/.claude/hooks/pre-tool-use.py`
- Capability discovery before each session
- Alert if daemon goes dormant

---

## Troubleshooting

### API Key Not Found
```
WARNING - ANTHROPIC_API_KEY not set - skipping Claude analysis
```
**Solution**: Set environment variable and restart daemon

### Import Error
```
WARNING - Anthropic SDK not available - recursive improvement will be limited
```
**Solution**: `pip3 install anthropic`

### No Patterns Detected
```
"claude_integration": {"status": "skipped", "reason": "no_proposal_generated"}
```
**Expected**: Normal if no patterns detected in lookback window

### Process Already Running
```
Address already in use
```
**Solution**: Kill existing daemon first: `kill $(pgrep -f autonomous_improvement_daemon)`

---

## Monitoring

### Daily Checks

```bash
# 1. Check daemon is running
ps aux | grep autonomous_improvement_daemon

# 2. Check recent cycle
ls -lt /Volumes/SSDRAID0/agentic-system/logs/improvement_cycles/ | head -1

# 3. Check for proposals
ls -lt /Volumes/SSDRAID0/agentic-system/logs/improvement_proposals/ | head -1

# 4. Check meta-learning outcomes
sqlite3 /Volumes/SSDRAID0/agentic-system/databases/meta_learning.db \
  "SELECT COUNT(*) FROM task_outcomes WHERE task_type='recursive_improvement';"
```

### Health Indicators

✅ **Healthy**:
- Daemon process running
- New cycle every 60 minutes
- Claude integration status: "success" or "skipped" (if no patterns)
- No error messages in logs

⚠️ **Warning**:
- Claude integration status: "error"
- API call failures (check API key)
- No new cycles (daemon may have crashed)

🚨 **Critical**:
- Daemon process not found
- Continuous errors in logs
- No cycles for >2 hours

---

## Cost Management

### API Usage Estimate

**Per Cycle**:
- Input: ~2000 tokens (patterns + context)
- Output: ~500 tokens (JSON proposal)
- Cost: ~$0.015 per cycle (Sonnet 4.5 pricing)

**Daily** (24 cycles at 60-minute intervals):
- Cost: ~$0.36/day
- Monthly: ~$11/month

**Recommendations**:
- Monitor usage in Anthropic console
- Set budget alerts
- Adjust cycle interval if needed
- Cache patterns to reduce API calls

---

## Success Criteria (Phase 2)

From ACTIVATION_PLAN.md Task 2.1:

- [x] Daemon calls Claude API every cycle
- [x] Claude analyzes patterns and proposes improvements
- [x] Darwin Gödel validates proposals
- [x] Improvements are logged (simulated execution)
- [x] Outcomes feed back to meta-learning

**Status**: ✅ Phase 2 Complete

**Next**: Phase 3 - Integration Hooks

---

## References

- **Activation Plan**: `/Volumes/SSDRAID0/agentic-system/ACTIVATION_PLAN.md`
- **ASI Capability Audit**: `/Volumes/SSDRAID0/agentic-system/ASI_CAPABILITY_AUDIT.md`
- **Daemon Code**: `/Volumes/SSDRAID0/agentic-system/intelligent-agents/autonomous_improvement_daemon.py`
- **Meta-Learning**: `/Volumes/SSDRAID0/agentic-system/intelligent-agents/meta_learning_engine.py`
- **Darwin Gödel**: `/Volumes/SSDRAID0/agentic-system/intelligent-agents/darwin_godel_machine.py`
