# Agentic Self-Improvement System - Quick Reference

**Version**: 1.0
**Status**: 🟢 OPERATIONAL

## 🚀 Quick Start

### Run Optimization (Standalone)
```bash
# Apply optimizations
python3 /Volumes/SSDRAID0/agentic-system/workflows/simple_optimizer.py

# See what would be done (dry run)
python3 /Volumes/SSDRAID0/agentic-system/workflows/simple_optimizer.py --dry-run
```

### Check System Status
```bash
# Run watchdog verification
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py

# Expected: "Configs healed: 0" (no rollbacks)
```

## 📊 Monitoring

### View Recent Optimizations
```bash
# Last 20 markers
tail -20 ~/.claude/.config_modifications.jsonl | jq .

# Count by type
jq -r '.change_type' ~/.claude/.config_modifications.jsonl | sort | uniq -c

# View specific session
jq 'select(.session_id | contains("optimizer"))' ~/.claude/.config_modifications.jsonl
```

### View Notifications
```bash
# Recent notifications
tail -20 ~/.claude/.config_notifications.jsonl | jq .

# By severity
jq -r '.severity' ~/.claude/.config_notifications.jsonl | sort | uniq -c
```

### Check Watchdog Decisions
```bash
# Recent decisions
tail ~/.claude/intelligent_healing_decisions.jsonl | jq .
```

## 🔧 Workflows

### Simple Optimizer
```bash
# Location
/Volumes/SSDRAID0/agentic-system/workflows/simple_optimizer.py

# Usage
python3 simple_optimizer.py [--dry-run]

# What it does
- Analyzes system resources
- Generates optimizations
- Marks changes with markers
- Verifies with watchdog
```

### Temporal Deep Learning
```bash
# Location
/Volumes/SSDRAID0/agentic-system/workflows/temporal/claude_deep_learning_optimizer.py

# Schedule every 6 hours
temporal workflow start \
  --type ClaudeDeepLearningWorkflow \
  --task-queue claude-optimization \
  --cron "0 */6 * * *"

# What it does
- Collects performance metrics
- Analyzes patterns over time
- Applies multi-parameter optimizations
- Stores learning memory
```

### AutoKitteh Event Handlers
```bash
# Location
/Volumes/SSDRAID0/agentic-system/workflows/autokitteh/system_event_optimizer.py

# Deploy
ak deploy system_optimizer.kitteh

# Test events
curl -X POST http://localhost:9980/events/memory -d '{"memory_percent": 0.92}'

# What it does
- Responds to system events instantly
- Handles: high memory, high CPU, errors, MCP latency
- Real-time optimization
```

## 🛡️ Safety

### Protected Keys (Never Modified)
```
statusLine.*
hooks.*.path
apiKeys.*
credentials.*
mcpServers.*.command
permissions.*
```

### Modifiable Keys (Safe for Auto-Optimization)
```
maxTokens
contextWindow
parallelToolCalls
maxParallelTools
cachingStrategy
compressionLevel
mcpServers.*.timeout
mcpServers.*.priority
loggingLevel
debugMode
```

### Trust Levels
```
agentic_optimization (0.95) → Notify only
agentic_learning    (0.90) → Notify only
user_edit           (0.85) → AI analyzes
session_start_check (0.50) → AI analyzes
system_boot         (0.30) → AI analyzes
```

## 🔍 Troubleshooting

### Optimization Not Applied
```bash
# Check if key is modifiable
python3 << 'EOF'
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
from intelligent_config_agent import IntelligentConfigAgent

agent = IntelligentConfigAgent()
key = "YOUR_KEY_HERE"
is_modifiable, reason = agent.is_key_modifiable(key)
print(f"Key: {key}")
print(f"Modifiable: {is_modifiable}")
print(f"Reason: {reason}")
EOF
```

### Watchdog Still Healing
```bash
# Check marker exists and is recent (<24h)
tail -1 ~/.claude/.config_modifications.jsonl | jq '.timestamp, .file, .key'

# Check marker age
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
EOF
```

### View Configuration Snapshots
```bash
# List snapshots
ls -lht ~/.claude/config_snapshots/ | head -10

# Restore from snapshot
cp ~/.claude/config_snapshots/TIMESTAMP_settings.json ~/.claude/settings.json
```

## 📁 File Locations

### Tracking Files
```
~/.claude/.config_modifications.jsonl    # Marker tracking
~/.claude/.config_notifications.jsonl    # Notifications
~/.claude/intelligent_healing_decisions.jsonl  # Watchdog decisions
~/.claude/config_snapshots/              # Pre-change backups
```

### Configuration Files
```
~/.claude/settings.json                  # Main settings
~/.claude.json                          # MCP servers
~/.mcp.json                             # Project MCP servers
```

### Workflows
```
/Volumes/SSDRAID0/agentic-system/workflows/
├── simple_optimizer.py                 # Standalone
├── temporal/claude_deep_learning_optimizer.py
└── autokitteh/system_event_optimizer.py
```

### Documentation
```
/Volumes/SSDRAID0/agentic-system/intelligent-self-healing/
├── AGENTIC_MARKER_USAGE_GUIDE.md       # Complete usage guide
├── TEST_AGENTIC_MARKERS.md             # Test suite
├── AGENTIC_SELF_IMPROVEMENT_COMPLETE.md  # Implementation summary
├── PROJECT_COMPLETE.md                  # Full project report
├── SYSTEM_OPERATIONAL.md                # Operational status
└── QUICK_REFERENCE.md                   # This file
```

## 🧪 Testing

### Test Marker System
```bash
# Create test marker
python3 << 'EOF'
import sys
sys.path.insert(0, '/Volumes/SSDRAID0/agentic-system/intelligent-self-healing')
from intelligent_config_agent import IntelligentConfigAgent

agent = IntelligentConfigAgent()
agent.mark_agentic_change(
    file="settings.json",
    key="maxTokens",
    reason="Test marker system",
    confidence=0.95
)
print("✅ Test marker created")
EOF

# Run watchdog - should recognize marker
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py

# Expected: "Configs healed: 0"
```

### Test Event Handlers
```bash
# Run in test mode
cd /Volumes/SSDRAID0/agentic-system/workflows/autokitteh
python3 system_event_optimizer.py

# Tests 4 event types:
# - High memory (92%)
# - High CPU (95%)
# - Error spike (15%)
# - MCP latency (3500ms)
```

### Test Temporal Workflow
```bash
# Run in standalone mode
cd /Volumes/SSDRAID0/agentic-system/workflows/temporal
python3 claude_deep_learning_optimizer.py

# Collects metrics and applies optimizations
```

## 💡 Common Operations

### Manual Optimization
```bash
# Analyze system and apply optimizations
python3 /Volumes/SSDRAID0/agentic-system/workflows/simple_optimizer.py
```

### Check What Changed
```bash
# View recent markers
tail ~/.claude/.config_modifications.jsonl | jq .
```

### Verify Watchdog
```bash
# Run manual check
python3 /Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py
```

### View Learning Memory (Temporal)
```bash
# View what system has learned
tail /tmp/claude_learning_memory.jsonl | jq .
```

### View Event Log (AutoKitteh)
```bash
# View event processing
tail /tmp/autokitteh_events.jsonl | jq .
```

## 🎯 Performance Optimization Targets

### Memory Pressure (>85%)
- **Action**: `cachingStrategy` → conservative
- **Confidence**: 92%

### High Memory Available (>8GB)
- **Action**: `maxTokens` → 250000
- **Confidence**: 88%

### Low Memory (<4GB)
- **Action**: `maxTokens` → 150000
- **Confidence**: 90%

### High CPU (>90%)
- **Action**: `maxParallelTools` -2
- **Confidence**: 89%

### Error Spike (>10%)
- **Action**: `loggingLevel` → DEBUG
- **Confidence**: 90%

### MCP Latency (>1s)
- **Action**: `mcpServers.*.timeout` optimized
- **Confidence**: 88%

## 📞 Support

### Documentation
- **Main Guide**: `AGENTIC_MARKER_USAGE_GUIDE.md`
- **Tests**: `TEST_AGENTIC_MARKERS.md`
- **Status**: `SYSTEM_OPERATIONAL.md`
- **Complete Report**: `PROJECT_COMPLETE.md`

### Quick Commands
```bash
# Check system
/Volumes/SSDRAID0/agentic-system/intelligent-self-healing/intelligent_statusline_watchdog.py

# Run optimizer
/Volumes/SSDRAID0/agentic-system/workflows/simple_optimizer.py

# View markers
tail ~/.claude/.config_modifications.jsonl | jq .
```

---

**Status**: 🟢 OPERATIONAL
**Version**: 1.0
**Updated**: 2025-11-04

**System ready for autonomous 24/7 self-improvement!** 🚀
