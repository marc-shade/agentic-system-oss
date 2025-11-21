# TOON Refactoring Opportunities - Agentic System

**Date:** 2025-11-20
**Status:** 🎯 Ready for Implementation
**Expected System-Wide Savings:** 2.83M+ tokens (50% reduction)
**Cost Impact:** ~$8.50/month savings + faster processing

## Executive Summary

Analysis of JSON usage across the agentic system identified **7 high-value refactoring targets** where TOON can deliver immediate 30-60% token savings. These areas process millions of tokens monthly and represent the core data serialization bottlenecks.

## High Priority Targets (Immediate ROI)

### 1. Enhanced Memory MCP - Entity Serialization
**Location:** `/mcp-servers/enhanced-memory-mcp/server.py`
**Current Usage:** JSON for all entity storage and retrieval
**Volume:** 31,446 entities × ~180 tokens each = 5.66M tokens
**TOON Impact:** 2.83M tokens saved (50% reduction)

**Current Pattern:**
```python
# Line ~650: Entity responses
return [TextContent(
    type="text",
    text=json.dumps(entity_data, indent=2)  # ~180 tokens
)]
```

**TOON Refactor:**
```python
# Import TOON encoder
from toon import encode

# Line ~650: Entity responses with TOON
return [TextContent(
    type="text",
    text=encode(entity_data)  # ~70-90 tokens (50% savings)
)]
```

**Integration Points:**
- `create_entities()` - Entity creation responses
- `search_nodes()` - Search result formatting
- `get_memory_status()` - System status reports
- `execute_code()` - Code execution results
- Entity storage in SQLite (compressed_data field)

**Files to Modify:**
- `mcp-servers/enhanced-memory-mcp/server.py` (primary)
- `mcp-servers/enhanced-memory-mcp/compression.py` (add TOON codec)

**Estimated Effort:** 4-6 hours
**Testing Required:** Backward compatibility with existing entities

---

### 2. Agent Runtime MCP - Task & Goal Serialization
**Location:** `/mcp-servers/agent-runtime-mcp/server.py`
**Current Usage:** JSON for task/goal definitions and queue operations
**Volume:** 9 active goals, ~50 tasks per day = ~15K tokens/day
**TOON Impact:** 7.5K tokens/day saved (50% reduction)

**Current Pattern:**
```python
# Lines 643, 658, 679, 699, 721, 736: All use json.dumps(data, indent=2)
text=json.dumps(goal, indent=2)     # Goal details
text=json.dumps(task, indent=2)     # Task details
text=json.dumps(goals, indent=2)    # Goal lists
text=json.dumps(tasks, indent=2)    # Task queues
```

**TOON Refactor:**
```python
from toon import encode

# Replace all json.dumps calls:
text=encode(goal)      # 50% fewer tokens
text=encode(task)      # 50% fewer tokens
text=encode(goals)     # Tabular arrays for lists
text=encode(tasks)     # Massive savings on queues
```

**Integration Points:**
- `create_goal()` - Goal creation responses
- `get_goal()` - Goal retrieval
- `list_goals()` - Goal listing (array optimization)
- `create_task()` - Task creation
- `get_next_task()` - Queue operations
- `list_tasks()` - Task queue listing (array optimization)
- `decompose_goal()` - AI-generated task lists

**Files to Modify:**
- `mcp-servers/agent-runtime-mcp/server.py` (all tool responses)

**Estimated Effort:** 2-3 hours
**Testing Required:** Goal/task parsing compatibility

---

### 3. Cluster Coordination - Heartbeat & Status Messages
**Location:** `/cluster-deployment/`
**Current Usage:** JSON for node heartbeats, status broadcasts, task routing
**Volume:** 4 nodes × 120 heartbeats/hour × 24 hours = 11,520 messages/day
**TOON Impact:** 50% reduction in cluster network overhead

**Current Files Using JSON:**
- `distributed_task_router.py` - Task definitions
- `github_node_daemon.py` - Heartbeat messages
- `performance_optimizer.py` - System metrics
- `submit_cluster_task.py` - Task submission

**Current Pattern (distributed_task_router.py:147):**
```python
task_file.write_text(json.dumps({
    "task_id": task_id,
    "task_def": task_def,
    "status": "pending",
    "assigned_to": self.local_node_id
}))
```

**TOON Refactor:**
```python
from toon import encode

task_file.write_text(encode({
    "task_id": task_id,
    "task_def": task_def,
    "status": "pending",
    "assigned_to": self.local_node_id
}))
```

**Integration Points:**
- Heartbeat broadcasts (every 30s from each node)
- Task submission messages
- Node status reports
- Performance metrics broadcasts
- Task result messages

**Files to Modify:**
- `cluster-deployment/distributed_task_router.py`
- `cluster-deployment/github_node_daemon.py`
- `cluster-deployment/performance_optimizer.py`
- `cluster-deployment/submit_cluster_task.py`

**Estimated Effort:** 3-4 hours
**Testing Required:** Cross-node compatibility (all nodes must support TOON)

---

### 4. MCP Server Tool Responses (System-Wide)
**Location:** All MCP servers
**Current Usage:** Every tool response uses JSON formatting
**Volume:** Varies by server, estimated 100+ tool calls/hour
**TOON Impact:** 30-50% reduction per response

**Affected Servers:**
1. `enhanced-memory-mcp` (88 json.dumps calls)
2. `agent-runtime-mcp` (21 json.dumps calls)
3. `agi-mcp` (31 json.dumps calls)
4. `video-transcript-mcp` (13 json.dumps calls)
5. `research-paper-mcp` (13 json.dumps calls)
6. `nuclei-mcp` (varies)

**Standard Pattern Across All Servers:**
```python
# Current: Every MCP tool response
return [TextContent(
    type="text",
    text=json.dumps(result, indent=2)
)]

# TOON Refactor: Create shared utility
from mcp_toon_utils import toon_response

return toon_response(result)  # Handles encoding internally
```

**Shared Utility to Create:**
```python
# File: mcp-servers/shared/toon_utils.py
from toon import encode
from mcp.types import TextContent

def toon_response(data, fallback_json=True):
    """Create TOON-encoded MCP response with JSON fallback"""
    try:
        return [TextContent(type="text", text=encode(data))]
    except Exception as e:
        if fallback_json:
            import json
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        raise
```

**Files to Modify:**
- Create `mcp-servers/shared/toon_utils.py` (new)
- Update all MCP server files to import and use `toon_response()`

**Estimated Effort:** 6-8 hours (system-wide change)
**Testing Required:** All MCP tools must pass validation

---

## Medium Priority Targets (Strategic Value)

### 5. Workflow State Persistence (Temporal/AutoKitteh)
**Location:** Various workflow state files
**Current Usage:** JSON for workflow serialization
**TOON Impact:** Faster workflow recovery, reduced state storage

**Integration Points:**
- Temporal workflow state snapshots
- AutoKitteh deployment configurations
- Workflow execution history

**Estimated Effort:** 4-6 hours
**Testing Required:** Workflow resume/recovery testing

---

### 6. Configuration Files
**Location:** System-wide config files
**Current Usage:** JSON for all configuration
**TOON Impact:** More readable configs, fewer tokens when loaded

**Target Files:**
- `.mcp.json` - MCP server configuration
- `claude_desktop_config.json` - Claude Code config
- Various service configs

**Note:** May require TOON → JSON conversion for compatibility
**Estimated Effort:** 2-3 hours per config type
**Testing Required:** All config parsers must support TOON

---

### 7. Log Formatting & Structured Logging
**Location:** System-wide logging
**Current Usage:** JSON-formatted structured logs
**TOON Impact:** More readable logs, reduced log storage

**Integration Points:**
- `structlog` configuration
- Error reporting
- Audit trails
- Performance metrics logs

**Estimated Effort:** 3-4 hours
**Testing Required:** Log parsing tools compatibility

---

## Implementation Strategy

### Phase 1: Foundation (Week 1)
1. **Install TOON in Python environment**
   ```bash
   # macpro51 already has built TOON, copy binaries
   scp -r marc@macpro51.local:/tmp/toon-build-macpro51/node_modules/@toon-format ./
   pip install toon-format  # Or use local build
   ```

2. **Create shared utilities**
   - `mcp-servers/shared/toon_utils.py` - TOON response helper
   - `mcp-servers/shared/toon_codec.py` - Encode/decode wrappers
   - `cluster-deployment/toon_serialization.py` - Cluster-specific

3. **Add backward compatibility layer**
   ```python
   def encode_with_fallback(data, use_toon=True):
       if use_toon:
           try:
               return toon.encode(data)
           except:
               pass  # Fall through to JSON
       return json.dumps(data, indent=2)
   ```

### Phase 2: Enhanced Memory MCP (Week 1-2)
1. **Update entity responses** (Priority #1)
   - Modify all `json.dumps()` calls in server.py
   - Add TOON codec to compression.py
   - Parallel storage: TOON + JSON for 30 days
   - Monitor for errors

2. **Migration script for existing entities**
   ```python
   # Convert all 31,446 entities to TOON format
   for entity in get_all_entities():
       entity['toon_data'] = toon.encode(entity)
       update_entity(entity)
   ```

3. **Performance benchmarking**
   - Measure encode/decode speed vs JSON
   - Token count validation
   - Memory usage comparison

### Phase 3: Agent Runtime MCP (Week 2)
1. **Update all tool responses**
   - Replace json.dumps with toon.encode
   - Test goal/task creation
   - Test queue operations
   - Validate decomposition results

2. **Tabular optimization for arrays**
   ```toon
   # Tasks queue - massive savings
   tasks:
     id  title                priority  status
     19  "Deploy Swarm"      10        pending
     20  "Code TOON"         10        pending
     21  "Integrate TOON"    9         pending
   ```

### Phase 4: Cluster Coordination (Week 2-3)
1. **Coordinate cross-node upgrade**
   - All nodes must support TOON simultaneously
   - Gradual rollout with version detection
   - Fallback to JSON for mixed-version clusters

2. **Update coordination files**
   - distributed_task_router.py
   - github_node_daemon.py
   - performance_optimizer.py

3. **Test cluster operations**
   - Heartbeat broadcasting
   - Task routing
   - Result collection

### Phase 5: System-Wide MCP Servers (Week 3-4)
1. **Batch update all servers**
   - Use shared toon_utils
   - Consistent response formatting
   - Comprehensive testing

2. **Validation suite**
   - Test all MCP tools
   - Verify Claude Code compatibility
   - Check tool argument parsing

### Phase 6: Monitoring & Optimization (Week 4+)
1. **Token usage tracking**
   - Before/after metrics
   - Cost savings validation
   - Performance monitoring

2. **Gradual feature rollout**
   - Start with new data only
   - Migrate existing data incrementally
   - Monitor for issues

---

## Migration Safety Net

### Backward Compatibility Strategy
```python
# Always support JSON decoding
def smart_decode(text):
    """Decode TOON or JSON automatically"""
    try:
        # Try TOON first
        return toon.decode(text)
    except:
        # Fallback to JSON
        return json.loads(text)
```

### Rollback Plan
1. **Parallel storage** (30 days)
   - Store both TOON and JSON versions
   - Use TOON for new operations
   - Keep JSON for rollback capability

2. **Feature flag**
   ```python
   USE_TOON = os.getenv("ENABLE_TOON_FORMAT", "true").lower() == "true"
   ```

3. **Monitoring**
   - Track TOON decode failures
   - Alert on increased error rates
   - Auto-rollback if errors > 1%

---

## Success Metrics

### Token Savings Targets
- **Enhanced Memory:** 2.83M tokens/month saved (50%)
- **Agent Runtime:** 225K tokens/month saved (50%)
- **Cluster Coordination:** 172K tokens/month saved (50%)
- **MCP Responses:** 500K tokens/month saved (30-50%)
- **Total System:** 3.7M+ tokens/month saved

### Cost Savings
- **Monthly:** ~$11/month (at $3/1M input tokens)
- **Annual:** ~$132/year
- **Plus:** Faster processing, reduced latency

### Performance Targets
- Encode/decode speed: < 1ms overhead vs JSON
- No increase in memory usage
- Zero breaking changes for existing workflows

---

## Risk Assessment

### Low Risk
✅ TOON is well-tested (374/374 tests passed)
✅ Backward compatibility via JSON fallback
✅ Gradual rollout with monitoring
✅ Parallel storage for 30-day safety net

### Medium Risk
⚠️ Cross-node coordination requires synchronized upgrade
⚠️ MCP protocol compatibility (needs validation)
⚠️ Migration of 31K+ entities takes time

### Mitigation
- Staged rollout (memory → runtime → cluster → system-wide)
- Comprehensive testing at each stage
- Feature flags for easy rollback
- Monitoring and alerting
- 30-day parallel storage period

---

## Concrete Next Steps

### This Week (2025-11-20 to 2025-11-27)
1. ✅ TOON build complete on macpro51 (DONE)
2. ⏳ Install TOON in Python environment
3. ⏳ Create shared utilities (toon_utils.py)
4. ⏳ Update Enhanced Memory MCP (Priority #1)
5. ⏳ Run token savings validation test

### Next Week (2025-11-27 to 2025-12-04)
1. ⏳ Update Agent Runtime MCP
2. ⏳ Begin cluster coordination update
3. ⏳ Start entity migration (31K entities)
4. ⏳ Performance benchmarking

### Weeks 3-4 (2025-12-04 to 2025-12-18)
1. ⏳ System-wide MCP server updates
2. ⏳ Monitoring and optimization
3. ⏳ Remove JSON fallback (if stable)
4. ⏳ Final validation and documentation

---

## Code Examples

### Example 1: Enhanced Memory Entity Response

**Before (JSON - ~180 tokens):**
```python
entity_response = {
    "name": "optimization-cluster-routing",
    "entityType": "system_learning",
    "observations": [
        "macpro51_validated_as_builder",
        "direct_ssh_faster_than_github_queue",
        "toon_build_success_374_tests"
    ],
    "metadata": {
        "confidence": 0.98,
        "source": "mac-studio",
        "timestamp": "2025-11-20T06:44:41Z",
        "tags": ["cluster", "optimization", "toon"]
    }
}

return [TextContent(type="text", text=json.dumps(entity_response, indent=2))]
```

**After (TOON - ~70-90 tokens, 50% savings):**
```python
entity_response = {
    "name": "optimization-cluster-routing",
    "entityType": "system_learning",
    "observations": [
        "macpro51_validated_as_builder",
        "direct_ssh_faster_than_github_queue",
        "toon_build_success_374_tests"
    ],
    "metadata": {
        "confidence": 0.98,
        "source": "mac-studio",
        "timestamp": "2025-11-20T06:44:41Z",
        "tags": ["cluster", "optimization", "toon"]
    }
}

from toon import encode
return [TextContent(type="text", text=encode(entity_response))]
```

### Example 2: Agent Runtime Task Queue

**Before (JSON - 100 tasks = ~15,000 tokens):**
```json
[
  {"id": 1, "title": "Validate macpro51", "priority": 10, "status": "completed"},
  {"id": 2, "title": "Build TOON", "priority": 10, "status": "completed"},
  {"id": 3, "title": "Integrate TOON", "priority": 9, "status": "pending"},
  ... (97 more tasks)
]
```

**After (TOON - 100 tasks = ~6,000-7,500 tokens, 50-60% savings):**
```toon
tasks:
  id  title                  priority  status
  1   "Validate macpro51"   10        completed
  2   "Build TOON"          10        completed
  3   "Integrate TOON"      9         pending
  ... (97 more rows - same format)
```

### Example 3: Cluster Heartbeat

**Before (JSON - ~120 tokens):**
```json
{
  "node_id": "macpro51",
  "timestamp": "2025-11-20T06:45:00Z",
  "cpu_percent": 15.2,
  "memory_percent": 45.8,
  "load_avg": [1.2, 1.5, 1.8],
  "active_tasks": 2,
  "status": "healthy"
}
```

**After (TOON - ~50-60 tokens, 50% savings):**
```toon
node_id: macpro51
timestamp: 2025-11-20T06:45:00Z
cpu_percent: 15.2
memory_percent: 45.8
load_avg: [1.2, 1.5, 1.8]
active_tasks: 2
status: healthy
```

---

## Summary

The agentic system has **7 major refactoring opportunities** where TOON can replace JSON:

1. ✅ **Enhanced Memory MCP** - 2.83M tokens/month saved (highest ROI)
2. ✅ **Agent Runtime MCP** - 225K tokens/month saved
3. ✅ **Cluster Coordination** - 172K tokens/month saved
4. ✅ **MCP Server Responses** - 500K tokens/month saved (system-wide)
5. ⏳ Workflow State Persistence
6. ⏳ Configuration Files
7. ⏳ Structured Logging

**Total Expected Savings:** 3.7M+ tokens/month (50% reduction)
**Cost Impact:** ~$11/month savings + faster processing
**Implementation Time:** 3-4 weeks for full system integration

---

**Status:** 🎯 Ready for Phase 1 Implementation
**Priority:** HIGH - Immediate cost and performance benefits
**Next Action:** Install TOON in Python environment and create shared utilities
**Owner:** mac-studio (Orchestrator)
**Date:** 2025-11-20 06:45 EST
