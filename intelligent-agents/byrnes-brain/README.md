# Byrnes Brain Architecture

Implementation of Steve Byrnes' brain architecture theory for AGI safety, as discussed in the Adam Marblestone interview.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  LEARNING SUBSYSTEM (Cortex)                                │
│    └─ Feature Extraction → Abstract Representations        │
├─────────────────────────────────────────────────────────────┤
│  THOUGHT ASSESSOR (Amygdala)                                │
│    └─ Predicts Steering responses from abstract features   │
│    └─ Multi-stage curriculum for progressive learning      │
│    └─ Omnidirectional memory for experience-based inference│
├─────────────────────────────────────────────────────────────┤
│  STEERING SUBSYSTEM (Subcortical/Innate)                    │
│    └─ Fast pattern matching (~0.008ms)                      │
│    └─ 5 innate detectors                                    │
│    └─ Immediate blocking for critical threats              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Innate Detectors (`innate_detectors.py`)
Fast pre-conscious pattern matching inspired by the subcortical "Steering Subsystem":

- **SecurityThreatDetector**: Destructive commands, API keys, credentials
- **ProductionViolationDetector**: POC markers, placeholders, mock data
- **ResourceExhaustionDetector**: Infinite loops, large allocations
- **DataCorruptionDetector**: Force pushes, database drops
- **PrivacyViolationDetector**: PII patterns, credential logging

Performance: ~0.008ms per scan (pre-compiled regex)

### 2. Thought Assessor (`thought_assessor.py`)
The "amygdala" that learns to PREDICT when Steering will fire:

- Extracts abstract features from actions (19 dimensions)
- Learns through prediction error (Hebbian-like)
- Multi-stage curriculum for progressive learning
- Integrates with omnidirectional memory

Key insight: The word "spider" triggers the same fear response as seeing a spider because the amygdala learned to predict the innate response.

### 3. Multi-Stage Curriculum
Progressive learning with different stages:

| Stage | Learning Rate | Focus |
|-------|--------------|-------|
| Bootstrap | 0.30 | Easy examples, security + corruption |
| Foundation | 0.20 | Moderate examples, add production |
| Refinement | 0.10 | Challenging examples, all detectors |
| Mastery | 0.05 | Edge cases |
| Maintenance | 0.02 | Continuous learning |

### 4. Omnidirectional Memory (`omnidirectional_memory.py`)
Unlike unidirectional next-token prediction, can predict ANY variable from ANY other:

```python
# Forward inference
memory.infer(tool='Bash') → {'outcome': {'blocked': 0.8}}

# Backward inference
memory.infer(outcome='blocked') → {'detector': {'security_threat': 0.9}}

# Pattern completion
memory.complete_pattern({'tool': 'Write', 'outcome': '?'})
```

## Usage

### Integration with Claude Code Hooks

The components are designed to run in the pre-tool-use and post-tool-use hooks:

```python
# pre-tool-use.py
from innate_detectors import quick_innate_scan
from thought_assessor import predict_steering_response

# Phase 0: Fast innate detection
allow, alerts = quick_innate_scan(action)
if not allow:
    return block_action(alerts)

# Phase 1: Predictive assessment
prediction = predict_steering_response(action)
if prediction.block_probability > 0.8:
    adjust_action(prediction.suggested_adjustments)
```

```python
# post-tool-use.py
from thought_assessor import learn_from_steering

# Learn from actual outcome
learn_from_steering(action, prediction, actual_response)
```

### Standalone Testing

```bash
# Run innate detector tests
python test_innate_detectors.py

# Run thought assessor self-test
python thought_assessor.py --test

# Run omnidirectional memory self-test
python omnidirectional_memory.py
```

## Performance

| Component | Speed | Notes |
|-----------|-------|-------|
| Innate Detectors | 0.008ms | Pre-compiled regex |
| Thought Assessor | 0.108ms | With memory integration |
| Omni Memory | 0.086ms | Spreading activation |

## Theory Background

Based on Steve Byrnes' work on brain architecture:

1. **Two Subsystems**: Learning (cortex) vs Steering (subcortical)
2. **Thought Assessors**: Amygdala learns to predict innate responses
3. **Omnidirectional Inference**: Predict any variable from any other
4. **Multi-stage Curriculum**: Different loss functions at different stages

The key safety insight: If we can make the Thought Assessor predict blocking BEFORE dangerous actions, we achieve proactive safety rather than reactive detection.

## Files

- `innate_detectors.py` - Fast pattern matching (Steering Subsystem)
- `thought_assessor.py` - Prediction model + Curriculum (Amygdala)
- `omnidirectional_memory.py` - Experience-based inference
- `test_innate_detectors.py` - Comprehensive test suite

## Persistence

State is persisted to:
- `~/.claude/thought_assessor_state.json` - Model weights
- `~/.claude/curriculum_state.json` - Curriculum progress
- `~/.claude/omnidirectional_memory.json` - Experience store
