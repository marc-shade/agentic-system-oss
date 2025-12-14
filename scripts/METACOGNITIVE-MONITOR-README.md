# Metacognitive Monitoring System

Research-based metacognitive monitoring for AGI systems implementing TRAP framework and failure prediction.

## Overview

The Metacognitive Monitoring System tracks self-awareness, reasoning quality, and failure prediction for autonomous agents based on cutting-edge research in agentic metacognition.

**Research Implementation:**
- **TRAP Framework** (Transparency, Reasoning, Adaptation, Perception)
- **Failure Prediction Triggers** (latency, repetition, confidence, stuck states)
- **Metacognitive Awareness Dimensions** (self, knowledge, process, limitation awareness)
- **Confidence Calibration** tracking and accuracy measurement

## Key Features

### 1. TRAP Framework Evaluation

**Transparency (0.0-1.0):**
- Quality of reasoning logs
- Completeness of decision documentation
- Traceability of thought process

**Reasoning Depth (count):**
- Self-reflection checkpoints
- Depth of meta-reasoning

**Adaptation Count (count):**
- Strategy adjustments made
- Error detection and correction

**Perception Accuracy (0.0-1.0):**
- Confidence calibration quality
- Predicted vs actual performance

### 2. Failure Prediction Triggers

**Latency Monitoring:**
- Simple tasks: 5s threshold
- Moderate tasks: 15s threshold
- Complex tasks: 30s threshold
- Novel tasks: 60s threshold

**Action Repetition Detection:**
- Flags repeated actions (>3 times)
- Identifies ineffective strategies

**Confidence Thresholds:**
- Low confidence (<0.5) triggers review
- Confidence mismatch detection (high confidence but failure)

**Stuck State Detection:**
- No progress for 5+ iterations
- Stagnant performance metrics

### 3. Metacognitive Awareness Tracking

**Self-Awareness (0.0-1.0):**
- Awareness of own state and capabilities
- Understanding of current limitations

**Knowledge-Awareness (0.0-1.0):**
- What is known vs unknown
- "Knowing what you know" vs "knowing what you don't know"

**Process-Awareness (0.0-1.0):**
- Understanding of own reasoning process
- Metacognitive monitoring quality

**Limitation-Awareness (0.0-1.0):**
- Boundary recognition
- Capability limitations understanding

## Installation

```bash
# The scripts are already in place
cd /mnt/agentic-system/scripts

# Make executable
chmod +x metacognitive-monitor.py
chmod +x metacognitive-integration-example.py

# Test installation
python metacognitive-monitor.py --help
```

## Usage

### Recording Metacognitive State

```bash
python metacognitive-monitor.py record \
  --task-id task_123 \
  --task-type code_generation \
  --complexity complex \
  --confidence 0.8 \
  --strategy "iterative_refinement" \
  --reasoning-trace "Step 1|Step 2|Step 3" \
  --self-awareness 0.8 \
  --knowledge-awareness 0.7 \
  --process-awareness 0.75 \
  --limitation-awareness 0.6
```

**Output:**
```json
{
  "timestamp": "2025-11-28T09:24:14.082160",
  "task_id": "task_123",
  "task_type": "code_generation",
  "complexity": "complex",
  "trap_metrics": {
    "transparency_score": 0.52,
    "reasoning_depth": 0,
    "adaptation_count": 0,
    "perception_accuracy": 0.5
  },
  "self_awareness": 0.8,
  "knowledge_awareness": 0.7,
  "process_awareness": 0.75,
  "limitation_awareness": 0.6,
  "confidence_level": 0.8
}
```

### Failure Prediction

```bash
python metacognitive-monitor.py predict \
  --task-id task_123 \
  --duration-ms 35000 \
  --complexity moderate \
  --confidence 0.4
```

**Output:**
```
⚠ 2 failure trigger(s) detected:

{
  "triggered": true,
  "trigger_type": "latency_exceeded",
  "confidence": 0.7,
  "reason": "Task duration (35000ms) exceeds threshold (15000ms)",
  "recommended_action": "Consider simplifying approach or breaking into subtasks"
}

{
  "triggered": true,
  "trigger_type": "low_confidence",
  "confidence": 0.6,
  "reason": "Confidence level (0.40) below threshold (0.5)",
  "recommended_action": "Seek additional information or request human guidance"
}
```

### Analyzing Metacognitive Accuracy

```bash
# Analyze last 7 days
python metacognitive-monitor.py analyze --days 7
```

**Output:**
```json
{
  "period_days": 7,
  "total_states": 42,
  "total_actions": 38,
  "total_predictions": 12,
  "average_trap_scores": {
    "transparency": 0.68,
    "reasoning_depth": 2.3,
    "adaptation_count": 1.8,
    "perception_accuracy": 0.72
  },
  "awareness_trends": {
    "self_awareness": [0.6, 0.65, 0.7, ...],
    "knowledge_awareness": [0.5, 0.6, 0.65, ...]
  },
  "prediction_accuracy": {
    "total_predictions": 12,
    "by_trigger_type": {
      "latency_exceeded": 5,
      "action_repetition": 4,
      "low_confidence": 2,
      "stuck_state": 1
    }
  },
  "confidence_calibration": {
    "high_confidence_success_rate": 0.85,
    "low_confidence_success_rate": 0.35,
    "calibration_gap": 0.15
  }
}
```

### Continuous Monitoring (Daemon Mode)

```bash
# Monitor every 60 seconds
python metacognitive-monitor.py monitor --interval 60
```

### Export Metrics

```bash
python metacognitive-monitor.py export \
  --output /tmp/metacog_export.json \
  --format json
```

## Integration with AGI Workflows

### Example 1: Code Generation Task

```python
from metacognitive_monitor import MetacognitiveMonitor, TaskComplexity, TRAPEvaluator

monitor = MetacognitiveMonitor()
trap_eval = TRAPEvaluator()

# Track reasoning
reasoning = []
reasoning.append("Analyzed requirements")
trap_eval.record_reasoning_checkpoint("Requirements analyzed", depth_level=1)

# Detect need for adaptation
trap_eval.record_adaptation(
    old_strategy="direct_implementation",
    new_strategy="validation_first",
    trigger="missing_validation_logic"
)
reasoning.append("Adapted: Added validation layer")

# Record final state
state = monitor.record_state(
    task_id="code_gen_001",
    task_type="code_generation",
    complexity=TaskComplexity.COMPLEX,
    confidence=0.85,
    reasoning_trace=reasoning,
    current_strategy="validation_first",
    self_awareness=0.8,
    knowledge_awareness=0.7,
    process_awareness=0.75,
    limitation_awareness=0.65
)

# Check for failure predictions
predictions = monitor.predict_failure(
    task_id="code_gen_001",
    duration_ms=5000,
    complexity=TaskComplexity.COMPLEX,
    confidence=0.85
)

if predictions:
    print("⚠ Failure triggers detected!")
    for pred in predictions:
        print(f"  {pred.trigger_type.value}: {pred.reason}")
        print(f"  Action: {pred.recommended_action}")
```

### Example 2: Stuck State Detection

```python
monitor = MetacognitiveMonitor()

# Record repeated failed attempts
for i in range(3):
    monitor.record_action(
        action_id=f"action_{i}",
        action_type="debugging",
        task_id="debug_task",
        duration_ms=8000,
        confidence=0.6,
        success=False
    )

# Add progress markers (showing stagnation)
for progress in [0.2, 0.21, 0.22, 0.21, 0.22]:
    monitor.failure_predictor.add_progress_marker(progress)

# Check predictions
predictions = monitor.predict_failure(
    task_id="debug_task",
    duration_ms=24000,
    complexity=TaskComplexity.MODERATE,
    confidence=0.6
)

# Will detect: action_repetition, stuck_state
```

### Example 3: Learning Curve Tracking

```python
# Track metacognitive awareness as skills develop

# Early stage: Low knowledge-awareness
monitor.record_state(
    task_id="learn_001",
    task_type="learning_pytorch",
    complexity=TaskComplexity.NOVEL,
    confidence=0.4,
    reasoning_trace=["Trying different approaches"],
    current_strategy="trial_and_error",
    self_awareness=0.4,
    knowledge_awareness=0.3,  # Don't know what I don't know
    process_awareness=0.5,
    limitation_awareness=0.6  # Aware of many limitations
)

# Later stage: Improved knowledge-awareness
monitor.record_state(
    task_id="learn_010",
    task_type="learning_pytorch",
    complexity=TaskComplexity.MODERATE,
    confidence=0.8,
    reasoning_trace=["Understood pattern", "Applied known solution"],
    current_strategy="pattern_application",
    self_awareness=0.8,
    knowledge_awareness=0.75,  # Know what I know
    process_awareness=0.8,
    limitation_awareness=0.7
)
```

## Enhanced Memory Integration

When enhanced-memory MCP is available, states are automatically stored:

```python
# Automatic integration
monitor = MetacognitiveMonitor(enable_memory_integration=True)

# States are recorded both locally and in enhanced-memory
state = monitor.record_state(...)
# → Stored in /tmp/metacognitive/metacognitive_states.jsonl
# → Stored in enhanced-memory database with full versioning

# Actions are recorded with outcomes
monitor.record_action(...)
# → Stored locally + enhanced-memory action outcome tracking
```

## Data Storage

**Local Storage** (always available):
- `/tmp/metacognitive/metacognitive_states.jsonl` - All state records
- `/tmp/metacognitive/action_records.jsonl` - All action executions
- `/tmp/metacognitive/failure_predictions.jsonl` - All predictions

**Enhanced Memory Storage** (when available):
- `record_metacognitive_state()` - Full state with context
- `record_action_outcome()` - Action results for learning
- Enables historical analysis and pattern extraction

## Task Complexity Levels

| Complexity | Description | Latency Threshold | Example |
|------------|-------------|-------------------|---------|
| SIMPLE | Single-step operations | 5 seconds | File read, simple calculation |
| MODERATE | Multi-step with clear path | 15 seconds | REST API implementation |
| COMPLEX | Requires planning | 30 seconds | Multi-file refactoring |
| NOVEL | No prior experience | 60 seconds | New framework/paradigm learning |

## Failure Trigger Thresholds

| Trigger | Threshold | Action |
|---------|-----------|--------|
| Latency Exceeded | Complexity-based | Simplify or break into subtasks |
| Action Repetition | 3+ same actions | Try alternative strategy |
| Low Confidence | < 0.5 | Seek additional information |
| Stuck State | 5+ iterations no progress | Reassess or request assistance |
| Confidence Mismatch | High conf + failure | Recalibrate confidence estimation |

## TRAP Metrics Interpretation

### Transparency Score (0.0-1.0)

- **0.0-0.3**: Poor - Minimal reasoning documentation
- **0.3-0.6**: Fair - Some reasoning captured but incomplete
- **0.6-0.8**: Good - Clear reasoning with most steps documented
- **0.8-1.0**: Excellent - Comprehensive, traceable reasoning

### Reasoning Depth (count)

- **0-2**: Shallow - Limited self-reflection
- **3-5**: Moderate - Regular checkpoints
- **6+**: Deep - Extensive meta-reasoning

### Adaptation Count (count)

- **0**: No adaptation (may indicate inflexibility)
- **1-3**: Healthy - Adjusting when needed
- **4+**: High - Frequent strategy changes (possible instability)

### Perception Accuracy (0.0-1.0)

- **0.0-0.5**: Poor calibration - Predictions unreliable
- **0.5-0.7**: Moderate - Some calibration issues
- **0.7-0.9**: Good - Well-calibrated confidence
- **0.9-1.0**: Excellent - Highly accurate self-assessment

## Examples and Testing

Run the integration examples:

```bash
# Full demonstration with 3 examples
python metacognitive-integration-example.py

# Output shows:
# 1. Code generation with TRAP framework
# 2. Failure prediction with stuck state detection
# 3. Metacognitive awareness evolution over learning curve
```

## Research Background

This implementation is based on:

1. **TRAP Framework**: Transparency, Reasoning, Adaptation, Perception
   - Provides structured evaluation of metacognitive quality
   - Enables systematic improvement tracking

2. **Agentic Metacognition Research**:
   - Failure prediction triggers validated in research
   - Latency thresholds based on task complexity
   - Repetition detection for ineffective strategies

3. **Metacognitive Awareness Theory**:
   - Four dimensions: Self, Knowledge, Process, Limitation
   - Tracks evolution from novice to expert
   - "Knowing what you know" as key milestone

4. **Confidence Calibration**:
   - Aligns self-assessment with actual performance
   - Detects overconfidence and underconfidence
   - Enables adaptive confidence estimation

## Future Enhancements

Planned improvements:

- [ ] Real-time visualization dashboard
- [ ] Pattern extraction from historical states
- [ ] Automated threshold tuning based on outcomes
- [ ] Multi-agent coordination awareness
- [ ] Integration with autonomous improvement daemon
- [ ] Causal analysis of failure triggers
- [ ] Metacognitive skill learning curves
- [ ] Export to Grafana/Prometheus for monitoring

## License

Part of the AGI Development System - Mac Pro 5,1 Agentic Node

## See Also

- `/mnt/agentic-system/mcp-servers/enhanced-memory-mcp` - Persistent memory storage
- `/mnt/agentic-system/intelligent-agents/autonomous_improvement_daemon.py` - Self-improvement
- `~/.claude/agi/docs/AGI-SYSTEM-OVERVIEW.md` - AGI system documentation
