# Agentic Workflows - Deployment Guide

**Date:** 2025-11-04
**Status:** ✅ Production Ready
**Purpose:** Deploy autonomous optimization workflows with marker system integration

## Overview

This directory contains production-ready autonomous workflows that use the agentic marker system to optimize Claude Code configuration without triggering watchdog rollbacks.

### Available Workflows

1. **Simple Optimizer** - Standalone script for immediate use
2. **Temporal Deep Learning** - 6-hour optimization cycles
3. **AutoKitteh Event Handlers** - Real-time event response

## Quick Start (Recommended)

### Option 1: Simple Optimizer (No Dependencies)

The easiest way to see the marker system in action:

```bash
# Run optimization
python3 /Volumes/SSDRAID0/agentic-system/workflows/simple_optimizer.py

# Dry run (see what would be done)
python3 /Volumes/SSDRAID0/agentic-system/workflows/simple_optimizer.py --dry-run
```

**What it does:**
- Analyzes system resources (memory, CPU)
- Generates appropriate optimizations
- Marks changes with marker system
- Verifies with watchdog
- Logs all actions

**Requirements:** None (uses stdlib only, psutil optional)

## Workflow Descriptions

### 1. Simple Optimizer

**File:** `simple_optimizer.py`
**Type:** Standalone Python script
**Frequency:** On-demand
**Dependencies:** None required (psutil optional)

**Features:**
- Quick system analysis
- Memory-based optimizations
- CPU-based optimizations
- Dry-run mode
- Automatic watchdog verification

**Usage:**
```bash
# Basic usage
python3 simple_optimizer.py

# See what would happen
python3 simple_optimizer.py --dry-run

# Check logs after
tail ~/.claude/.config_modifications.jsonl | jq .
```

**Optimizations Applied:**

| Condition | Optimization | Confidence |
|-----------|-------------|------------|
| Memory >85% | cachingStrategy → conservative | 92% |
| Memory >8GB available | maxTokens → 250000 | 88% |
| Memory <4GB available | maxTokens → 150000 | 90% |
| CPU >90% | maxParallelTools -2 | 89% |

### 2. Temporal Deep Learning Workflow

**File:** `temporal/claude_deep_learning_optimizer.py`
**Type:** Temporal workflow
**Frequency:** Every 6 hours
**Dependencies:** Temporal, temporalio Python SDK

**Features:**
- Comprehensive metric collection
- Performance analysis
- Multi-parameter optimization
- Learning memory storage
- Confidence-based decisions

**Metrics Analyzed:**
- Tool execution patterns
- Memory usage trends
- Response time statistics
- Error rates
- Context utilization

**Setup:**

1. **Install Temporal:**
```bash
# Install Temporal server
brew install temporal

# Start Temporal server
temporal server start-dev --db-filename /tmp/temporal.db --ui-port 8233
```

2. **Install Python SDK:**
```bash
pip3 install temporalio
```

3. **Start Worker:**
```bash
cd /Volumes/SSDRAID0/agentic-system/workflows/temporal

# Start worker
python3 << 'EOF'
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from claude_deep_learning_optimizer import (
    ClaudeDeepLearningWorkflow,
    collect_performance_metrics,
    analyze_and_optimize
)

async def main():
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="claude-optimization",
        workflows=[ClaudeDeepLearningWorkflow],
        activities=[collect_performance_metrics, analyze_and_optimize]
    )

    print("🚀 Deep Learning Worker Started")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
EOF
```

4. **Schedule Workflow:**
```bash
# Start workflow every 6 hours
temporal workflow start \
  --type ClaudeDeepLearningWorkflow \
  --task-queue claude-optimization \
  --workflow-id claude-deep-learning \
  --cron "0 */6 * * *"
```

**Monitoring:**
```bash
# View workflow status
temporal workflow show --workflow-id claude-deep-learning

# View learning memory
tail /tmp/claude_learning_memory.jsonl | jq .

# View Temporal UI
open http://localhost:8233
```

### 3. AutoKitteh Event Handlers

**File:** `autokitteh/system_event_optimizer.py`
**Type:** Event-driven handlers
**Frequency:** Real-time (on events)
**Dependencies:** AutoKitteh

**Handlers:**

| Event | Trigger | Optimization |
|-------|---------|--------------|
| `on_high_memory` | Memory >85% | Reduce caching |
| `on_high_cpu` | CPU >90% | Reduce parallel tools |
| `on_error_spike` | Errors >10% | Enable debug logging |
| `on_mcp_latency` | Latency >1s | Adjust MCP timeout |

**Setup:**

1. **Install AutoKitteh:**
```bash
# Install ak CLI
brew install autokitteh/tap/ak

# Initialize
ak init
```

2. **Deploy Handlers:**
```bash
# Create AutoKitteh deployment file
cat > /tmp/system_optimizer.kitteh << 'EOF'
version: v1
project: claude-optimization

triggers:
  - name: high_memory
    type: webhook
    path: /events/memory
    handler: on_high_memory

  - name: high_cpu
    type: webhook
    path: /events/cpu
    handler: on_high_cpu

  - name: error_spike
    type: webhook
    path: /events/errors
    handler: on_error_spike

  - name: mcp_latency
    type: webhook
    path: /events/mcp
    handler: on_mcp_latency

handlers:
  - name: on_high_memory
    file: system_event_optimizer.py
    function: on_high_memory

  - name: on_high_cpu
    file: system_event_optimizer.py
    function: on_high_cpu

  - name: on_error_spike
    file: system_event_optimizer.py
    function: on_error_spike

  - name: on_mcp_latency
    file: system_event_optimizer.py
    function: on_mcp_latency
EOF

# Deploy
cd /Volumes/SSDRAID0/agentic-system/workflows/autokitteh
ak deploy /tmp/system_optimizer.kitteh
```

3. **Trigger Events:**
```bash
# Test high memory handler
curl -X POST http://localhost:9980/events/memory \
  -H "Content-Type: application/json" \
  -d '{"memory_percent": 0.92}'

# Test MCP latency handler
curl -X POST http://localhost:9980/events/mcp \
  -H "Content-Type: application/json" \
  -d '{"server_name": "voice-mode", "avg_latency_ms": 3500}'
```

**Monitoring:**
```bash
# View deployments
ak deployment list

# View sessions
ak session list

# View logs
ak session logs <session-id>

# View event log
tail /tmp/autokitteh_events.jsonl | jq .
```

## Marker System Integration

All workflows use the marker system to signal intentional changes:

### 1. Check Modifiability

```python
is_modifiable, reason = agent.is_key_modifiable(key)
if not is_modifiable:
    return  # Skip protected keys
```

### 2. Apply Change

```python
settings[key] = new_value
# Save settings...
```

### 3. Mark Change

```python
agent.mark_agentic_change(
    file="settings.json",
    key=key,
    reason="Detailed reason for optimization",
    change_type="agentic_optimization",
    confidence=0.95,
    session_id="workflow_session_id"
)
```

### 4. Notify (Optional)

```python
agent.notify_change(
    change_info={
        "optimization": "description",
        "reason": "why it was done"
    },
    severity="info",
    use_voice=True
)
```

## Monitoring & Logs

### Marker Activity

```bash
# View recent markers
tail -20 ~/.claude/.config_modifications.jsonl | jq .

# Count by type
jq -r '.change_type' ~/.claude/.config_modifications.jsonl | sort | uniq -c

# View specific session
jq 'select(.session_id | contains("deep_learning"))' ~/.claude/.config_modifications.jsonl
```

### Notifications

```bash
# View recent notifications
tail -20 ~/.claude/.config_notifications.jsonl | jq .

# Count by severity
jq -r '.severity' ~/.claude/.config_notifications.jsonl | sort | uniq -c
```

### Watchdog Verification

```bash
# Run watchdog manually
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py

# Check healing decisions
tail ~/.claude/intelligent_healing_decisions.jsonl | jq .
```

### Workflow Logs

```bash
# Simple optimizer - check exit code
echo $?  # 0 = success

# Temporal - view learning memory
tail /tmp/claude_learning_memory.jsonl | jq .

# AutoKitteh - view event log
tail /tmp/autokitteh_events.jsonl | jq .
```

## Validation & Testing

### Test Workflow Integration

```bash
# 1. Create test marker
python3 << 'EOF'
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
from intelligent_config_agent import IntelligentConfigAgent

agent = IntelligentConfigAgent()
agent.mark_agentic_change(
    file="settings.json",
    key="maxTokens",
    reason="Test workflow integration",
    confidence=0.95,
    session_id="test_integration"
)
print("✅ Test marker created")
EOF

# 2. Run simple optimizer
python3 /Volumes/SSDRAID0/agentic-system/workflows/simple_optimizer.py --dry-run

# 3. Run watchdog - should recognize marker
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py

# 4. Verify no healing occurred
# Expected output: "Configs healed: 0"
```

### Test Event Handlers

```bash
# Run AutoKitteh handlers in test mode
cd /Volumes/SSDRAID0/agentic-system/workflows/autokitteh
python3 system_event_optimizer.py

# Expected output:
# Test 1: High Memory Event (92%)
# Test 2: High CPU Event (95%)
# Test 3: Error Spike (15%)
# Test 4: MCP Latency (voice-mode, 3500ms)
```

### Test Temporal Workflow

```bash
# Run in standalone mode
cd /Volumes/SSDRAID0/agentic-system/workflows/temporal
python3 claude_deep_learning_optimizer.py

# Expected output:
# 🧠 Claude Deep Learning Optimizer (Standalone Mode)
# Applied X optimizations
```

## Troubleshooting

### Workflow Not Marking Changes

**Problem:** Changes applied but no marker created

**Check:**
```bash
# Verify agent import
python3 << 'EOF'
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
from intelligent_config_agent import IntelligentConfigAgent
agent = IntelligentConfigAgent()
print("✅ Agent loaded successfully")
EOF

# Check marker file
ls -la ~/.claude/.config_modifications.jsonl
```

### Watchdog Still Healing

**Problem:** Watchdog healing despite markers

**Check:**
```bash
# Verify marker exists and is recent
tail -1 ~/.claude/.config_modifications.jsonl | jq '.timestamp, .file, .key'

# Check marker age (must be <24 hours)
python3 << 'EOF'
from datetime import datetime
import json
from pathlib import Path

marker_file = Path.home() / ".claude" / ".config_modifications.jsonl"
with open(marker_file, 'r') as f:
    lines = f.readlines()

if lines:
    marker = json.loads(lines[-1])
    age = datetime.now() - datetime.fromisoformat(marker['timestamp'])
    print(f"Latest marker age: {age.total_seconds() / 3600:.1f} hours")
else:
    print("No markers found")
EOF
```

### Protected Key Error

**Problem:** Workflow tries to modify protected key

**Check:**
```bash
# Test key modifiability
python3 << 'EOF'
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
from intelligent_config_agent import IntelligentConfigAgent

agent = IntelligentConfigAgent()
key = "statusLine.command"  # Replace with your key

is_modifiable, reason = agent.is_key_modifiable(key)
print(f"Key: {key}")
print(f"Modifiable: {is_modifiable}")
print(f"Reason: {reason}")
EOF
```

## Best Practices

### 1. Always Check Modifiability

```python
# ✅ Good
is_modifiable, reason = agent.is_key_modifiable(key)
if not is_modifiable:
    print(f"⚠️  Skipping {key}: {reason}")
    return

# ❌ Bad - might try to modify protected key
settings[key] = value  # No check!
```

### 2. Use High Confidence for Tested Optimizations

```python
# ✅ Good - well-tested optimization
agent.mark_agentic_change(
    key="maxTokens",
    reason="Increased based on 2-week performance analysis",
    confidence=0.95  # High confidence
)

# ⚠️  Caution - experimental optimization
agent.mark_agentic_change(
    key="experimentalFeature",
    reason="Testing new feature",
    confidence=0.70  # Lower confidence
)
```

### 3. Provide Detailed Reasons

```python
# ✅ Good
reason = f"Memory at {memory_percent:.1%}, reducing caching to free {expected_savings}MB"

# ❌ Bad
reason = "optimizing memory"
```

### 4. Use Unique Session IDs

```python
# ✅ Good - unique and traceable
session_id = f"deep_learning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

# ❌ Bad - not unique
session_id = "optimization"
```

### 5. Log Before and After

```python
# ✅ Good
old_value = settings.get(key)
settings[key] = new_value
agent.mark_agentic_change(...)
print(f"✅ Optimized {key}: {old_value} → {new_value}")

# ❌ Bad - no logging
settings[key] = new_value
agent.mark_agentic_change(...)
```

## Production Deployment Checklist

- [ ] Test workflow in standalone mode
- [ ] Verify marker system integration
- [ ] Test with watchdog verification
- [ ] Review modifiable/protected keys
- [ ] Set appropriate confidence levels
- [ ] Configure notification preferences
- [ ] Set up monitoring/logging
- [ ] Test rollback procedures
- [ ] Document session ID format
- [ ] Schedule appropriate frequency

## Performance Impact

### Simple Optimizer

- **Runtime:** ~1-2 seconds
- **Frequency:** On-demand
- **Resource Usage:** Minimal
- **API Calls:** None

### Temporal Workflow

- **Runtime:** ~30-60 seconds per cycle
- **Frequency:** Every 6 hours
- **Resource Usage:** Low
- **API Calls:** None (uses local metrics)

### AutoKitteh Handlers

- **Runtime:** <500ms per event
- **Frequency:** Event-driven
- **Resource Usage:** Minimal
- **API Calls:** None

## Directory Structure

```
/Volumes/SSDRAID0/agentic-system/workflows/
├── simple_optimizer.py              # Standalone optimizer
├── temporal/
│   └── claude_deep_learning_optimizer.py
├── autokitteh/
│   └── system_event_optimizer.py
├── DEPLOYMENT_GUIDE.md             # This file
└── README.md                        # Overview
```

## Next Steps

1. **Start Simple:**
   ```bash
   # Run simple optimizer to see marker system in action
   python3 simple_optimizer.py --dry-run
   python3 simple_optimizer.py
   ```

2. **Monitor Activity:**
   ```bash
   # Watch markers being created
   tail -f ~/.claude/.config_modifications.jsonl | jq .
   ```

3. **Deploy Temporal (Optional):**
   - Install Temporal server
   - Start worker
   - Schedule workflow

4. **Deploy AutoKitteh (Optional):**
   - Install AutoKitteh
   - Deploy handlers
   - Configure event sources

## Support

### Documentation

- **Marker System Usage:** `../intelligent-self-healing/AGENTIC_MARKER_USAGE_GUIDE.md`
- **Testing Guide:** `../intelligent-self-healing/TEST_AGENTIC_MARKERS.md`
- **Implementation Complete:** `../intelligent-self-healing/AGENTIC_SELF_IMPROVEMENT_COMPLETE.md`

### Quick Reference

```bash
# Run optimization
python3 /Volumes/SSDRAID0/agentic-system/workflows/simple_optimizer.py

# Check markers
tail ~/.claude/.config_modifications.jsonl | jq .

# Verify with watchdog
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py
```

---

**Status:** ✅ Production Ready
**Last Updated:** 2025-11-04
**Version:** 1.0
