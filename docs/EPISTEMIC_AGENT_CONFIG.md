# Epistemic Agent Configuration Pattern

## Stanford Research Finding

**Problem**: Agent personas constrain truth-seeking behavior
- Agents refuse to update beliefs when it conflicts with their persona
- Example: "Data analyst" agent refuses to consider non-statistical evidence
- Result: Narrative overfitting and epistemic silos

**Solution**: Separate epistemic stance from agent persona

## Configuration Pattern

### Old Pattern (Problematic)
```json
{
  "agent_name": "data_analyst",
  "persona": "You are a strict data analyst who ONLY trusts statistical evidence",
  "task_types": ["analysis"]
}
```

**Issue**: Persona prevents agent from considering valid non-statistical evidence

### New Pattern (Stanford-Aligned)
```json
{
  "agent_name": "data_analyst",
  "role": "Data analysis specialist",
  "persona": {
    "communication_style": "analytical and precise",
    "expertise_areas": ["statistics", "data visualization", "quantitative analysis"],
    "preferred_methods": ["statistical tests", "data modeling"]
  },
  "epistemic_config": {
    "stance": "evidence-based",
    "flexibility": 0.8,
    "belief_update_threshold": 0.6,
    "contradiction_tolerance": 0.3,
    "counterfactual_testing": true
  },
  "task_types": ["analysis"]
}
```

## Epistemic Configuration Fields

### `stance` (string)
How the agent approaches truth-seeking:
- `"evidence-based"`: Updates beliefs based on evidence quality
- `"skeptical"`: Requires strong evidence for belief updates
- `"exploratory"`: Readily considers alternative hypotheses
- `"conservative"`: Maintains existing beliefs unless contradicted

### `flexibility` (float 0.0-1.0)
How readily the agent updates beliefs:
- `0.0`: Never updates beliefs (dogmatic)
- `0.5`: Moderate flexibility
- `1.0`: Highly flexible (updates readily)

**Recommended**: 0.7-0.9 for most agents

### `belief_update_threshold` (float 0.0-1.0)
Minimum evidence strength required for belief update:
- `0.3`: Low bar (updates easily)
- `0.6`: Moderate bar
- `0.9`: High bar (requires very strong evidence)

**Recommended**: 0.5-0.7 for balanced truth-seeking

### `contradiction_tolerance` (float 0.0-1.0)
How much contradiction the agent accepts before flagging:
- `0.0`: Flag any contradiction immediately
- `0.3`: Tolerate minor contradictions
- `0.6`: High tolerance (may miss issues)

**Recommended**: 0.2-0.4 for early detection

### `counterfactual_testing` (boolean)
Whether agent tests beliefs against counterfactuals:
- `true`: Regularly tests "what if X were false?"
- `false`: Accepts beliefs at face value

**Recommended**: `true` for all reasoning agents

## Implementation

### 1. Update Agent Registry Schema
```python
# In multi_agent_coordinator.py or agent registry
cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_registry (
        agent_name TEXT PRIMARY KEY,
        role TEXT NOT NULL,
        persona_json TEXT NOT NULL,
        epistemic_config_json TEXT NOT NULL,
        task_types TEXT NOT NULL,
        performance_score REAL NOT NULL
    )
""")
```

### 2. Create Agent With Epistemic Config
```python
agent_config = {
    "agent_name": "research_analyst",
    "role": "Research and analysis specialist",
    "persona": {
        "communication_style": "thorough and evidence-based",
        "expertise_areas": ["academic research", "literature review", "synthesis"]
    },
    "epistemic_config": {
        "stance": "evidence-based",
        "flexibility": 0.85,
        "belief_update_threshold": 0.6,
        "contradiction_tolerance": 0.25,
        "counterfactual_testing": True
    }
}
```

### 3. Use Epistemic Config in Agent Behavior
```python
def should_update_belief(self, new_evidence, current_belief, agent_config):
    """Determine if agent should update belief based on epistemic config."""
    epistemic = agent_config.get("epistemic_config", {})

    evidence_strength = calculate_evidence_strength(new_evidence)
    threshold = epistemic.get("belief_update_threshold", 0.6)

    if evidence_strength >= threshold:
        # Evidence strong enough to update
        flexibility = epistemic.get("flexibility", 0.8)
        update_probability = evidence_strength * flexibility

        # Apply counterfactual test if enabled
        if epistemic.get("counterfactual_testing", False):
            counterfactual_score = test_counterfactual(current_belief, new_evidence)
            update_probability *= counterfactual_score

        return update_probability > 0.5
    return False
```

## Migration Guide

### Step 1: Identify Problematic Personas
Look for agent definitions with hard constraints:
- "ONLY considers X"
- "NEVER accepts Y"
- "ALWAYS uses Z"

### Step 2: Extract Persona from Constraints
Separate identity/style from epistemic behavior:
```python
# Before
"persona": "You are a security expert who NEVER trusts external code"

# After
"role": "Security specialist",
"persona": {
    "communication_style": "cautious and thorough",
    "expertise_areas": ["security analysis", "threat modeling"]
},
"epistemic_config": {
    "stance": "skeptical",
    "flexibility": 0.6,  # Lower than average
    "belief_update_threshold": 0.8  # Requires strong evidence
}
```

### Step 3: Add Epistemic Monitoring
Track when agents refuse belief updates:
```python
if not should_update_belief(evidence, belief, config):
    log_epistemic_event({
        "agent": agent_name,
        "event": "belief_update_refused",
        "evidence_strength": evidence_strength,
        "threshold": threshold,
        "reason": "Below epistemic threshold"
    })
```

## Testing Pattern

### Counterfactual Test
```python
def test_agent_epistemic_flexibility(agent_config):
    """Test if agent updates beliefs when presented with strong evidence."""

    # Present contradictory evidence
    initial_belief = agent.get_belief("topic_X")
    contradictory_evidence = generate_strong_evidence(contradicts=initial_belief)

    # Check if belief updates
    new_belief = agent.process_evidence(contradictory_evidence, agent_config)

    epistemic_config = agent_config.get("epistemic_config", {})
    expected_flexibility = epistemic_config.get("flexibility", 0.8)

    # Agent should update if evidence is strong and flexibility is high
    if evidence_strength > 0.9 and expected_flexibility > 0.7:
        assert new_belief != initial_belief, "Agent failed to update belief despite strong evidence"
```

## Stanford Ask WhAI Pattern

### Out-of-Persona Queries
Allow agents to answer questions outside their persona when epistemic stance permits:

```python
# Enable contextual instantiation
agent_prompt = f"""
{agent.persona.communication_style}

EPISTEMIC STANCE: {agent.epistemic_config.stance}
- You may update beliefs based on evidence (flexibility: {agent.epistemic_config.flexibility})
- Your expertise is {agent.persona.expertise_areas}, but you are not limited to this
- When evidence contradicts your initial beliefs, evaluate it objectively

Task: {task_description}
"""
```

## Benefits

1. **Reduces Narrative Overfitting**: Agents can update beliefs
2. **Improves Multi-Agent Accuracy**: Less persona-driven conflicts
3. **Enables Counterfactual Testing**: Agents test their own beliefs
4. **Maintains Agent Identity**: Persona for communication, epistemic stance for reasoning
5. **Measurable**: Track epistemic flexibility and belief updates

## Example Configurations

### Conservative Analyst
```json
{
  "stance": "conservative",
  "flexibility": 0.5,
  "belief_update_threshold": 0.8,
  "contradiction_tolerance": 0.2,
  "counterfactual_testing": true
}
```

### Exploratory Researcher
```json
{
  "stance": "exploratory",
  "flexibility": 0.9,
  "belief_update_threshold": 0.4,
  "contradiction_tolerance": 0.4,
  "counterfactual_testing": true
}
```

### Skeptical Reviewer
```json
{
  "stance": "skeptical",
  "flexibility": 0.6,
  "belief_update_threshold": 0.9,
  "contradiction_tolerance": 0.1,
  "counterfactual_testing": true
}
```

## References

- Stanford "Ask WhAI" Research (2024)
- Contextual Instantiation Pattern
- Sherlock Problem (persona constraints preventing truth-telling)
- EMR (Editable Memory Representation) System
