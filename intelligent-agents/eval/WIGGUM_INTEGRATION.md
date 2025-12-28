# Wiggum Integration for Self-* Feature Evaluation

## Overview

The Wiggum Evaluation Integration extends the agentic system's self-improvement, self-healing, and self-optimization capabilities with **guaranteed completion loops** and **cross-iteration learning**.

Based on the [Chief Wiggum](https://github.com/jes5199/chief-wiggum) Claude Code plugin, this integration wraps autonomous operations in iterative loops that:
- Keep trying until success criteria is verifiably met
- Capture learnings from each iteration
- Enforce quality gates via Ember
- Track metrics for evaluation

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Wiggum Eval Integration                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │  Task Executor  │───▶│  Wiggum Loop    │───▶│ Ember Check  │ │
│  │  (Self-* Op)    │    │  (Iterations)   │    │ (Quality)    │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
│           │                     │                     │          │
│           ▼                     ▼                     ▼          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │ Darwin-Gödel    │    │ Enhanced Memory │    │  Eval DB     │ │
│  │ (Proof-Verify)  │    │ (Learnings)     │    │  (Metrics)   │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. WiggumEvalIntegration

Main class for wrapping tasks in evaluated Wiggum loops.

```python
from wiggum_eval_integration import WiggumEvalIntegration

evaluator = WiggumEvalIntegration()

async def my_self_improvement_task(iteration: int):
    # Return (success: bool, output: str, insight: str)
    if iteration >= 3:
        return True, "Optimized code", "Third approach worked"
    return False, None, f"Attempt {iteration} failed"

result = await evaluator.evaluate_with_wiggum(
    task="Optimize memory consolidation",
    success_criteria="Consolidation under 100ms",
    task_executor=my_self_improvement_task,
    max_iterations=10,
    criteria_name='self_optimization'
)
```

### 2. WiggumEvalCriteria

Pre-configured evaluation criteria for different self-* operation types:

| Criteria | Max Iterations | Min Quality | Learning Required |
|----------|---------------|-------------|-------------------|
| `self_improvement` | 10 | 0.8 | Yes |
| `self_healing` | 5 | 0.7 | Yes |
| `self_optimization` | 15 | 0.75 | Yes |
| `skill_evolution` | 8 | 0.8 | Yes (higher weight) |

### 3. WiggumDarwinGodelIntegration

Combines Wiggum loops with Darwin-Gödel formal verification:

```python
from wiggum_eval_integration import WiggumDarwinGodelIntegration

dgm_wiggum = WiggumDarwinGodelIntegration()

result = await dgm_wiggum.verified_self_improvement(
    improvement_description="Reduce latency by 50%",
    expected_gain=0.5,
    max_iterations=10
)

# Result includes:
# - Wiggum metrics (iterations, learnings, duration)
# - Darwin-Gödel proof status
# - Quality scores
```

## Evaluation Metrics

Each Wiggum evaluation tracks:

| Metric | Description | Weight |
|--------|-------------|--------|
| `completion` | Did task complete successfully? | 40% |
| `efficiency` | How many iterations needed? | 30% |
| `quality` | Ember approval + quality score | 20% |
| `learning` | Insights captured per iteration | 10% |

### Scoring Formula

```
total_score = (
    completion * 0.4 +
    efficiency * 0.3 +
    quality * 0.2 +
    learning * 0.1
)

passed = total_score >= 0.7 AND ember_approved
```

## Integration Points

### Enhanced Memory

Each iteration stores learnings in enhanced-memory:

```json
{
    "name": "wiggum-eval-abc123-iter2",
    "entityType": "wiggum_eval_iteration",
    "observations": [
        "task: Optimize consolidation",
        "iteration: 2",
        "result: failure",
        "insight: Index optimization not sufficient",
        "duration_ms: 150.5"
    ]
}
```

### Ember Quality Gate

Before marking success, Ember validates:
- No TODO/FIXME markers
- No placeholder content
- No mock data
- Production-ready output

### Darwin-Gödel Machine

For self-improvement tasks:
1. Propose modification with expected gain
2. Generate formal proof of improvement
3. Verify proof validity
4. Apply modification if proven
5. Measure actual improvement
6. Store results in Wiggum loop

## Database Schema

```sql
-- Evaluation results
CREATE TABLE wiggum_evals (
    eval_id TEXT PRIMARY KEY,
    task TEXT,
    success_criteria TEXT,
    outcome TEXT,  -- success, max_iterations, quality_failure, error
    total_iterations INTEGER,
    max_iterations INTEGER,
    ember_approved INTEGER,
    quality_score REAL,
    learnings_stored INTEGER,
    total_duration_ms REAL
);

-- Individual iterations
CREATE TABLE wiggum_iterations (
    eval_id TEXT,
    iteration_number INTEGER,
    approach_tried TEXT,
    result TEXT,
    insight_gained TEXT,
    duration_ms REAL,
    memory_entity_id TEXT
);
```

## CLI Usage

```bash
# Run test evaluation
python3 wiggum_eval_integration.py --test

# View statistics
python3 wiggum_eval_integration.py --stats

# View history
python3 wiggum_eval_integration.py --history
```

## Test Suite

```bash
# Run all 14 tests
python3 eval/test_wiggum_integration.py

# Tests cover:
# - Criteria evaluation (success, failure, quality rejection)
# - Async evaluation (immediate, gradual, max iterations)
# - Efficiency scoring
# - Learning storage
# - Statistics retrieval
# - Darwin-Gödel integration
```

## Example: Self-Healing Pipeline

```python
async def self_healing_pipeline():
    """Heal a broken service with guaranteed completion"""
    evaluator = WiggumEvalIntegration()

    async def heal_service(iteration: int):
        # Diagnose
        diagnosis = await diagnose_failure()

        # Apply fix based on iteration strategy
        if iteration == 1:
            fix = "restart_service"
        elif iteration == 2:
            fix = "clear_cache"
        elif iteration == 3:
            fix = "rollback_config"
        else:
            fix = "full_reinstall"

        result = await apply_fix(fix)

        if result.success:
            return True, f"Fixed with {fix}", f"Solution: {fix} works"
        return False, None, f"{fix} didn't resolve issue"

    result = await evaluator.evaluate_with_wiggum(
        task="Heal broken MCP server",
        success_criteria="Server responds to health check",
        task_executor=heal_service,
        max_iterations=5,
        criteria_name='self_healing'
    )

    return result
```

## Future Enhancements

1. **Multi-Node Wiggum**: Distribute iterations across cluster nodes
2. **A/B Testing**: Compare different iteration strategies
3. **Temporal Integration**: Durable Wiggum loops across sessions
4. **Arduino Feedback**: Physical progress indication during loops
5. **Real-time Memory Search**: Query past learnings during iterations

## Files

| File | Description |
|------|-------------|
| `wiggum_eval_integration.py` | Main integration class |
| `eval/test_wiggum_integration.py` | Test suite (14 tests) |
| `eval/WIGGUM_INTEGRATION.md` | This documentation |

## Related Systems

- **Darwin-Gödel Machine**: `darwin_godel_machine.py`
- **Self-Evaluation System**: `self_evaluation_system.py`
- **Agent Eval Framework**: `agent_eval_framework.py`
- **Skill Evolution**: `skill_evolution_system.py`
- **Chief Wiggum Plugin**: `~/.claude/plugins/chief-wiggum/`
- **Wiggum-Task Skill**: `~/.claude/skills/wiggum-task/`
