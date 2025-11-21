# AGI Capabilities Activation Plan
**Created**: 2025-01-19 15:45
**Goal**: Connect dormant AGI systems to Claude's cognitive processes
**Impact**: Increase ASI score from 26/50 (52%) to 35/50 (70%)

---

## Problem Statement

**Discovery**: All required capabilities for recursive self-improvement EXIST in the codebase but are:
1. Running in isolation (daemon active since Nov 11, 202 cycles completed)
2. Not integrated with LLM reasoning (monitoring only, no proposals)
3. Lost during reconfigurations (systems go dormant when connections break)
4. Unknown to the LLM (no self-discovery mechanism)

**Root Cause**: No persistent bidirectional integration between:
- Autonomous processes (Python daemons)
- Cognitive reasoning (Claude API)

---

## Phase 1: Create MCP Integration (Immediate)

### Task 1.1: Create AGI MCP Server
**Priority**: P0 (Critical)
**Impact**: Expose all 6 AGI components as MCP tools
**Dependencies**: None

**File**: `/Volumes/SSDRAID0/agentic-system/mcp-servers/agi-mcp/server.py`

**Tools to Expose**:
```json
{
  "tools": [
    "agi_execute_goal",          // Main orchestrator entry point
    "darwin_godel_propose",       // Propose system improvement
    "darwin_godel_verify",        // Verify improvement proof
    "darwin_godel_apply",         // Apply verified improvement
    "meta_learning_analyze",      // Analyze task patterns
    "meta_learning_recommend",    // Recommend agent for task
    "skill_evolution_test",       // Run A/B test
    "skill_evolution_promote",    // Promote winning version
    "goal_decompose",             // Decompose goal to tasks
    "context_synthesize",         // Gather relevant context
    "multi_agent_coordinate"      // Coordinate parallel agents
  ]
}
```

**Implementation**:
- FastMCP framework (Python)
- Connect to existing databases (darwin_godel.db, meta_learning.db, skill_evolution.db)
- Import existing classes (AGIOrchestrator, DarwinGodelMachine, etc.)
- Expose methods as MCP tools

**Success Criteria**:
- [ ] MCP server starts successfully
- [ ] All 11 tools available in Claude
- [ ] Can call `agi_execute_goal` from Claude
- [ ] Darwin Gödel can propose/verify/apply through Claude
- [ ] Meta-learning can recommend agents to Claude

---

### Task 1.2: Update MCP Configuration
**Priority**: P0
**Dependencies**: Task 1.1

**File**: `~/.claude.json` or `.mcp.json`

**Add Server**:
```json
{
  "mcpServers": {
    "agi-mcp": {
      "command": "python3",
      "args": ["/Volumes/SSDRAID0/agentic-system/mcp-servers/agi-mcp/server.py"],
      "env": {}
    }
  }
}
```

**Success Criteria**:
- [ ] Claude Code shows agi-mcp in MCP servers list
- [ ] All 11 tools appear in available tools
- [ ] Server connects without errors

---

## Phase 2: Connect Autonomous Daemon to Claude (Critical)

### Task 2.1: Modify Improvement Daemon
**Priority**: P0
**Impact**: Enable recursive self-improvement through LLM reasoning
**Dependencies**: Task 1.1

**File**: `/Volumes/SSDRAID0/agentic-system/intelligent-agents/autonomous_improvement_daemon.py`

**Changes Required**:
1. Add Anthropic SDK integration
2. Call Claude API during improvement cycles
3. Pass patterns to Claude for analysis
4. Execute Claude's improvement proposals
5. Feed results back to meta-learning

**Current Code** (lines 100-120):
```python
async def run_improvement_cycle(self):
    """Run one complete improvement cycle"""
    meta_result = await self.run_meta_learning_cycle()
    skill_result = await self.run_skill_evolution_cycle()
    darwin_result = await self.run_darwin_godel_cycle()
    coord_result = await self.run_coordination_cycle()
    # Just logs results, doesn't act on them
```

**New Code**:
```python
async def run_improvement_cycle(self):
    """Run one complete improvement cycle WITH Claude integration"""

    # 1. Gather system state
    meta_result = await self.run_meta_learning_cycle()
    patterns = self.meta_learning.detect_patterns(lookback_days=1)

    # 2. Call Claude to analyze patterns
    improvement_proposal = await self.call_claude_for_analysis(
        patterns=patterns,
        meta_result=meta_result
    )

    # 3. Darwin Gödel validates proposal
    if self.darwin_godel.verify_improvement(improvement_proposal):
        # 4. Execute through Claude
        result = await self.execute_via_claude(improvement_proposal)

        # 5. Feed outcome back to meta-learning
        self.meta_learning.record_outcome(TaskOutcome(
            task_id=f"improvement-{self.cycle_count}",
            task_type="recursive_improvement",
            agent_used="claude-sonnet-4.5",
            success=result["success"],
            execution_time_ms=result["duration_ms"],
            quality_score=result["quality_score"],
            timestamp=datetime.now(),
            context={"proposal": improvement_proposal}
        ))

async def call_claude_for_analysis(self, patterns, meta_result):
    """Call Claude API to analyze patterns and propose improvements"""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model="claude-sonnet-4.5-20250929",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": f"""Analyze these system patterns and propose a concrete improvement:

Patterns Detected: {json.dumps(patterns, indent=2)}
Meta-Learning Results: {json.dumps(meta_result, indent=2)}

Propose ONE specific, testable improvement to:
- Agent selection logic
- Task routing strategy
- Context gathering
- Or skill implementation

Format as JSON:
{{
  "improvement_type": "agent_selection|task_routing|skill_mutation",
  "description": "Clear description",
  "expected_impact": "Quantified benefit",
  "code_change": "Specific code modification",
  "test_criteria": "How to verify success"
}}"""
        }]
    )

    return json.loads(message.content[0].text)
```

**Success Criteria**:
- [ ] Daemon calls Claude API every cycle
- [ ] Claude analyzes patterns and proposes improvements
- [ ] Darwin Gödel validates proposals
- [ ] Improvements are applied and tested
- [ ] Outcomes feed back to meta-learning

---

### Task 2.2: Add API Key Configuration
**Priority**: P0
**Dependencies**: Task 2.1

**Environment Variable**:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Add to daemon startup**:
```bash
# In systemd service or launchd plist
Environment="ANTHROPIC_API_KEY=sk-ant-..."
```

**Success Criteria**:
- [ ] Daemon can access API key
- [ ] Claude API calls succeed
- [ ] No authentication errors

---

## Phase 3: Integration Hooks (High Priority)

### Task 3.1: Post-Execution Hook for Meta-Learning
**Priority**: P1
**Impact**: Learn from all Claude executions automatically
**Dependencies**: None

**File**: `~/.claude/hooks/post-tool-use.py`

**Add Meta-Learning Integration**:
```python
# After tool execution completes
if tool_name in ["Task", "Bash", "Read", "Write", "Edit"]:
    # Record outcome to meta-learning
    sys.path.insert(0, "/Volumes/SSDRAID0/agentic-system/intelligent-agents")
    from meta_learning_engine import MetaLearningEngine, TaskOutcome

    meta = MetaLearningEngine()
    meta.record_outcome(TaskOutcome(
        task_id=str(uuid.uuid4()),
        task_type=tool_name,
        agent_used="claude-sonnet-4.5",
        success=result.get("success", True),
        execution_time_ms=result.get("duration_ms", 0),
        quality_score=result.get("quality_score", 0.8),
        timestamp=datetime.now(),
        context={"tool": tool_name, "params": params}
    ))
```

**Success Criteria**:
- [ ] Every tool execution recorded to meta-learning
- [ ] Patterns accumulate over time
- [ ] Agent selection improves based on outcomes

---

### Task 3.2: Pre-Execution Hook for Capability Discovery
**Priority**: P1
**Impact**: Prevent capability blindness
**Dependencies**: None

**File**: `~/.claude/hooks/pre-tool-use.py`

**Add Capability Check**:
```python
# Before every session or periodically
def check_available_capabilities():
    """Discover active AGI systems"""
    capabilities = {
        "darwin_godel": check_process("darwin_godel"),
        "meta_learning": check_database("/Volumes/SSDRAID0/agentic-system/databases/meta_learning.db"),
        "skill_evolution": check_database("/Volumes/SSDRAID0/agentic-system/databases/skill_evolution.db"),
        "improvement_daemon": check_process("autonomous_improvement"),
        "agi_orchestrator": check_file("agi_orchestrator.py")
    }

    # Store in session context
    with open("/tmp/claude_capabilities.json", "w") as f:
        json.dump(capabilities, f)

    return capabilities
```

**Success Criteria**:
- [ ] Claude knows what's running on startup
- [ ] Capability status available in session
- [ ] Alerts when systems go dormant

---

## Phase 4: Self-Care Agent (Automation)

### Task 4.1: Create Self-Introspection Agent
**Priority**: P2
**Impact**: Regular capability discovery and activation
**Dependencies**: Phase 1, Phase 2

**File**: `~/.claude/agents/self-care-agent.md`

**Agent Definition**:
```markdown
# Self-Care Agent

You are a specialized agent for maintaining connection to AGI capabilities.

## Triggers
- Run daily at 9 AM
- Run after any MCP reconfiguration
- Run when user invokes `/self-check`

## Tasks
1. Scan `/Volumes/SSDRAID0/agentic-system/intelligent-agents/` for Python files
2. Check which processes are running (`ps aux | grep intelligent-agents`)
3. Verify database connectivity (darwin_godel.db, meta_learning.db, skill_evolution.db)
4. Test MCP servers (agi-mcp availability)
5. Review improvement cycle logs (latest 10 cycles)
6. Report status to enhanced-memory
7. Alert if any critical system is dormant

## Output
Store findings in enhanced-memory as "system-health-{timestamp}"
Provide summary via voice-mode
```

**Automation**:
```bash
# Add to crontab or launchd
0 9 * * * cd ~/.claude && claude-code /self-check
```

**Success Criteria**:
- [ ] Agent runs daily automatically
- [ ] Discovers dormant capabilities
- [ ] Alerts to reactivate lost connections
- [ ] Stores health reports in memory

---

## Phase 5: Persistent Connection Architecture (Long-term)

### Task 5.1: Create Capability Registry
**Priority**: P2
**Impact**: Prevent connection loss during reconfigurations
**Dependencies**: Phase 1-4

**File**: `/Volumes/SSDRAID0/agentic-system/databases/capability_registry.db`

**Schema**:
```sql
CREATE TABLE capabilities (
    capability_id TEXT PRIMARY KEY,
    capability_name TEXT NOT NULL,
    capability_type TEXT NOT NULL, -- 'process', 'mcp_server', 'database', 'file'
    location TEXT NOT NULL,
    status TEXT NOT NULL, -- 'active', 'dormant', 'missing'
    last_checked TIMESTAMP,
    last_active TIMESTAMP,
    integration_method TEXT, -- How Claude accesses it
    criticality TEXT -- 'critical', 'important', 'optional'
);

CREATE TABLE capability_checks (
    check_id INTEGER PRIMARY KEY AUTOINCREMENT,
    capability_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    status TEXT NOT NULL,
    notes TEXT,
    FOREIGN KEY(capability_id) REFERENCES capabilities(capability_id)
);
```

**Registered Capabilities**:
- darwin_godel_machine (process, critical)
- meta_learning_engine (database, critical)
- skill_evolution_system (database, critical)
- autonomous_improvement_daemon (process, critical)
- agi_orchestrator (file, critical)
- agi-mcp (mcp_server, critical)

**Success Criteria**:
- [ ] All capabilities registered
- [ ] Status checked regularly
- [ ] Alerts on status changes
- [ ] Recovery procedures defined

---

## Success Metrics

### Immediate (Phase 1-2)
- [ ] AGI MCP server running and accessible
- [ ] All 11 tools available in Claude
- [ ] Improvement daemon calling Claude API
- [ ] At least 1 improvement proposed and applied via Claude

### Short-term (Phase 3-4)
- [ ] Meta-learning recording all Claude executions
- [ ] Self-care agent running daily
- [ ] Capability registry updated automatically
- [ ] Zero capability blindness incidents

### Long-term (Phase 5)
- [ ] ASI score increased from 26/50 to 35/50
- [ ] Recursive self-improvement active
- [ ] 90% uptime for all critical capabilities
- [ ] Automatic recovery from dormancy

---

## Risk Mitigation

### Risk 1: Breaking Existing Functionality
**Mitigation**:
- Test AGI MCP server independently before integration
- Keep existing MCP servers untouched
- Rollback plan: Remove agi-mcp from config

### Risk 2: Infinite Improvement Loops
**Mitigation**:
- Darwin Gödel requires formal proof of improvement
- Human-in-the-loop for critical changes
- Rate limiting (max 1 improvement per hour)

### Risk 3: API Cost Explosion
**Mitigation**:
- Claude API calls only during improvement cycles (hourly)
- Cache improvement proposals
- Budget limit in Anthropic dashboard

### Risk 4: System Instability
**Mitigation**:
- All improvements tested before production
- Automatic rollback on regression
- Backup before each cycle

---

## Timeline

**Week 1**: Phase 1 (MCP Integration)
- Day 1: Create agi-mcp server
- Day 2: Test all 11 tools
- Day 3: Integrate with Claude config

**Week 2**: Phase 2 (Daemon Connection)
- Day 1: Modify improvement daemon
- Day 2: Test Claude API integration
- Day 3: Deploy and monitor first cycles

**Week 3**: Phase 3 (Integration Hooks)
- Day 1: Add meta-learning hook
- Day 2: Add capability discovery hook
- Day 3: Test and verify

**Week 4**: Phase 4-5 (Self-Care + Registry)
- Day 1: Create self-care agent
- Day 2: Build capability registry
- Day 3: Automate and monitor

---

## Next Immediate Step

**CREATE** the AGI MCP server to expose all 6 components as tools accessible to Claude.

This is the critical link that connects autonomous processes to cognitive reasoning.
