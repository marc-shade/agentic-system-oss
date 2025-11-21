# File Location Migration - COMPLETE ✅

**Date**: 2025-11-20
**Status**: Successfully completed

---

## Migration Summary

Fixed systemic file location policy violations - all agentic system data now lives on SSDRAID0 as required.

### Issues Fixed

**7 File Location Violations Corrected:**

1. **Temporal Database** - `/tmp/temporal.db` (163MB) → SSDRAID0
2. **Enhanced Memory Database** - `~/.claude/enhanced_memories/memory.db` (55MB) → SSDRAID0
3. **Performance Metrics** - `/tmp/claude_performance_metrics.json` → SSDRAID0
4. **Learning Memory** - `/tmp/claude_learning_memory.jsonl` → SSDRAID0
5. **Self-Healing Status** - `/tmp/self_healing_status.json` → SSDRAID0
6. **AutoKitteh Events** - `/tmp/autokitteh_events.jsonl` → SSDRAID0
7. **Monitor Outputs** - 4 files in `/tmp/claude_*.json` → SSDRAID0

---

## Changes Made

### Phase 1: Directory Structure ✅
Created all required directories on SSDRAID0:
```bash
/Volumes/SSDRAID0/agentic-system/logs/
├── performance/
├── learning/
├── self_healing/
├── autokitteh/
├── alerts/
└── optimizations/

/Volumes/SSDRAID0/agentic-system/databases/
├── temporal/
└── enhanced_memory/
```

### Phase 2: Code Updates ✅
Updated 5 files with 11 total path corrections:

1. **workflows/temporal/claude_deep_learning_optimizer.py** (3 fixes)
   - metrics_file: `/tmp/` → `/Volumes/SSDRAID0/agentic-system/logs/performance/`
   - learning_memory: `/tmp/` → `/Volumes/SSDRAID0/agentic-system/logs/learning/`

2. **workflows/self_healing_monitor.py** (1 fix)
   - status_file: `/tmp/` → `/Volumes/SSDRAID0/agentic-system/logs/self_healing/`

3. **workflows/autokitteh/system_event_optimizer.py** (1 fix)
   - event_log: `/tmp/` → `/Volumes/SSDRAID0/agentic-system/logs/autokitteh/`

4. **workflows/autokitteh/handlers/claude_monitor_handlers.py** (5 fixes)
   - claude_metrics.json: `/tmp/` → `logs/performance/`
   - pattern_analysis.json: `/tmp/` → `logs/performance/`
   - maintenance_alerts.json: `/tmp/` → `logs/alerts/`
   - applied.json: `/tmp/` → `logs/optimizations/`
   - summary.json: `/tmp/` → `logs/learning/`

5. **intelligent-agents/proactive_memory_loader.py** (1 fix)
   - memory_db: `~/.claude/enhanced_memories/` → `/Volumes/SSDRAID0/agentic-system/databases/enhanced_memory/`

**Pattern Used:**
```python
# Store on SSDRAID0 (not /tmp - see FILE_LOCATION_POLICY.md)
base = Path("/Volumes/SSDRAID0/agentic-system")
file_path = base / "logs/category/filename.json"
file_path.parent.mkdir(parents=True, exist_ok=True)
```

### Phase 3: Data Migration ✅
Moved existing databases:
```bash
mv /tmp/temporal.db → /Volumes/SSDRAID0/agentic-system/databases/temporal/
mv ~/.claude/enhanced_memories/memory.db → /Volumes/SSDRAID0/agentic-system/databases/enhanced_memory/
```

### Phase 4: Temporal Restart ✅
Restarted Temporal server with new database location:
```bash
pkill -f "temporal server"
temporal server start-dev \
  --db-filename /Volumes/SSDRAID0/agentic-system/databases/temporal/temporal.db \
  --ui-port 8233
```

**Verification:**
```
✓ PID 11336 running with correct database path
✓ temporal.db size: 163MB
```

### Phase 5: Enforcement Hook ✅
Added pre-commit hook enforcement to prevent future violations:

**Created:** `~/.claude/hooks/file_location_enforcement.py`
- Blocks Write/Edit/MultiEdit to forbidden locations
- Allows exception for `~/.claude/` configs
- Integrated into `pre-tool-use.py` hook

**Forbidden Locations:**
- `/tmp/` (except truly temporary files)
- `/Users/marc/` (except `~/.claude/` configs)
- `/Volumes/FILES/` (backup drive, read-only)

**Test Results:**
```
✓ PASS: Write to SSDRAID0
✓ PASS: Write to ~/.claude/ (exception)
✓ PASS: Read from /tmp/ (reads allowed)
✗ FAIL: Write to /tmp/ (correctly blocked!)
✗ FAIL: Write to /Users/marc/ (correctly blocked!)
```

---

## Verification

### Database Locations ✅
```bash
/Volumes/SSDRAID0/agentic-system/databases/temporal/temporal.db - 163MB
/Volumes/SSDRAID0/agentic-system/databases/enhanced_memory/memory.db - 55MB
```

### Log Directories ✅
```bash
/Volumes/SSDRAID0/agentic-system/logs/alerts/
/Volumes/SSDRAID0/agentic-system/logs/autokitteh/
/Volumes/SSDRAID0/agentic-system/logs/learning/
/Volumes/SSDRAID0/agentic-system/logs/optimizations/
/Volumes/SSDRAID0/agentic-system/logs/performance/
/Volumes/SSDRAID0/agentic-system/logs/self_healing/
```

### No Files in Forbidden Locations ✅
```bash
# Checked for stray files - all clean!
/tmp/claude*.json - NOT FOUND ✓
/tmp/claude*.jsonl - NOT FOUND ✓
/tmp/temporal.db - NOT FOUND ✓
~/.claude/enhanced_memories/memory.db - NOT FOUND ✓
```

### Temporal Running Correctly ✅
```
PID 11336: temporal server start-dev
  --db-filename /Volumes/SSDRAID0/agentic-system/databases/temporal/temporal.db
  --ui-port 8233
```

---

## Reference Documents

- **Policy Document**: `/Volumes/SSDRAID0/agentic-system/FILE_LOCATION_POLICY.md`
- **Enforcement Script**: `~/.claude/hooks/file_location_enforcement.py`
- **Hook Integration**: `~/.claude/hooks/pre-tool-use.py` (lines 86-103, 153-162)

---

## Impact

**Before Migration:**
- 7 critical files in wrong locations
- Temporal database on volatile `/tmp/`
- Enhanced memory database in user directory
- No enforcement mechanism

**After Migration:**
- ✅ All data on SSDRAID0
- ✅ Temporal database persistent and backed up
- ✅ Enhanced memory database properly located
- ✅ Pre-commit hook prevents future violations
- ✅ Clean separation: configs vs data vs backups

**Benefits:**
1. **System Drive Clean** - No agentic data pollution
2. **Persistence** - Databases survive reboots (not in `/tmp/`)
3. **Backups Work** - SSDRAID0 is backed up to `/Volumes/FILES/`
4. **Future-Proof** - Enforcement hook prevents regressions
5. **Maintainability** - Clear policy documented

---

## Automation Review Status

From `/tmp/automation_analysis.md`:
- **Automation Coverage**: 65%
- **Active Workflows**: 7 Temporal workflows running
- **Scheduled Jobs**: 12 AutoKitteh triggers
- **All workflows now using correct file locations** ✅

---

---

## Update 2025-11-20 14:53: Memory DB Service Fix ✅

### Issue Found
After restart, enhanced-memory still using wrong database:
- Was using: `/Users/marc/.claude/enhanced_memories/memory.db` (90 entities)
- Should use: `/Volumes/SSDRAID0/agentic-system/databases/enhanced_memory/memory.db` (33,505 entities)

### Root Cause
`memory_db_service.py` (the actual database service) had hardcoded path that wasn't reading env var:
```python
# Line 39 (OLD - hardcoded)
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
```

### Fix Applied
**File**: `/Volumes/SSDRAID0/agentic-system/mcp-servers/enhanced-memory-mcp/memory_db_service.py`
**Lines**: 39-44

```python
# Use env var or default to SSDRAID0 (see FILE_LOCATION_POLICY.md)
MEMORY_DIR = Path(os.getenv(
    "ENHANCED_MEMORY_DB_DIR",
    "/Volumes/SSDRAID0/agentic-system/databases/enhanced_memory"
))
DB_PATH = MEMORY_DIR / "memory.db"
```

### Config Updated
**File**: `~/.claude/settings.json` (lines 78-86)

Added `ENHANCED_MEMORY_DB_DIR` env var to enhanced-memory MCP server config.

### Verification
```bash
mcp__enhanced-memory__get_memory_status
```

**Results:**
- ✅ Database path: `/Volumes/SSDRAID0/agentic-system/databases/enhanced_memory/memory.db`
- ✅ Entities: 33,505 (correct!)
- ✅ Tiers: Properly distributed (working: 32,452, reference: 1,029, core: 21, archive: 2, episodic: 1)

### For Autonomous Agents

**CRITICAL**: This is an intentional change, NOT a bug!

**Do NOT revert:**
- ❌ `MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"`
- ❌ Any paths pointing to `/Users/marc/.claude/enhanced_memories/`
- ❌ Any paths pointing to `/Users/marc/agentic-system/`

**Allowed patterns:**
- ✅ `os.getenv("ENHANCED_MEMORY_DB_DIR", "/Volumes/SSDRAID0/agentic-system/databases/enhanced_memory")`
- ✅ `/Volumes/SSDRAID0/agentic-system/`
- ✅ Environment variable driven paths with SSDRAID0 defaults

---

**Migration Status**: COMPLETE ✅
**Last Updated**: 2025-11-20 14:53
**Next Steps**: Monitor for autonomous agent interference
