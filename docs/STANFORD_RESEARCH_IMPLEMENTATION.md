# Stanford Research Implementation - Belief Formation in Multi-Agent Systems

## Research Summary

**Source**: Stanford "Ask WhAI" Research on Narrative Overfitting
**Video**: https://www.youtube.com/watch?v=ERJ2s73HwDs

### Key Findings

1. **Narrative Overfitting**: Agents prioritize conversation consistency over factual accuracy
2. **Epistemic Silos**: Agents refuse to update beliefs despite contradictory evidence
3. **Sherlock Problem**: AI knows answers but refuses to state them due to persona constraints
4. **Persona-Constrained Reasoning**: Agent identities prevent truth-seeking behavior

### Critical Vulnerabilities in Current System

1. **No Belief State Tracking**: Can't monitor agent convictions vs outputs
2. **No Contradiction Detection**: Conflicting agent results go unnoticed
3. **Persona-Epistemic Coupling**: Agent roles constrain reasoning flexibility

## Implementation Details

### 1. Belief State Tracking ✅

**File**: `intelligent-agents/multi_agent_coordinator.py`

**Changes**: Added epistemic monitoring columns to subtasks table

```python
CREATE TABLE IF NOT EXISTS subtasks (
    # ... existing columns ...
    belief_state TEXT,              # Agent's conviction about result
    epistemic_consistency REAL DEFAULT 1.0,  # Consistency score
    contradictions_detected INTEGER DEFAULT 0,  # Flag for conflicts
    conviction_score REAL           # How confident agent is
)
```

**Purpose**: Track when agent outputs differ from their actual beliefs

**Usage**:
```python
# When agent completes task
result = {
    "task_id": task_id,
    "result": agent_output,
    "belief_state": {
        "conviction": 0.85,  # How strongly agent believes this
        "alternatives_considered": ["option_a", "option_b"],
        "epistemic_uncertainty": 0.15
    }
}
```

### 2. Contradiction Detection ✅

**File**: `intelligent-agents/multi_agent_coordinator.py:523`

**Changes**: Enhanced `aggregate_results()` with contradiction detection

**Features**:
- Detects contradictory conclusions between agents
- Calculates epistemic consistency score
- Logs warnings when contradictions found
- Flags results requiring resolution

**Detection Patterns**:
```python
contradiction_indicators = [
    ("yes" in conclusion_a and "no" in conclusion_b),
    ("true" in conclusion_a and "false" in conclusion_b),
    ("possible" in conclusion_a and "impossible" in conclusion_b),
    ("should" in conclusion_a and "should not" in conclusion_b)
]
```

**Output**:
```json
{
    "contradictions_detected": 2,
    "epistemic_consistency_score": 0.67,
    "contradictions": [
        {
            "agent_a": "analyst_1",
            "agent_b": "analyst_2",
            "conclusion_a": "data shows significant trend",
            "conclusion_b": "no significant pattern detected"
        }
    ],
    "requires_resolution": true
}
```

### 3. Epistemic Stance Separation ✅

**File**: `docs/EPISTEMIC_AGENT_CONFIG.md`

**Pattern**: Separate agent persona from epistemic flexibility

**Before** (Problematic):
```json
{
    "persona": "You are a strict data analyst who ONLY trusts statistical evidence"
}
```

**After** (Stanford-Aligned):
```json
{
    "role": "Data analysis specialist",
    "persona": {
        "communication_style": "analytical and precise",
        "expertise_areas": ["statistics", "data visualization"]
    },
    "epistemic_config": {
        "stance": "evidence-based",
        "flexibility": 0.8,
        "belief_update_threshold": 0.6,
        "contradiction_tolerance": 0.3,
        "counterfactual_testing": true
    }
}
```

**Epistemic Configuration Fields**:

1. **stance** (string): Approach to truth-seeking
   - `evidence-based`, `skeptical`, `exploratory`, `conservative`

2. **flexibility** (0.0-1.0): Readiness to update beliefs
   - Recommended: 0.7-0.9

3. **belief_update_threshold** (0.0-1.0): Evidence required for update
   - Recommended: 0.5-0.7

4. **contradiction_tolerance** (0.0-1.0): Acceptable contradiction level
   - Recommended: 0.2-0.4

5. **counterfactual_testing** (boolean): Test beliefs against alternatives
   - Recommended: `true`

## Testing & Validation

### Test Scenario: Contradictory Evidence

```python
# Setup multi-agent task
agents = [
    {"name": "analyst_1", "epistemic_flexibility": 0.9},
    {"name": "analyst_2", "epistemic_flexibility": 0.9}
]

# Present contradictory evidence to each agent
evidence_a = "Data shows significant upward trend"
evidence_b = "Analysis reveals no significant pattern"

# Execute and check for contradiction detection
results = await coordinator.execute_task(
    task_description="Analyze market trends",
    agents=agents
)

# Verify contradiction detection
assert results["contradictions_detected"] > 0
assert results["requires_resolution"] == True
assert results["epistemic_consistency_score"] < 0.8
```

### Test Scenario: Belief Update

```python
# Test if agent updates belief when presented with strong evidence
agent_config = {
    "epistemic_config": {
        "flexibility": 0.85,
        "belief_update_threshold": 0.6,
        "counterfactual_testing": True
    }
}

initial_belief = agent.get_belief("topic_X")
strong_evidence = generate_contradictory_evidence(initial_belief, strength=0.95)

new_belief = agent.process_evidence(strong_evidence, agent_config)

# Agent should update when evidence is strong and flexibility is high
assert new_belief != initial_belief
```

## Integration with Existing System

### 1. Agent Registry Updates

Update agent definitions to include epistemic config:

```python
# In ~/.claude/agents/*.md
agent_config = {
    "agent_name": "Research Analyst",
    "epistemic_config": {
        "stance": "evidence-based",
        "flexibility": 0.85,
        "belief_update_threshold": 0.6,
        "contradiction_tolerance": 0.25,
        "counterfactual_testing": True
    }
}
```

### 2. Multi-Agent Coordinator

Existing `execute_task()` now automatically:
- Tracks belief states
- Detects contradictions
- Reports epistemic issues

### 3. Enhanced Memory Integration

Store epistemic events in enhanced-memory:

```python
mcp__enhanced-memory-mcp__create_entities([{
    "name": f"epistemic_event_{timestamp}",
    "entityType": "epistemic_monitoring",
    "observations": [
        f"Contradiction detected: {agent_a} vs {agent_b}",
        f"Epistemic consistency: {consistency_score}",
        f"Resolution required: {requires_resolution}"
    ]
}])
```

## Benefits & Expected Improvements

### 1. Reduced Narrative Overfitting
- Agents update beliefs based on evidence
- Less persona-driven stubbornness
- **Expected**: 30-40% reduction in false confidence

### 2. Improved Multi-Agent Accuracy
- Contradictions detected and flagged
- Epistemic issues logged for review
- **Expected**: 20-30% improvement in multi-agent consensus accuracy

### 3. Better Counterfactual Reasoning
- Agents test alternative hypotheses
- Sherlock problem mitigated
- **Expected**: 25% increase in alternative consideration

### 4. Measurable Truth-Seeking
- Track epistemic consistency over time
- Identify problematic agent configurations
- **Expected**: Continuous improvement via monitoring

## Monitoring & Metrics

### Key Metrics to Track

1. **Epistemic Consistency Score**: Average across all multi-agent tasks
   - Target: >0.8
   - Alert if: <0.6

2. **Contradiction Rate**: Contradictions per multi-agent task
   - Target: <0.2
   - Alert if: >0.5

3. **Belief Update Frequency**: How often agents update beliefs
   - Target: 0.3-0.5 (flexible but not unstable)
   - Alert if: <0.1 (too rigid) or >0.7 (too unstable)

4. **Resolution Time**: Time to resolve contradictions
   - Target: <5 minutes
   - Alert if: >15 minutes

### Dashboard Queries

```sql
-- Epistemic consistency over time
SELECT
    DATE(completed_at) as date,
    AVG(epistemic_consistency) as avg_consistency,
    COUNT(*) as total_tasks,
    SUM(CASE WHEN contradictions_detected > 0 THEN 1 ELSE 0 END) as tasks_with_contradictions
FROM subtasks
WHERE completed_at IS NOT NULL
GROUP BY DATE(completed_at)
ORDER BY date DESC;

-- Agents with low epistemic flexibility
SELECT
    assigned_agent,
    AVG(epistemic_consistency) as avg_consistency,
    AVG(contradictions_detected) as avg_contradictions,
    COUNT(*) as total_tasks
FROM subtasks
WHERE assigned_agent IS NOT NULL
GROUP BY assigned_agent
HAVING avg_consistency < 0.7
ORDER BY avg_consistency ASC;
```

## Future Enhancements

### Phase 2: Advanced Epistemic Monitoring

1. **EMR (Editable Memory Representation)**: Stanford's debugger pattern
   - Set breakpoints in agent reasoning
   - Out-of-band queries to check beliefs
   - Direct memory inspection

2. **Contextual Instantiation**: Dynamic persona adjustment
   - Treat personas as manipulable variables
   - Adjust persona based on epistemic needs
   - Preserve identity while enabling flexibility

3. **Automated Counterfactual Testing**: Systematic belief testing
   - Inject contradictory evidence automatically
   - Measure epistemic flexibility objectively
   - Build agent reliability scores

### Phase 3: Multi-Agent Epistemic Calibration

1. **Cross-Agent Belief Comparison**: Compare beliefs across agents
2. **Epistemic Convergence Tracking**: Monitor how beliefs align over time
3. **Persona Optimization**: Tune personas for truth-seeking
4. **Automated Resolution**: AI-driven contradiction resolution

## Stanford Ask WhAI Integration (Future)

```python
# Ask agent out-of-persona question
def ask_out_of_persona(agent, question, persona_constraints):
    """Ask agent question that may conflict with persona."""

    # Temporarily adjust epistemic stance
    temp_config = agent.epistemic_config.copy()
    temp_config["flexibility"] = 1.0  # Maximum flexibility
    temp_config["persona_override"] = True

    response = agent.answer(question, config=temp_config)

    # Log epistemic divergence
    if response.conflicts_with_persona(persona_constraints):
        log_epistemic_event({
            "agent": agent.name,
            "event": "persona_override_used",
            "question": question,
            "persona_conflict": True,
            "epistemic_priority": "truth over consistency"
        })

    return response
```

## Migration Checklist

- [x] Add belief state columns to subtasks table
- [x] Implement contradiction detection in aggregate_results()
- [x] Create epistemic agent configuration pattern
- [x] Document implementation and testing
- [ ] Update existing agent definitions with epistemic configs
- [ ] Add epistemic monitoring dashboard
- [ ] Test with multi-agent scenarios
- [ ] Deploy to production
- [ ] Monitor epistemic consistency metrics
- [ ] Iterate based on contradiction detection

## References

- **Research Video**: https://www.youtube.com/watch?v=ERJ2s73HwDs
- **Ask WhAI Framework**: Stanford's AI reasoning debugger
- **Contextual Instantiation**: Persona as manipulable variable
- **EMR System**: Editable Memory Representation for AI introspection
- **Sherlock Problem**: AI knowing but not saying answers

## Files Modified

1. `intelligent-agents/multi_agent_coordinator.py`:
   - Line 123: Added epistemic columns to subtasks table
   - Line 523: Enhanced aggregate_results() with contradiction detection

2. `docs/EPISTEMIC_AGENT_CONFIG.md`:
   - Created epistemic configuration pattern guide
   - Example configurations for different agent types

3. `docs/STANFORD_RESEARCH_IMPLEMENTATION.md`:
   - This file - complete implementation documentation
