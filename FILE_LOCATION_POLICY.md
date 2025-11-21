# File Location Policy - Agentic System

**Created:** 2025-11-20
**Priority:** CRITICAL
**Purpose:** Enforce proper file storage locations to keep system drive clean

---

## 🎯 Core Principle

**ALL agentic system data MUST live on `/Volumes/SSDRAID0/agentic-system/`**

Only configuration files required by external tools (Claude Code CLI) may use system locations.

---

## ✅ CORRECT Locations

### Configuration Files (System Drive OK - Required by Tools)

```
~/.claude/
├── settings.json          ✅ Claude Code CLI config
├── settings.local.json    ✅ Claude Code CLI local settings
├── CLAUDE.md             ✅ Claude Code instructions
├── .claude.json          ✅ MCP server config (user-level)
├── .mcp.json             ✅ MCP server config (project-level)
├── hooks/                ✅ Claude Code hooks (required location)
├── commands/             ✅ Custom slash commands
├── agents/               ✅ Sub-agent definitions
└── skills/               ✅ Compositional skills
```

**Why OK?** Claude Code CLI requires these in `~/.claude/` to function.

### Data, Logs, Databases (MUST be on SSDRAID0)

```
/Volumes/SSDRAID0/agentic-system/
├── databases/            ✅ ALL databases
│   ├── meta_learning.db
│   ├── darwin_godel.db
│   ├── capability_registry.db
│   ├── cluster/
│   ├── temporal/         ✅ Move from /tmp/temporal.db
│   └── qdrant/
├── logs/                 ✅ ALL logs
│   ├── improvement_cycles/
│   ├── improvement_proposals/
│   ├── autonomous_improvement.log
│   ├── performance/      ✅ NEW: claude_performance_metrics.json
│   ├── learning/         ✅ NEW: claude_learning_memory.jsonl
│   ├── self_healing/     ✅ NEW: self_healing_status.json
│   ├── autokitteh/       ✅ NEW: autokitteh_events.jsonl
│   ├── alerts/           ✅ NEW: maintenance alerts
│   └── optimizations/    ✅ NEW: applied optimizations
├── tmp-workspace/        ✅ Temporary working files
└── mcp-servers/          ✅ MCP server code
```

---

## ❌ FORBIDDEN Locations

### Never Write Here

```
/tmp/                     ❌ EXCEPT truly temporary (< 1 hour lifetime)
/Users/marc/              ❌ NEVER (except ~/.claude/ for configs)
~/                        ❌ NEVER (except ~/.claude/ for configs)
/Volumes/FILES/           ❌ NEVER (backup drive, read-only)
```

### Exceptions (Truly Temporary Only)

`/tmp/` is acceptable ONLY for:
- Files that live < 1 hour
- Intermediate processing steps
- Files that can be lost on reboot without issue

**NOT acceptable for:**
- Learning memory
- Performance metrics
- Event logs
- Status tracking
- Any data that should persist

---

## 🔧 Migration Required

### Files Currently in Wrong Locations

**High Priority - Move Immediately:**

1. **Temporal Database**
   - Current: `/tmp/temporal.db`
   - Should be: `/Volumes/SSDRAID0/agentic-system/databases/temporal/temporal.db`
   - Files: `temporal.db`, workflow data

2. **Performance Metrics**
   - Current: `/tmp/claude_performance_metrics.json`
   - Should be: `/Volumes/SSDRAID0/agentic-system/logs/performance/claude_metrics.json`
   - Referenced in: `workflows/temporal/claude_deep_learning_optimizer.py`

3. **Learning Memory**
   - Current: `/tmp/claude_learning_memory.jsonl`
   - Should be: `/Volumes/SSDRAID0/agentic-system/logs/learning/learning_memory.jsonl`
   - Referenced in: `workflows/temporal/claude_deep_learning_optimizer.py`

4. **Self-Healing Status**
   - Current: `/tmp/self_healing_status.json`
   - Should be: `/Volumes/SSDRAID0/agentic-system/logs/self_healing/status.json`
   - Referenced in: `workflows/self_healing_monitor.py`

5. **AutoKitteh Events**
   - Current: `/tmp/autokitteh_events.jsonl`
   - Should be: `/Volumes/SSDRAID0/agentic-system/logs/autokitteh/events.jsonl`
   - Referenced in: `workflows/autokitteh/system_event_optimizer.py`

6. **Claude Monitor Outputs**
   - Current: `/tmp/claude_pattern_analysis.json`
   - Should be: `/Volumes/SSDRAID0/agentic-system/logs/performance/pattern_analysis.json`
   - Current: `/tmp/claude_maintenance_alerts.json`
   - Should be: `/Volumes/SSDRAID0/agentic-system/logs/alerts/maintenance_alerts.json`
   - Current: `/tmp/claude_optimizations_applied.json`
   - Should be: `/Volumes/SSDRAID0/agentic-system/logs/optimizations/applied.json`
   - Current: `/tmp/claude_learning_summary.json`
   - Should be: `/Volumes/SSDRAID0/agentic-system/logs/learning/summary.json`
   - Referenced in: `workflows/autokitteh/handlers/claude_monitor_handlers.py`

7. **Proactive Memory Database**
   - Current: `~/.claude/enhanced_memories/memory.db`
   - Should be: `/Volumes/SSDRAID0/agentic-system/databases/enhanced_memory/memory.db`
   - Referenced in: `intelligent-agents/proactive_memory_loader.py`

**Medium Priority - Update in Next Release:**

8. **Hardcoded User Paths**
   - Files with `/Users/marc` hardcoded
   - Replace with environment variable or config file

---

## 🛠️ Implementation Checklist

### Phase 1: Create Directory Structure

```bash
# Create new log directories
mkdir -p /Volumes/SSDRAID0/agentic-system/logs/performance
mkdir -p /Volumes/SSDRAID0/agentic-system/logs/learning
mkdir -p /Volumes/SSDRAID0/agentic-system/logs/self_healing
mkdir -p /Volumes/SSDRAID0/agentic-system/logs/autokitteh
mkdir -p /Volumes/SSDRAID0/agentic-system/logs/alerts
mkdir -p /Volumes/SSDRAID0/agentic-system/logs/optimizations
mkdir -p /Volumes/SSDRAID0/agentic-system/databases/temporal
mkdir -p /Volumes/SSDRAID0/agentic-system/databases/enhanced_memory
```

### Phase 2: Update Code References

**Files to Update:**

1. `workflows/temporal/claude_deep_learning_optimizer.py`
   - Line 44: metrics_file path
   - Line 45: learning_memory path
   - Line 355: learning_memory path
   - Line 421: learning_memory path

2. `workflows/self_healing_monitor.py`
   - status_file path

3. `workflows/autokitteh/system_event_optimizer.py`
   - event_log path

4. `workflows/autokitteh/handlers/claude_monitor_handlers.py`
   - All /tmp/ references

5. `intelligent-agents/proactive_memory_loader.py`
   - memory_db path

### Phase 3: Migrate Existing Data

```bash
# Move existing files (if they exist)
mv /tmp/claude_performance_metrics.json /Volumes/SSDRAID0/agentic-system/logs/performance/claude_metrics.json 2>/dev/null || true
mv /tmp/claude_learning_memory.jsonl /Volumes/SSDRAID0/agentic-system/logs/learning/learning_memory.jsonl 2>/dev/null || true
mv /tmp/self_healing_status.json /Volumes/SSDRAID0/agentic-system/logs/self_healing/status.json 2>/dev/null || true
mv /tmp/autokitteh_events.jsonl /Volumes/SSDRAID0/agentic-system/logs/autokitteh/events.jsonl 2>/dev/null || true
```

### Phase 4: Update Temporal Configuration

```bash
# Stop Temporal server
pkill -f "temporal server"

# Move database
mv /tmp/temporal.db /Volumes/SSDRAID0/agentic-system/databases/temporal/ 2>/dev/null || true

# Restart with new location
temporal server start-dev \
  --db-filename /Volumes/SSDRAID0/agentic-system/databases/temporal/temporal.db \
  --ui-port 8233
```

### Phase 5: Verification

```bash
# Verify no new files in /tmp (except truly temporary)
watch -n 60 'ls -lt /tmp/*.json /tmp/*.jsonl /tmp/*.db 2>/dev/null | head -10'

# Verify files are being written to correct locations
watch -n 60 'ls -lt /Volumes/SSDRAID0/agentic-system/logs/*/*.json | head -10'
```

---

## 📋 Code Patterns

### ✅ CORRECT Pattern

```python
from pathlib import Path

# Base path for all agentic system data
AGENTIC_BASE = Path("/Volumes/SSDRAID0/agentic-system")

# Logs
LOG_DIR = AGENTIC_BASE / "logs"
PERFORMANCE_LOG = LOG_DIR / "performance" / "metrics.json"

# Databases
DB_DIR = AGENTIC_BASE / "databases"
META_LEARNING_DB = DB_DIR / "meta_learning.db"
```

### ❌ INCORRECT Pattern

```python
# WRONG - using /tmp for persistent data
metrics_file = Path("/tmp/claude_performance_metrics.json")

# WRONG - using home directory for data
memory_db = Path.home() / ".claude" / "enhanced_memories" / "memory.db"

# WRONG - hardcoded username
config = Path("/Users/marc/agentic-system/config.json")
```

---

## 🔍 Audit Commands

### Find Files in Wrong Locations

```bash
# Find /tmp references in code
grep -r "/tmp/" /Volumes/SSDRAID0/agentic-system --include="*.py" | grep -v ".pyc"

# Find home directory data storage
grep -r "Path.home()" /Volumes/SSDRAID0/agentic-system --include="*.py" | grep -v ".claude.json"

# Find hardcoded user paths
grep -r "/Users/marc" /Volumes/SSDRAID0/agentic-system --include="*.py"
```

### Monitor File Creation

```bash
# Watch for new files in forbidden locations
fswatch /tmp /Users/marc | grep -E '\.(json|jsonl|db|log)$'
```

---

## 🚨 Enforcement

### Pre-Commit Hook

Add to `~/.claude/hooks/pre-tool-use.py`:

```python
def check_file_locations(tool_name, params):
    """Enforce file location policy"""
    forbidden_paths = [
        "/tmp/",
        "/Users/marc/",
        str(Path.home()),
        "/Volumes/FILES/"
    ]

    # Check file paths in Write, Edit operations
    if tool_name in ["Write", "Edit", "MultiEdit"]:
        file_path = params.get("file_path", "")

        for forbidden in forbidden_paths:
            if file_path.startswith(forbidden):
                # Allow ~/.claude/ for configs
                if "/.claude/" in file_path:
                    continue

                raise ValueError(
                    f"FORBIDDEN: Cannot write to {file_path}\n"
                    f"Use /Volumes/SSDRAID0/agentic-system/ instead\n"
                    f"See FILE_LOCATION_POLICY.md"
                )
```

---

## ✅ Verification Checklist

After migration, verify:

- [ ] No files in `/tmp/` older than 1 hour
- [ ] No data files in `/Users/marc/` (except `~/.claude/` configs)
- [ ] All logs in `/Volumes/SSDRAID0/agentic-system/logs/`
- [ ] All databases in `/Volumes/SSDRAID0/agentic-system/databases/`
- [ ] Temporal using SSDRAID0 database
- [ ] All workflows updated with new paths
- [ ] Pre-commit hook enforcing policy
- [ ] No hardcoded `/Users/marc` paths remain

---

## 📚 References

- **Primary Storage:** `/Volumes/SSDRAID0/agentic-system/`
- **Backup (Read-Only):** `/Volumes/FILES/agentic-system/`
- **Config Only:** `~/.claude/`
- **Truly Temporary:** `/tmp/` (< 1 hour lifetime)

---

**Next Steps:**
1. Run Phase 1 (create directories)
2. Run Phase 2 (update code)
3. Run Phase 3 (migrate data)
4. Run Phase 4 (reconfigure Temporal)
5. Run Phase 5 (verification)
6. Add pre-commit hook enforcement
