# Agentic Modification Marker System - Usage Guide

**Date:** 2025-11-04
**Status:** ✅ Production Ready
**Purpose:** Enable agentic system to signal intentional self-improvements without triggering watchdog rollbacks

## Overview

The marker system allows agentic workflows (Temporal, AutoKitteh, deep learning cycles) to signal that configuration changes are **intentional self-improvements**, not corruption or errors.

### Problem Solved

**Before:** Watchdog couldn't distinguish between:
- ✅ Agentic system optimizing configurations
- ❌ System corruption or bugs
- ✅ User manual edits

**After:** Agentic system marks changes with metadata:
- **What** was changed
- **Why** it was changed
- **When** it was changed
- **Confidence** in the change

Watchdog checks for markers first, only analyzes if no marker found.

## Quick Start

### 1. Basic Usage Pattern

```python
from pathlib import Path
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
from intelligent_config_agent import IntelligentConfigAgent

# Initialize agent
agent = IntelligentConfigAgent()

# Make configuration change
import json
settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)

settings['maxTokens'] = 100000  # Optimization

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

# Mark it as intentional agentic change
agent.mark_agentic_change(
    file="settings.json",
    key="maxTokens",
    reason="Increased based on deep learning performance analysis",
    confidence=0.95,
    session_id="deep_learning_cycle_001"
)
```

### 2. Trust Levels

Different change types have different trust levels:

```python
from intelligent_config_agent import TRUST_LEVELS

# agentic_optimization - Highest trust (notify only, never heal)
agent.mark_agentic_change(
    file="settings.json",
    key="parallelToolCalls",
    reason="Enabled for 2x performance boost",
    change_type="agentic_optimization",  # ← Trust level 0.95
    confidence=0.95
)

# agentic_learning - High trust (notify only)
agent.mark_agentic_change(
    file="settings.json",
    key="learningRate",
    reason="Adjusted based on training metrics",
    change_type="agentic_learning",  # ← Trust level 0.90
    confidence=0.90
)
```

## Trust Levels Reference

| Change Type | Trust | Requires Analysis | Notify Only | Auto-Heal Threshold |
|-------------|-------|-------------------|-------------|---------------------|
| `agentic_optimization` | 0.95 | No | Yes | None (never heals) |
| `agentic_learning` | 0.90 | No | Yes | None |
| `user_edit` | 0.85 | Yes | No | 0.85 |
| `session_start_check` | 0.50 | Yes | No | 0.70 |
| `system_boot` | 0.30 | Yes | No | 0.60 |

## Allowlist & Blocklist

### What Can Be Modified

Check if a key is modifiable before changing:

```python
from intelligent_config_agent import IntelligentConfigAgent

agent = IntelligentConfigAgent()

# Check if key can be modified
is_modifiable, reason = agent.is_key_modifiable("maxTokens")
print(f"Can modify: {is_modifiable} - {reason}")
# Output: Can modify: True - Allowlisted key: maxTokens

is_modifiable, reason = agent.is_key_modifiable("statusLine.command")
print(f"Can modify: {is_modifiable} - {reason}")
# Output: Can modify: False - Protected key: statusLine.command
```

### Allowlisted Keys (Safe for Agentic Modification)

```python
AGENTIC_MODIFIABLE_KEYS = {
    # Performance optimization
    "maxTokens",
    "contextWindow",
    "parallelToolCalls",
    "maxParallelTools",

    # Memory management
    "memoryTiers",
    "cachingStrategy",
    "compressionLevel",

    # MCP server tuning (not adding/removing)
    "mcpServers.*.priority",      # Wildcard: any server's priority
    "mcpServers.*.timeout",
    "mcpServers.*.retries",

    # Learning parameters
    "learningRate",
    "explorationFactor",
    "optimizationLevel",

    # System parameters
    "loggingLevel",
    "metricsCollection",
    "debugMode"
}
```

### Protected Keys (Never Auto-Modify)

```python
PROTECTED_KEYS = {
    # Core configuration
    "statusLine.command",
    "statusLine.type",

    # Hooks (critical for system integrity)
    "hooks.PreToolUse.path",
    "hooks.PostToolUse.path",
    "hooks.*.path",              # All hook paths protected

    # Security
    "apiKeys.*",                 # All API keys
    "credentials.*",             # All credentials
    "ANTHROPIC_API_KEY",

    # MCP server structure
    "mcpServers.*.command",      # Can tune params, not commands
    "mcpServers.*.args",

    # Permissions
    "permissions.*",
    "bypassPermissions"
}
```

## Complete Workflow Examples

### Example 1: Temporal Deep Learning Cycle

```python
#!/usr/bin/env python3
"""
Temporal worker for Claude deep learning cycle
Shows how to mark optimizations
"""
import sys
from pathlib import Path
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')

from intelligent_config_agent import IntelligentConfigAgent
import json

def optimize_performance():
    """Analyze performance and optimize settings"""

    agent = IntelligentConfigAgent()
    settings_file = Path.home() / ".claude" / "settings.json"

    # Load current settings
    with open(settings_file, 'r') as f:
        settings = json.load(f)

    # Analyze and optimize
    optimizations = analyze_performance_data()  # Your analysis logic

    for key, new_value, reason, confidence in optimizations:
        # Check if key can be modified
        is_modifiable, mod_reason = agent.is_key_modifiable(key)

        if not is_modifiable:
            print(f"⚠️  Skipping {key}: {mod_reason}")
            continue

        # Apply optimization
        old_value = settings.get(key)
        settings[key] = new_value

        print(f"🔧 Optimizing {key}: {old_value} → {new_value}")
        print(f"   Reason: {reason}")

        # Mark as intentional change
        agent.mark_agentic_change(
            file="settings.json",
            key=key,
            reason=reason,
            change_type="agentic_optimization",
            confidence=confidence,
            session_id="deep_learning_cycle"
        )

    # Save optimized settings
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)

    print(f"✅ Applied {len(optimizations)} optimizations")

def analyze_performance_data():
    """Mock performance analysis - replace with real logic"""
    return [
        ("maxTokens", 100000, "Increased for better context retention", 0.95),
        ("parallelToolCalls", True, "Enabled for 2x speedup in multi-tool ops", 0.92),
        ("loggingLevel", "INFO", "Reduced from DEBUG to improve performance", 0.88)
    ]

if __name__ == "__main__":
    optimize_performance()
```

### Example 2: AutoKitteh Event Handler

```python
#!/usr/bin/env python3
"""
AutoKitteh event handler that optimizes based on triggers
"""
import sys
from pathlib import Path
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')

from intelligent_config_agent import IntelligentConfigAgent

def handle_high_memory_event(memory_usage: float):
    """Respond to high memory usage by optimizing"""

    if memory_usage < 0.85:
        return  # Not critical

    agent = IntelligentConfigAgent()

    # Check if we can modify caching strategy
    is_modifiable, reason = agent.is_key_modifiable("cachingStrategy")
    if not is_modifiable:
        print(f"⚠️  Cannot optimize caching: {reason}")
        return

    # Optimize caching to reduce memory
    settings_file = Path.home() / ".claude" / "settings.json"

    import json
    with open(settings_file, 'r') as f:
        settings = json.load(f)

    old_strategy = settings.get('cachingStrategy', 'aggressive')
    settings['cachingStrategy'] = 'conservative'

    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)

    # Mark change
    agent.mark_agentic_change(
        file="settings.json",
        key="cachingStrategy",
        reason=f"Memory usage at {memory_usage:.1%}, reducing caching to free memory",
        change_type="agentic_optimization",
        confidence=0.93,
        session_id=f"autokitteh_memory_event_{int(memory_usage*100)}"
    )

    print(f"✅ Optimized caching: {old_strategy} → conservative")

    # Optional: Notify user via voice
    agent.notify_change(
        change_info={
            "file": "settings.json",
            "key": "cachingStrategy",
            "reason": f"Reduced caching due to {memory_usage:.1%} memory usage"
        },
        severity="info",
        use_voice=True
    )

if __name__ == "__main__":
    # Example: triggered by AutoKitteh
    handle_high_memory_event(0.92)  # 92% memory usage
```

### Example 3: MCP Server Parameter Tuning

```python
#!/usr/bin/env python3
"""
Optimize MCP server timeouts based on performance data
"""
import sys
from pathlib import Path
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')

from intelligent_config_agent import IntelligentConfigAgent
import json

def optimize_mcp_timeouts():
    """Adjust MCP server timeouts based on observed latency"""

    agent = IntelligentConfigAgent()

    # Performance data (mock - replace with real metrics)
    latency_data = {
        "enhanced-memory": 150,      # ms
        "voice-mode": 3500,          # ms (slow!)
        "arduino-surface": 50,       # ms (fast)
    }

    mcp_config_file = Path.home() / ".claude.json"

    with open(mcp_config_file, 'r') as f:
        config = json.load(f)

    optimizations = []

    for server_name, avg_latency in latency_data.items():
        # Calculate optimal timeout (3x average latency + buffer)
        optimal_timeout = int(avg_latency * 3 + 1000)

        key = f"mcpServers.{server_name}.timeout"

        # Check if we can modify this
        is_modifiable, reason = agent.is_key_modifiable(key)
        if not is_modifiable:
            print(f"⚠️  Cannot modify {key}: {reason}")
            continue

        # Check if server exists in config
        if server_name not in config.get('mcpServers', {}):
            print(f"⚠️  Server {server_name} not in config")
            continue

        # Get current timeout
        current_timeout = config['mcpServers'][server_name].get('timeout', 5000)

        # Only change if significantly different
        if abs(optimal_timeout - current_timeout) > 500:
            config['mcpServers'][server_name]['timeout'] = optimal_timeout

            optimizations.append({
                "key": key,
                "old": current_timeout,
                "new": optimal_timeout,
                "latency": avg_latency
            })

            # Mark change
            agent.mark_agentic_change(
                file=".claude.json",
                key=key,
                reason=f"Optimized timeout based on {avg_latency}ms avg latency",
                change_type="agentic_optimization",
                confidence=0.88
            )

    if optimizations:
        # Save changes
        with open(mcp_config_file, 'w') as f:
            json.dump(config, f, indent=2)

        print(f"✅ Optimized {len(optimizations)} MCP server timeouts:")
        for opt in optimizations:
            print(f"   {opt['key']}: {opt['old']}ms → {opt['new']}ms (latency: {opt['latency']}ms)")
    else:
        print("✅ All MCP timeouts already optimal")

if __name__ == "__main__":
    optimize_mcp_timeouts()
```

## Checking for Existing Markers

```python
from intelligent_config_agent import IntelligentConfigAgent

agent = IntelligentConfigAgent()

# Check for recent marker (last 24 hours)
marker = agent.check_agentic_marker(
    file="settings.json",
    key="maxTokens",
    ***REMOVED***
)

if marker:
    print(f"Found marker:")
    print(f"  Timestamp: {marker['timestamp']}")
    print(f"  Reason: {marker['reason']}")
    print(f"  Confidence: {marker['confidence']}")
    print(f"  Type: {marker['change_type']}")
    print(f"  Session: {marker.get('session_id', 'N/A')}")
else:
    print("No recent marker found")
```

## Notification System

The system can notify about changes without blocking:

```python
from intelligent_config_agent import IntelligentConfigAgent

agent = IntelligentConfigAgent()

# Notify about optimization (with voice)
agent.notify_change(
    change_info={
        "file": "settings.json",
        "key": "maxTokens",
        "reason": "Optimized for better performance"
    },
    severity="info",      # info, warning, or error
    use_voice=True        # Use voice-mode if available
)
```

Notifications are logged to `~/.claude/.config_notifications.jsonl`:

```json
{
  "timestamp": "2025-11-04T10:30:00",
  "severity": "info",
  "details": {
    "file": "settings.json",
    "key": "maxTokens",
    "reason": "Optimized for better performance"
  }
}
```

## Testing Your Integration

### Manual Test

```bash
# 1. Create a test marker
python3 << 'EOF'
from pathlib import Path
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
from intelligent_config_agent import IntelligentConfigAgent

agent = IntelligentConfigAgent()
agent.mark_agentic_change(
    file="settings.json",
    key="maxTokens",
    reason="Test agentic modification",
    confidence=0.95
)
print("✅ Test marker created")
EOF

# 2. Make actual change
python3 << 'EOF'
import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)

settings['maxTokens'] = 99999  # Test value

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("✅ Test change applied")
EOF

# 3. Run watchdog - should NOT heal (marker present)
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py

# Expected output:
# ✅ Agentic modification detected:
#    Reason: Test agentic modification
#    Confidence: 95.0%
#    Action: Notification only (trusted change)

# 4. Clean up
python3 << 'EOF'
import json
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"
with open(settings_file, 'r') as f:
    settings = json.load(f)

settings['maxTokens'] = 200000  # Restore

with open(settings_file, 'w') as f:
    json.dump(settings, f, indent=2)

print("✅ Restored original value")
EOF
```

### Automated Test Suite

See `TEST_AGENTIC_MARKERS.md` for complete test scenarios.

## Troubleshooting

### Marker Not Found

**Problem:** Watchdog still analyzing even though marker was created.

**Solutions:**
1. Check marker file exists: `cat ~/.claude/.config_modifications.jsonl`
2. Verify file name matches exactly (e.g., "settings.json" not "~/.claude/settings.json")
3. Check marker timestamp is within 24 hours
4. Verify marker JSON is valid

### Change Still Got Healed

**Problem:** Watchdog restored config even with marker.

**Reasons:**
1. Marker confidence too low (<0.70)
2. Key is in PROTECTED_KEYS list
3. Marker older than 24 hours
4. Trust level requires analysis (check TRUST_LEVELS)

**Solutions:**
1. Use higher confidence (>0.85)
2. Check if key is modifiable: `agent.is_key_modifiable(key)`
3. Create fresh marker before change
4. Use `change_type="agentic_optimization"` for highest trust

### Voice Notification Not Working

**Problem:** `use_voice=True` but no voice notification.

**Solutions:**
1. Voice-mode MCP might not be available
2. Silent fail by design (doesn't break system)
3. Check voice-mode status: `/status` in Claude Code
4. Notification still logged even if voice fails

## Best Practices

### 1. Always Check Modifiability First

```python
is_modifiable, reason = agent.is_key_modifiable(key)
if not is_modifiable:
    print(f"⚠️  Cannot modify {key}: {reason}")
    return
```

### 2. Use High Confidence for Critical Changes

```python
agent.mark_agentic_change(
    file="settings.json",
    key="maxTokens",
    reason="Critical performance optimization",
    confidence=0.95  # High confidence = trusted
)
```

### 3. Provide Detailed Reasons

```python
# ❌ Bad
reason="optimizing"

# ✅ Good
reason="Increased from 50K to 100K based on 2-week performance analysis showing 35% improvement in long-context tasks"
```

### 4. Use Session IDs for Tracking

```python
agent.mark_agentic_change(
    file="settings.json",
    key="parallelToolCalls",
    reason="Enabled parallel execution",
    confidence=0.92,
    session_id="deep_learning_cycle_20251104_001"  # ← Traceable
)
```

### 5. Test Before Deploying

Always test your integration manually before running in production:

```python
# Dry run mode
def optimize_settings(dry_run=True):
    # ... analyze ...

    if dry_run:
        print(f"Would mark: {key} = {new_value}")
        return

    # Actually apply and mark
    agent.mark_agentic_change(...)
```

## Integration Checklist

Before deploying agentic workflow with marker system:

- [ ] Import `IntelligentConfigAgent` correctly
- [ ] Check key modifiability before changing
- [ ] Use appropriate trust level (`agentic_optimization` for most cases)
- [ ] Provide detailed, traceable reasons
- [ ] Include session_id for tracking
- [ ] Test manually with watchdog before production
- [ ] Handle errors gracefully (marker creation can fail)
- [ ] Don't mark changes to PROTECTED_KEYS
- [ ] Use high confidence (>0.85) for automatic approval
- [ ] Consider voice notifications for important changes

## File Locations

- **Marker log**: `~/.claude/.config_modifications.jsonl`
- **Notification log**: `~/.claude/.config_notifications.jsonl`
- **Agent module**: `/Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_config_agent.py`
- **Watchdog**: `/Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py`

## Related Documentation

- **Implementation Details**: `AGENTIC_SELF_IMPROVEMENT_AUDIT.md`
- **System Overview**: `README.md`
- **Testing Guide**: `TEST_AGENTIC_MARKERS.md`

## Summary

The marker system enables true agentic self-improvement:

✅ **Agentic system can modify safe keys** (allowlist)
✅ **Watchdog recognizes intentional changes** (markers)
✅ **Critical keys protected** (blocklist)
✅ **Notifications instead of blocking** (trust levels)
✅ **Full auditability** (JSONL logs)

**Result:** The agentic system can self-improve without being blocked by its own protections.

---

**Status**: ✅ Production Ready
**Last Updated**: 2025-11-04
**Version**: 1.0
