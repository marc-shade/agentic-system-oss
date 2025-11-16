# Recovery Procedures - Phase 1 Autonomous System

**Purpose**: Ensure the system can always restart and continue from exactly where it left off.
**Applies To**: Graceful restarts, crashes, power failures, system reboots, Claude Code restarts

---

## Quick Recovery Checklist

When restarting after ANY interruption, run these commands in order:

```bash
# 1. Verify system state
cd /Volumes/SSDRAID0/agentic-system
python3 verify_phase1_restart.py

# 2. Review current phase
cat .phase1_state.json | jq '.'

# 3. Check progress
python3 phase1_tracker.py --report

# 4. Verify autonomous loop
ps aux | grep autonomous_recursive_agi_loop.py

# 5. If loop not running, restart it
python3 autonomous_recursive_agi_loop.py &
echo $! > /tmp/autonomous_loop.pid

# 6. Resume monitoring
python3 phase1_monitor.py
```

---

## Persistence Layers

### Layer 1: File System (Primary Persistence)

**Configuration** - Always survives restart:
- `agi_config.json` - System configuration with all 10 production targets
- `.phase1_state.json` - Current phase and progress state
- `databases/phase1_tracking.db` - SQLite database with all progress snapshots

**Documentation** - Strategic context survives:
- `STRATEGIC_ROADMAP_TO_40.md` - 18-24 month strategic plan (18/50 → 40/50)
- `ASI_SELF_ASSESSMENT.md` - Baseline capability assessment (18/50)
- `PHASE1_MONITORING_CHECKLIST.md` - Monitoring procedures
- `PRODUCTION_TARGETS_ROLLOUT.md` - Detailed rollout plan for all targets
- `PHASE1_PREPARATION_COMPLETE.md` - Preparation summary
- `RECOVERY_PROCEDURES.md` - This file

**Scripts** - Operational procedures survive:
- `phase1_monitor.py` - 24-hour practice period monitoring
- `phase1_tracker.py` - Progress tracking with database
- `verify_phase1_restart.py` - Restart verification
- `autonomous_recursive_agi_loop.py` - The autonomous loop itself

**Git History** - All modifications tracked:
- Every improvement committed automatically
- Rollbacks tracked
- Safety incidents logged
- Complete audit trail

### Layer 2: Enhanced Memory (Secondary Persistence)

**Strategic Context** stored in enhanced-memory:
- Phase1-Preparation-Complete (Entity ID: 7524)
- Strategic-Roadmap-18-to-40 (Entity ID: 7487)
- ASI-Self-Assessment-Baseline (Entity ID: 7430)

**Recovery**: Query enhanced-memory to rebuild context:
```python
mcp__enhanced-memory__search_nodes("Phase 1 strategic")
mcp__enhanced-memory__search_nodes("ASI assessment baseline")
mcp__enhanced-memory__search_nodes("rollout plan")
```

### Layer 3: Databases (Progress Tracking)

**phase1_tracking.db** - Complete progress history:
- `progress_snapshots` - All progress recordings
- `milestones` - Achievement tracking
- `target_status` - Per-file status
- `asi_history` - ASI score progression

**coordination.db** - Temporal/AutoKitteh state
**memory.db** - Enhanced memory persistence
**qdrant/` - Vector embeddings

---

## Recovery Scenarios

### Scenario 1: Claude Code Restart (Most Common)

**What Happens**:
- Claude Code process restarts
- MCP servers reload
- Conversation context lost

**What Persists**:
- ✅ All files on disk
- ✅ Enhanced memory entities
- ✅ Databases
- ✅ Git history
- ✅ Autonomous loop (still running independently)

**Recovery Steps**:
1. MCP servers automatically reconnect
2. Read `.phase1_state.json` to see current phase
3. Query enhanced-memory for strategic context
4. Run `python3 phase1_tracker.py --report` to see progress
5. Continue monitoring with `python3 phase1_monitor.py`

**Time to Resume**: < 1 minute

### Scenario 2: Autonomous Loop Crash

**What Happens**:
- autonomous_recursive_agi_loop.py process dies
- No new improvements generated
- Monitoring can still run

**What Persists**:
- ✅ All configuration
- ✅ All progress data
- ✅ Last successful state in git
- ✅ Tracking database intact

**Recovery Steps**:
```bash
# 1. Check if really crashed
ps aux | grep autonomous_recursive_agi_loop.py

# 2. Review last log entries
tail -100 logs/autonomous_loop.log

# 3. Check for errors
grep -i error logs/autonomous_loop.log | tail -20

# 4. Verify git state is clean
git status

# 5. Restart loop
python3 autonomous_recursive_agi_loop.py &
echo $! > /tmp/autonomous_loop.pid

# 6. Verify restarted successfully
ps aux | grep autonomous_recursive_agi_loop.py

# 7. Monitor next cycle
tail -f logs/autonomous_loop.log
```

**Time to Resume**: 2-5 minutes

### Scenario 3: System Reboot (Power Failure)

**What Happens**:
- All processes terminate
- System restarts from scratch
- Need to restart all services

**What Persists**:
- ✅ All files on disk (SSDRAID0)
- ✅ All databases
- ✅ Git repository
- ✅ Configuration

**Recovery Steps**:
```bash
# 1. Navigate to system directory
cd /Volumes/SSDRAID0/agentic-system

# 2. Run full verification
python3 verify_phase1_restart.py

# 3. Start Temporal (if needed)
cd scripts && ./start-temporal.sh && cd ..

# 4. Start Qdrant (if needed)
cd scripts && ./start-qdrant.sh && cd ..

# 5. Verify MCP servers (Claude Code handles this)
# They auto-start when Claude Code starts

# 6. Restart autonomous loop
python3 autonomous_recursive_agi_loop.py &
echo $! > /tmp/autonomous_loop.pid

# 7. Check system state
python3 phase1_tracker.py --report

# 8. Resume monitoring
python3 phase1_monitor.py
```

**Time to Resume**: 5-10 minutes

### Scenario 4: Database Corruption

**What Happens**:
- phase1_tracking.db becomes corrupted
- Progress data potentially lost

**What Persists**:
- ✅ Git history (can reconstruct from commits)
- ✅ Enhanced memory (can query for context)
- ✅ Configuration files
- ✅ Log files

**Recovery Steps**:
```bash
# 1. Backup corrupted database
mv databases/phase1_tracking.db databases/phase1_tracking.db.corrupted

# 2. Recreate database schema
python3 phase1_tracker.py --asi  # This creates DB

# 3. Reconstruct from git history
python3 phase1_tracker.py --record --phase "1A" --notes "Reconstructed after DB corruption"

# 4. Generate fresh report
python3 phase1_tracker.py --report

# 5. Query enhanced-memory for context
# Use Claude Code to query: mcp__enhanced-memory__search_nodes("Phase 1")
```

**Time to Resume**: 10-15 minutes

---

## Critical Files Checklist

Before declaring "recovered", verify these files exist and are readable:

**Configuration**:
- [ ] `agi_config.json` - System configuration
- [ ] `.phase1_state.json` - Current phase state

**Documentation**:
- [ ] `STRATEGIC_ROADMAP_TO_40.md` - Strategic plan
- [ ] `ASI_SELF_ASSESSMENT.md` - Baseline assessment
- [ ] `PHASE1_MONITORING_CHECKLIST.md` - Monitoring procedures
- [ ] `PRODUCTION_TARGETS_ROLLOUT.md` - Rollout plan
- [ ] `PHASE1_PREPARATION_COMPLETE.md` - Preparation summary
- [ ] `RECOVERY_PROCEDURES.md` - This file

**Scripts**:
- [ ] `phase1_monitor.py` - Practice period monitoring
- [ ] `phase1_tracker.py` - Progress tracking
- [ ] `verify_phase1_restart.py` - Verification script
- [ ] `autonomous_recursive_agi_loop.py` - The loop

**Databases**:
- [ ] `databases/phase1_tracking.db` - Progress tracking
- [ ] `databases/coordination.db` - Temporal state
- [ ] `agent-memory/enhanced_memories/memory.db` - Enhanced memory

**Target Files**:
- [ ] `intelligent-agents/sample_module.py` - Practice target
- [ ] All 10 production target files exist

---

## Restart Verification Script

The `verify_phase1_restart.py` script checks all critical components:

```bash
python3 verify_phase1_restart.py
```

**Checks**:
1. ✅ All critical files present
2. ✅ Configuration valid JSON
3. ✅ State file current
4. ✅ Databases accessible
5. ✅ Git repository healthy
6. ✅ Autonomous loop status
7. ✅ Enhanced memory accessible
8. ✅ Progress tracking operational

**Output**:
- Green checkmarks (✅) = All good
- Red X marks (❌) = Needs attention
- Summary of current phase and progress

---

## Context Recovery Commands

When Claude Code restarts, use these to rebuild full context:

### 1. Check Current Phase
```bash
cat .phase1_state.json | jq '.current_phase, .status, .target_file'
```

### 2. Get Progress Summary
```bash
python3 phase1_tracker.py --report
```

### 3. Query Enhanced Memory
```python
# In Claude Code:
mcp__enhanced-memory__search_nodes("Phase 1 strategic", limit=10)
mcp__enhanced-memory__search_nodes("ASI baseline", limit=5)
mcp__enhanced-memory__search_nodes("rollout plan", limit=5)
```

### 4. Review Recent Activity
```bash
# Recent git commits
git log --oneline --since="24 hours ago"

# Recent improvements to target
git log --oneline -- intelligent-agents/sample_module.py

# Check autonomous loop logs
tail -100 logs/autonomous_loop.log
```

### 5. Verify Monitoring State
```bash
# Run practice period monitor
python3 phase1_monitor.py

# Check for any safety incidents
git log --grep=SAFETY --grep=EMERGENCY -i --since="7 days ago"
```

---

## Autonomous Loop Recovery

The autonomous loop is designed to be resilient:

### Normal Operation
```bash
# Check if running
ps aux | grep autonomous_recursive_agi_loop.py

# View live logs
tail -f logs/autonomous_loop.log

# Check cycle status
grep "Starting cycle" logs/autonomous_loop.log | tail -5
```

### If Loop Stopped
```bash
# Restart loop
python3 autonomous_recursive_agi_loop.py &

# Verify started
ps aux | grep autonomous_recursive_agi_loop.py

# Watch for first cycle
tail -f logs/autonomous_loop.log
```

### Loop Recovery Guarantees
- ✅ Configuration loads from `agi_config.json`
- ✅ Knowledge sources reconnect (research papers, video transcripts)
- ✅ Git integration automatic
- ✅ Sandbox testing available
- ✅ Safety systems active
- ✅ Picks up from last committed state

---

## Enhanced Memory Recovery

Enhanced memory persists across all restarts:

### Verify Memory Accessible
```python
mcp__enhanced-memory__get_memory_status()
```

### Recover Strategic Context
```python
# Get Phase 1 preparation context
prep = mcp__enhanced-memory__search_nodes("Phase1-Preparation-Complete")

# Get strategic roadmap
roadmap = mcp__enhanced-memory__search_nodes("Strategic-Roadmap-18-to-40")

# Get ASI baseline
baseline = mcp__enhanced-memory__search_nodes("ASI-Self-Assessment-Baseline")
```

### Store New Recovery Event
```python
mcp__enhanced-memory__create_entities([{
    "name": f"Recovery-Event-{timestamp}",
    "entityType": "system_event",
    "observations": [
        "System recovered from restart",
        "Context rebuilt successfully",
        "Continuing Phase 1A",
        "All persistence layers verified"
    ]
}])
```

---

## Monitoring Continuity

After restart, monitoring continues seamlessly:

### Resume Hourly Monitoring
```bash
# Run immediately after restart
python3 phase1_monitor.py

# Set up cron job (if desired)
# Add to crontab: 0 * * * * cd /Volumes/SSDRAID0/agentic-system && python3 phase1_monitor.py
```

### Resume Progress Tracking
```bash
# Record restart event
python3 phase1_tracker.py --record --phase "1A" --notes "System restarted - resumed monitoring"

# Check current status
python3 phase1_tracker.py --report
```

### Verify No Data Loss
```bash
# Check tracking database
sqlite3 databases/phase1_tracking.db "SELECT COUNT(*) FROM progress_snapshots;"

# Check git history intact
git log --oneline | wc -l

# Verify configuration unchanged
cat agi_config.json | jq '.target_files.production_targets | length'
# Should be: 10
```

---

## Emergency Contacts

If recovery fails or data is corrupted:

1. **Check Git History**: `git reflog` - Can recover from almost anything
2. **Check Backups**: `/Volumes/FILES/agentic-system/` - Cold storage backup
3. **Enhanced Memory**: Query for critical context even if files lost
4. **Logs**: `logs/` directory contains diagnostic information

---

## Testing Recovery

To test recovery procedures without risk:

```bash
# 1. Create test state snapshot
python3 phase1_tracker.py --export

# 2. Record current git commit
git rev-parse HEAD > /tmp/current_commit.txt

# 3. Simulate restart
pkill -f autonomous_recursive_agi_loop.py

# 4. Run verification
python3 verify_phase1_restart.py

# 5. Check reports still work
python3 phase1_tracker.py --report

# 6. Restart loop
python3 autonomous_recursive_agi_loop.py &

# 7. Verify recovery complete
python3 verify_phase1_restart.py
```

---

## Recovery Success Criteria

Consider recovery successful when:

- ✅ All critical files readable
- ✅ Configuration intact (agi_config.json valid)
- ✅ State file current (.phase1_state.json)
- ✅ Databases accessible (phase1_tracking.db, memory.db)
- ✅ Git repository healthy
- ✅ Autonomous loop running (or restartable)
- ✅ MCP servers connected
- ✅ Enhanced memory accessible
- ✅ Progress reports generate
- ✅ Can continue from exact same phase
- ✅ No data loss detected

---

## Post-Recovery Actions

After successful recovery:

1. **Record Recovery Event**:
```bash
python3 phase1_tracker.py --record --notes "Recovered from [restart type]"
```

2. **Store in Enhanced Memory**:
```python
mcp__enhanced-memory__create_entities([{
    "name": f"Recovery-{timestamp}",
    "entityType": "system_event",
    "observations": ["recovery_type", "time_to_recover", "data_integrity_verified"]
}])
```

3. **Resume Normal Operations**:
- Continue hourly monitoring
- Watch for next autonomous cycle
- Verify improvements still applying

4. **Update Recovery Log**:
```bash
echo "$(date): Recovered from [type] - $(python3 phase1_tracker.py --report | head -20)" >> logs/recovery_log.txt
```

---

## Persistence Guarantees

**What ALWAYS Survives** (100% guaranteed):
- Configuration files (agi_config.json, .phase1_state.json)
- All markdown documentation
- All Python scripts
- Git repository and history
- SQLite databases (if not corrupted)
- Enhanced memory entities
- Logs directory

**What MIGHT Be Lost** (requires recreation):
- Running process state (PID, memory)
- Claude Code conversation context
- In-flight improvements (not yet committed)
- Uncommitted git changes
- Terminal output

**Recovery Time**:
- Best case: < 1 minute (Claude Code restart)
- Normal case: 2-5 minutes (loop crash)
- Worst case: 10-15 minutes (full system reboot)

---

## Summary

**The system is designed for resilience**:

1. **Multiple Persistence Layers** - Files, databases, enhanced memory, git
2. **State Tracking** - `.phase1_state.json` tracks current phase
3. **Progress Tracking** - `phase1_tracking.db` records all history
4. **Documentation** - All procedures documented on disk
5. **Verification** - `verify_phase1_restart.py` checks everything
6. **Recovery Procedures** - This file guides recovery
7. **Context Recovery** - Enhanced memory stores strategic context

**Result**: Can ALWAYS recover and continue from exactly where we left off.

---

**Last Updated**: 2025-11-10
**Version**: 1.0
**Status**: ACTIVE
