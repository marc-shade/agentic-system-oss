# Agentic Optimization Workflows

**Status:** ✅ Production Ready
**Date:** 2025-11-04
**Purpose:** Autonomous workflows that optimize Claude Code with marker system integration

## Overview

This directory contains production-ready autonomous optimization workflows that use the **agentic marker system** to optimize Claude Code configuration without triggering watchdog rollbacks.

### Key Innovation

These workflows use the marker system to signal **intentional self-improvements**, allowing the agentic system to:

- ✅ Freely optimize configuration
- ✅ Prevent watchdog rollbacks
- ✅ Maintain full audit trail
- ✅ Respect protected keys
- ✅ Provide confidence scores

## Available Workflows

| Workflow | Type | Frequency | Complexity | Status |
|----------|------|-----------|------------|--------|
| **simple_optimizer.py** | Standalone | On-demand | Simple | ✅ Ready |
| **temporal/claude_deep_learning_optimizer.py** | Temporal | Every 6h | Advanced | ✅ Ready |
| **autokitteh/system_event_optimizer.py** | Event-driven | Real-time | Advanced | ✅ Ready |

## Quick Start

### Simplest Option (No Setup Required)

```bash
# See what optimizations would be applied
python3 simple_optimizer.py --dry-run

# Apply optimizations
python3 simple_optimizer.py

# Check what was marked
tail ~/.claude/.config_modifications.jsonl | jq .
```

**That's it!** The simple optimizer:
- Analyzes system resources
- Generates appropriate optimizations
- Marks changes with marker system
- Verifies with watchdog
- Logs everything

## What Gets Optimized

### Memory-Based Optimizations

| Condition | Action | Confidence |
|-----------|--------|------------|
| Memory >85% | `cachingStrategy` → conservative | 92% |
| Memory >8GB free | `maxTokens` → 250000 | 88% |
| Memory <4GB free | `maxTokens` → 150000 | 90% |

### CPU-Based Optimizations

| Condition | Action | Confidence |
|-----------|--------|------------|
| CPU >90% | Reduce `maxParallelTools` by 2 | 89% |

### Error-Based Optimizations

| Condition | Action | Confidence |
|-----------|--------|------------|
| Errors >10% | `loggingLevel` → DEBUG | 90% |

### MCP-Based Optimizations

| Condition | Action | Confidence |
|-----------|--------|------------|
| Latency >1s | Adjust `mcpServers.*.timeout` | 88% |

## How Marker System Integration Works

### 1. Check Key Modifiability

Before changing anything, workflows check if the key can be modified:

```python
is_modifiable, reason = agent.is_key_modifiable("maxTokens")
if not is_modifiable:
    return  # Skip protected keys
```

**Protected keys** (never modified):
- `statusLine.command`
- `hooks.*.path`
- `apiKeys.*`
- `credentials.*`
- `mcpServers.*.command`

**Modifiable keys** (safe for optimization):
- `maxTokens`
- `parallelToolCalls`
- `cachingStrategy`
- `mcpServers.*.timeout`
- `loggingLevel`
- And 19 more...

### 2. Apply Optimization

```python
settings['maxTokens'] = 250000
# Save settings...
```

### 3. Mark as Intentional

```python
agent.mark_agentic_change(
    file="settings.json",
    key="maxTokens",
    reason="Increased based on available memory analysis",
    change_type="agentic_optimization",
    confidence=0.95,
    session_id="optimizer_20251104_123456"
)
```

### 4. Watchdog Recognizes Marker

When Claude Code starts:
1. Watchdog detects configuration change
2. Checks for marker (finds it)
3. Sees high trust level (0.95)
4. **Logs but doesn't heal** ✅
5. System continues with optimization

## Workflow Details

### Simple Optimizer

**Best for:** Quick optimizations, testing, manual runs

```bash
# Usage
python3 simple_optimizer.py [--dry-run]

# What it analyzes
- System memory usage
- CPU utilization
- Available resources

# What it optimizes
- Context window (maxTokens)
- Caching strategy
- Parallel execution
```

**Advantages:**
- No dependencies
- Immediate results
- Easy to understand
- Perfect for testing

### Temporal Deep Learning Workflow

**Best for:** Continuous optimization, comprehensive analysis

```bash
# Requires Temporal server
temporal server start-dev

# Start worker
python3 temporal/claude_deep_learning_optimizer.py

# Schedule (every 6 hours)
temporal workflow start \
  --type ClaudeDeepLearningWorkflow \
  --task-queue claude-optimization \
  --cron "0 */6 * * *"
```

**What it analyzes:**
- Tool execution patterns
- Memory usage trends
- Response times
- Error rates
- Context utilization

**Advantages:**
- Comprehensive metrics
- Historical learning
- Fault-tolerant
- Production-grade

### AutoKitteh Event Handlers

**Best for:** Real-time response to system events

```bash
# Requires AutoKitteh
ak deploy system_optimizer.kitteh

# Trigger events
curl -X POST http://localhost:9980/events/memory \
  -d '{"memory_percent": 0.92}'
```

**Event handlers:**
- `on_high_memory` - Memory >85%
- `on_high_cpu` - CPU >90%
- `on_error_spike` - Errors >10%
- `on_mcp_latency` - Latency >1s

**Advantages:**
- Instant response
- Event-driven
- Minimal overhead
- Real-time optimization

## Monitoring

### View Markers

```bash
# Recent markers
tail -20 ~/.claude/.config_modifications.jsonl | jq .

# Count by type
jq -r '.change_type' ~/.claude/.config_modifications.jsonl | sort | uniq -c

# Specific session
jq 'select(.session_id | contains("optimizer"))' ~/.claude/.config_modifications.jsonl
```

### View Notifications

```bash
# Recent notifications
tail -20 ~/.claude/.config_notifications.jsonl | jq .

# By severity
jq -r '.severity' ~/.claude/.config_notifications.jsonl | sort | uniq -c
```

### Verify with Watchdog

```bash
# Run watchdog manually
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py

# Expected output for marked changes:
# "✅ Agentic modification detected"
# "Configs healed: 0"
```

## Example: Complete Workflow

### Step 1: Analyze System

```bash
python3 simple_optimizer.py --dry-run
```

**Output:**
```
📊 Analyzing system...
  Memory: 67.5% (10.4GB available)
  CPU: 18.1%

✓ System performing well - no optimizations needed
```

### Step 2: High Memory Detected

System memory increases to 92%:

```bash
python3 simple_optimizer.py
```

**Output:**
```
💡 Found 1 optimization opportunity:

  • cachingStrategy: aggressive → conservative
    Reason: High memory at 92.0%, reducing cache
    Confidence: 92.0%

🔧 Applying optimizations...
  ✓ cachingStrategy

✅ Applied 1 optimization

🛡️  Verifying with intelligent watchdog...
✅ Watchdog verified - optimizations recognized as intentional
```

### Step 3: Marker Created

```bash
tail -1 ~/.claude/.config_modifications.jsonl | jq .
```

**Output:**
```json
{
  "timestamp": "2025-11-04T12:34:56",
  "file": "settings.json",
  "key": "cachingStrategy",
  "change_type": "agentic_optimization",
  "reason": "High memory at 92.0%, reducing cache",
  "confidence": 0.92,
  "session_id": "simple_optimizer_20251104_123456"
}
```

### Step 4: Watchdog Verification

Next Claude Code session:

```
🤖 Analyzing statusline change in settings.json...

✅ Agentic modification detected:
   Reason: High memory at 92.0%, reducing cache
   Confidence: 92.0%
   Action: Notification only (trusted change)

Configs healed: 0
```

## Integration with Agentic System

These workflows are **production-ready** for integration with:

### Temporal Workflows

```python
# 6-hour optimization cycles
@workflow.defn
class ClaudeDeepLearningWorkflow:
    @workflow.run
    async def run(self):
        # Collect metrics
        metrics = await collect_performance_metrics()

        # Analyze and optimize with marker system
        result = await analyze_and_optimize(metrics, session_id)

        # Watchdog recognizes markers automatically
        return result
```

### AutoKitteh Events

```python
# Real-time event response
def on_high_memory(event: Dict) -> Dict:
    optimizer = SystemEventOptimizer()
    memory_percent = event['memory_percent']

    # Optimizes with marker system
    return optimizer.handle_high_memory_event(memory_percent)
```

### n8n Workflows (Future)

Ready for n8n integration when needed.

## Files

```
workflows/
├── README.md                                    # This file
├── DEPLOYMENT_GUIDE.md                          # Full deployment guide
├── simple_optimizer.py                          # Standalone optimizer
├── temporal/
│   └── claude_deep_learning_optimizer.py        # Temporal workflow
└── autokitteh/
    └── system_event_optimizer.py                # Event handlers
```

## Documentation

- **Usage Guide:** `../intelligent-self-healing/AGENTIC_MARKER_USAGE_GUIDE.md`
- **Testing:** `../intelligent-self-healing/TEST_AGENTIC_MARKERS.md`
- **Implementation:** `../intelligent-self-healing/AGENTIC_SELF_IMPROVEMENT_COMPLETE.md`
- **Deployment:** `DEPLOYMENT_GUIDE.md`

## Next Steps

### Immediate (Now)

1. **Test simple optimizer:**
   ```bash
   python3 simple_optimizer.py --dry-run
   ```

2. **Run with optimizations:**
   ```bash
   python3 simple_optimizer.py
   ```

3. **Verify markers:**
   ```bash
   tail ~/.claude/.config_modifications.jsonl | jq .
   ```

### Short-term (This Week)

1. **Deploy Temporal workflow** for continuous optimization
2. **Set up AutoKitteh handlers** for real-time response
3. **Monitor optimization patterns** via logs

### Long-term (This Month)

1. **Analyze learning memory** for optimization patterns
2. **Tune confidence thresholds** based on results
3. **Expand modifiable keys** as needed
4. **Add custom optimizations** for specific use cases

## Success Criteria

✅ **Working:** Optimizations applied with marker system
✅ **Protected:** Watchdog recognizes and preserves changes
✅ **Auditable:** Full logging of all decisions
✅ **Safe:** Protected keys never modified
✅ **Intelligent:** Confidence-based decision making

## Support

### Quick Reference

```bash
# Run optimizer
python3 simple_optimizer.py

# Check markers
tail ~/.claude/.config_modifications.jsonl | jq .

# Verify watchdog
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py
```

### Troubleshooting

See `DEPLOYMENT_GUIDE.md` for complete troubleshooting guide.

---

**Status:** ✅ Production Ready
**Last Updated:** 2025-11-04
**Version:** 1.0

**Ready for autonomous self-improvement!** 🚀
