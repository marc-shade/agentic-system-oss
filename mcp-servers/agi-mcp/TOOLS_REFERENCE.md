# AGI MCP Tools - Quick Reference

All 21 tools for direct AGI system access from Claude Code.

## Meta-Learning Tools (4)

### agi_record_outcome
Record task execution outcomes for learning.

**Parameters:**
- `task_id` (string, required): Unique task identifier
- `task_type` (string, required): Type of task (e.g., "code_generation", "analysis")
- `agent_used` (string, required): Agent that executed the task
- `success` (boolean, required): Whether task succeeded
- `execution_time_ms` (int, required): Execution time in milliseconds
- `quality_score` (float, optional): Quality score 0.0-1.0
- `error_message` (string, optional): Error message if failed
- `context` (dict, optional): Additional context

**Returns:** Confirmation with recorded outcome details

**Example:**
```python
agi_record_outcome(
    task_id="task_001",
    task_type="code_generation",
    agent_used="coder",
    success=True,
    execution_time_ms=1500,
    quality_score=0.9
)
```

---

### agi_recommend_agent
Get agent recommendation based on learned performance.

**Parameters:**
- `task_type` (string, required): Type of task
- `context` (dict, optional): Additional context for recommendation

**Returns:** Recommended agent with confidence score

**Example:**
```python
agi_recommend_agent(task_type="code_generation")
# Returns: {"recommended_agent": "coder", "confidence": 0.85}
```

---

### agi_detect_patterns
Detect patterns in recent task executions.

**Parameters:**
- `lookback_days` (int, optional, default=7): Number of days to analyze

**Returns:** List of detected patterns with insights

**Example:**
```python
agi_detect_patterns(lookback_days=14)
# Returns: {"patterns_detected": 3, "patterns": [...]}
```

---

### agi_get_learning_summary
Get overall meta-learning system statistics.

**Parameters:** None

**Returns:** Learning summary with key metrics

**Example:**
```python
agi_get_learning_summary()
# Returns: {"total_outcomes": 150, "success_rate": 0.87, ...}
```

---

## Multi-Agent Coordination Tools (2)

### agi_execute_task
Execute a task using multi-agent coordination.

**Parameters:**
- `description` (string, required): Natural language task description
- `task_type` (string, optional, default="general"): Task type for agent selection

**Returns:** Execution results with subtask outcomes

**Example:**
```python
agi_execute_task(
    description="Implement user authentication with JWT tokens",
    task_type="code_generation"
)
# Returns: Decomposed subtasks with execution results
```

---

### agi_get_system_status
Get multi-agent system status.

**Parameters:** None

**Returns:** System status including agents, utilization, and health

**Example:**
```python
agi_get_system_status()
# Returns: {"agents": 5, "active_sessions": 2, ...}
```

---

## Skill Evolution Tools (3)

### agi_register_skill
Register a new skill version.

**Parameters:**
- `skill_name` (string, required): Unique skill name
- `code` (string, required): Skill implementation code
- `description` (string, optional): Skill description
- `version` (string, optional): Version string (auto-generated if not provided)

**Returns:** Skill registration details

**Example:**
```python
agi_register_skill(
    skill_name="data_processor",
    code="def process(data): return [x*2 for x in data if x > 0]",
    description="Optimized data processor"
)
# Returns: {"name": "data_processor", "version": "v1", ...}
```

---

### agi_start_ab_test
Start A/B test between two skill versions.

**Parameters:**
- `skill_name` (string, required): Skill to test
- `version_a` (string, required): First version
- `version_b` (string, required): Second version
- `split_ratio` (float, optional, default=0.5): Traffic split ratio (0.0-1.0)

**Returns:** Test ID and configuration

**Example:**
```python
agi_start_ab_test(
    skill_name="data_processor",
    version_a="v1",
    version_b="v2",
    split_ratio=0.5
)
# Returns: {"test_id": "abc-123", ...}
```

---

### agi_promote_skill
Promote a skill version to production.

**Parameters:**
- `skill_name` (string, required): Skill name
- `version` (string, required): Version to promote

**Returns:** Promotion confirmation

**Example:**
```python
agi_promote_skill(
    skill_name="data_processor",
    version="v2"
)
# Returns: {"status": "success", "promoted_version": "v2"}
```

---

## Goal Decomposition Tools (2)

### agi_execute_goal
Parse and execute a natural language goal.

**Parameters:**
- `goal_description` (string, required): Natural language goal
- `context` (dict, optional): Additional context (language, framework, constraints)

**Returns:** Goal execution plan with decomposed tasks

**Example:**
```python
agi_execute_goal(
    goal_description="Build a REST API for user management",
    context={"language": "Python", "framework": "FastAPI"}
)
# Returns: Hierarchical task breakdown with estimates
```

---

### agi_get_goal_progress
Get progress on a decomposed goal.

**Parameters:**
- `goal_id` (string, required): Goal identifier

**Returns:** Goal progress with completed/pending tasks

**Example:**
```python
agi_get_goal_progress(goal_id="goal_123")
# Returns: {"completed": 3, "pending": 2, "progress": 0.6}
```

---

## Context Synthesis Tools (1)

### agi_synthesize_context
Synthesize optimal context from multiple sources.

**Parameters:**
- `query` (string, required): Context query
- `source_types` (list[string], optional): Source types to include (file, memory, code, api, sensor)
- `target_tokens` (int, optional): Target token count for compression

**Returns:** Synthesized context with compression stats

**Example:**
```python
agi_synthesize_context(
    query="multi-agent coordination implementation",
    source_types=["file", "memory", "code"],
    target_tokens=10000
)
# Returns: Compressed context with relevance scores
```

---

## Darwin Gödel Machine Tools (3)

### agi_propose_modification
Propose a self-modification with formal proof.

**Parameters:**
- `code_before` (string, required): Original code
- `code_after` (string, required): Modified code
- `modification_type` (string, required): Type: "algorithm_improve", "data_structure", "interface", "optimization"
- `description` (string, required): Modification description

**Returns:** Modification proposal with proof status

**Example:**
```python
agi_propose_modification(
    code_before="def old_algo(): ...",
    code_after="def new_algo(): ...",
    modification_type="algorithm_improve",
    description="Optimize from O(n²) to O(n)"
)
# Returns: {"modification_id": "abc-123", "proof_status": "verified"}
```

---

### agi_apply_modification
Apply a verified modification.

**Parameters:**
- `modification_id` (string, required): Modification to apply

**Returns:** Application result with safety checks

**Example:**
```python
agi_apply_modification(modification_id="abc-123")
# Returns: Application status (auto-rollback if safety violated)
```

---

### agi_get_improvement_history
Get history of self-improvements.

**Parameters:** None

**Returns:** Recent modifications with performance impact

**Example:**
```python
agi_get_improvement_history()
# Returns: List of modifications with status and metrics
```

---

## Common Patterns

### Pattern 1: Learn from Execution
```python
# Execute task
result = agi_execute_task(description="Generate API endpoint")

# Record outcome
agi_record_outcome(
    task_id="task_001",
    task_type="code_generation",
    agent_used="coder",
    success=True,
    execution_time_ms=result.execution_time,
    quality_score=0.9
)

# Get recommendation for next similar task
recommendation = agi_recommend_agent(task_type="code_generation")
```

### Pattern 2: Skill Evolution Cycle
```python
# Register new skill version
skill_v2 = agi_register_skill(
    skill_name="processor",
    code=new_implementation,
    description="Optimized version"
)

# Start A/B test
test = agi_start_ab_test(
    skill_name="processor",
    version_a="v1",
    version_b="v2"
)

# After testing period, promote winner
agi_promote_skill(skill_name="processor", version="v2")
```

### Pattern 3: Goal-Driven Development
```python
# Decompose high-level goal
goal = agi_execute_goal(
    goal_description="Build user authentication system",
    context={"language": "Python", "framework": "FastAPI"}
)

# Track progress
progress = agi_get_goal_progress(goal_id=goal.goal_id)

# Execute each subtask
for task in goal.tasks:
    agi_execute_task(description=task.description)
```

### Pattern 4: Context-Aware Execution
```python
# Gather relevant context
context = agi_synthesize_context(
    query="authentication implementation patterns",
    source_types=["file", "memory", "code"],
    target_tokens=10000
)

# Execute with context
result = agi_execute_task(
    description="Implement JWT authentication",
    task_type="code_generation"
)
```

### Pattern 5: Safe Self-Improvement
```python
# Propose improvement
modification = agi_propose_modification(
    code_before=current_implementation,
    code_after=improved_implementation,
    modification_type="optimization",
    description="Reduce memory usage by 40%"
)

# If proof verified, apply
if modification.proof_status == "verified":
    agi_apply_modification(modification_id=modification.modification_id)

# Review history
history = agi_get_improvement_history()
```

---

## Tool Categories by Use Case

### For Autonomous Learning
- `agi_record_outcome` - Capture what happens
- `agi_recommend_agent` - Learn from history
- `agi_detect_patterns` - Find insights
- `agi_get_learning_summary` - Track progress

### For Task Execution
- `agi_execute_task` - Run complex tasks
- `agi_get_system_status` - Monitor health
- `agi_synthesize_context` - Gather information
- `agi_execute_goal` - Goal-driven work

### For Continuous Improvement
- `agi_register_skill` - Track implementations
- `agi_start_ab_test` - Test alternatives
- `agi_promote_skill` - Deploy winners
- `agi_propose_modification` - Improve safely
- `agi_get_improvement_history` - Learn from changes

---

## Integration with Other MCP Servers

### With Enhanced Memory MCP
```python
# Synthesize context from memory
context = agi_synthesize_context(
    query="previous authentication implementations",
    source_types=["memory"]
)

# Execute with learned context
result = agi_execute_task(description="Implement auth")

# Store new learning
# (Enhanced Memory MCP call would go here)
```

### With Agent Runtime MCP
```python
# Create persistent goal
goal = agi_execute_goal(description="Build complete API")

# Track as persistent task in Agent Runtime
# (Agent Runtime MCP call would go here)

# Check progress
progress = agi_get_goal_progress(goal_id=goal.goal_id)
```

---

**All tools are available after Claude Code restart.**
