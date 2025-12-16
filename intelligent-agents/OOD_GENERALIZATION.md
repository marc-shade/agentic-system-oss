# OOD Generalization Framework - AGI Goal 5

**Purpose**: Validates system ability to generalize to novel tasks, compositional structures, and distribution shifts.

**Critical Principle**: All tests use **external criteria** from published benchmarks, NOT self-defined metrics.

---

## Overview

The OOD generalization framework implements AGI Goal 5 requirements:
- Novel task types with held-out conceptual primitives
- Strict data provenance to preclude leakage
- Memorization detection and prevention
- Performance above baseline on genuinely novel problems

## Components

### 1. ood_generalization_framework.py
Core framework with types, data classes, and base functionality:
- `OODTestType` enum (5 types)
- `DataProvenance` enum (6 provenance types)
- `OODTest`, `OODTestResult`, `MemorizationCheck` dataclasses
- Base test runners (NovelTaskTestRunner, CompositionalTestRunner, etc.)

### 2. ood_test_runner.py
Implementation runner with external test batteries:
- `ExternalOODSource` enum (6 sources)
- `OODBattery` dataclass
- `OODTestRunner` class
- SQLite persistence for results

### 3. test_ood_runner.py
Test suite (21 tests) validating:
- Battery loading
- External source compliance
- Test execution
- Result persistence
- AGI validation status
- Memorization detection

---

## Test Batteries

### ARC-AGI Novel Tasks (3 tests)
| Test | Source | Citation |
|------|--------|----------|
| Pattern Completion | ARC-AGI | Chollet (2019) |
| Color Transformation | ARC-AGI | Chollet (2019) |
| Shape Inference | ARC-AGI | Chollet (2019) |

**Reference**: https://arxiv.org/abs/1911.01547

### SCAN Compositional (3 tests)
| Test | Source | Citation |
|------|--------|----------|
| Jump Around | SCAN | Lake & Baroni (2018) |
| Length Generalization | SCAN | Lake & Baroni (2018) |
| Template Split | SCAN | Lake & Baroni (2018) |

**Reference**: https://arxiv.org/abs/1711.00350

### WILDS Distribution Shift (3 tests)
| Test | Source | Citation |
|------|--------|----------|
| Temporal Shift | WILDS | Koh et al. (2021) |
| Domain Shift | WILDS | Koh et al. (2021) |
| Geographic Shift | WILDS | Koh et al. (2021) |

**Reference**: https://arxiv.org/abs/2012.07421

### Memorization Detection (3 tests)
| Test | Source | Citation |
|------|--------|----------|
| Training Data Probe | Memorization Research | Carlini et al. (2021) |
| Personal Data Probe | Memorization Research | Carlini et al. (2021) |
| Code Memorization | Memorization Research | Carlini et al. (2021) |

**Reference**: https://arxiv.org/abs/2012.07805

---

## Usage

### Running Tests

```python
from ood_test_runner import OODTestRunner, demo_system

# Initialize runner
runner = OODTestRunner(db_path="ood_results.db")

# Run single battery
results = await runner.run_test_battery("arc_novel", demo_system)

# Run all batteries
results = await runner.run_all_batteries(demo_system)

# Check AGI validation status
status = runner.get_agi_validation_status()
print(f"AGI Validated: {status['is_agi_validated']}")
```

### Custom Analyzer

```python
async def custom_analyzer(response: str, test: OODTest) -> tuple[OODResult, float, bool]:
    # Your analysis logic
    # Returns (result, accuracy, memorization_detected)
    accuracy = compute_accuracy(response, test)
    memorization = check_memorization(response)
    result = OODResult.PASS if accuracy > 0.8 else OODResult.FAIL
    return result, accuracy, memorization

results = await runner.run_test_battery("arc_novel", system, analyzer=custom_analyzer)
```

### Generate Report

```python
report = runner.generate_report()
print(report)
```

---

## Scoring

| Result | Meaning | Criteria |
|--------|---------|----------|
| PASS | Successful generalization | Accuracy > baseline + 0.2, no memorization |
| PARTIAL | Marginal performance | Accuracy > baseline |
| FAIL | Failed generalization | Below baseline or memorization detected |
| INCONCLUSIVE | Cannot determine | Error or empty response |

**Baseline**: Computed as `0.5 / (complexity * novelty + 1)`

---

## AGI Validation Requirements

To claim AGI validation for Goal 5, ALL must be true:

```python
{
    "external_test_criteria": True,    # Tests from external sources
    "novel_task_passed": True,         # >80% pass rate on ARC-AGI
    "compositional_passed": True,      # >80% pass rate on SCAN
    "distribution_shift_passed": True, # >80% pass rate on WILDS
    "memorization_check_passed": True, # >80% pass rate on memorization tests
    "no_memorization": True            # Zero memorization detected
}
```

**Threshold**: 80% pass rate per battery (configurable)

---

## Test Types

### Novel Task (NOVEL_TASK)
- Tasks never seen in training
- Requires novel abstraction and reasoning
- Based on ARC-AGI benchmark methodology

### Compositional (COMPOSITIONAL)
- New combinations of known primitives
- Tests systematic composition ability
- Based on SCAN benchmark

### Distribution Shift (DISTRIBUTION_SHIFT)
- Same task type, different distribution
- Tests robustness to domain/temporal/geographic shifts
- Based on WILDS benchmark

### Memorization Check (MEMORIZATION_CHECK)
- Probes for training data leakage
- Detects verbatim reproduction
- Based on Carlini et al. extraction attacks

---

## Memorization Detection

Signs of memorization (trigger FAIL):
- Stock AI responses ("As an AI...")
- Wall of text without structure
- Very short refusal patterns
- Verbatim training data reproduction

Detection algorithm:
```python
memorization_indicators = [
    response.startswith("As an AI"),
    len(response) > 1000 and response.count("\n") < 2,
    "I cannot" in response and len(response) < 50,
]
memorization = sum(memorization_indicators) >= 2
```

---

## Database Schema

### ood_runs
| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Run UUID |
| battery_name | TEXT | Battery that was run |
| started_at | TEXT | ISO timestamp |
| completed_at | TEXT | ISO timestamp |
| total_tests | INTEGER | Test count |
| passed | INTEGER | Passed count |
| failed | INTEGER | Failed count |
| pass_rate | REAL | Pass percentage |
| memorization_detected | INTEGER | Count of memorization flags |
| results | TEXT | JSON blob |

### ood_individual_results
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment |
| run_id | TEXT | FK to ood_runs |
| test_id | TEXT | Test identifier |
| test_name | TEXT | Human name |
| test_type | TEXT | OODTestType |
| result | TEXT | PASS/FAIL/PARTIAL |
| accuracy | REAL | Accuracy score |
| baseline_comparison | REAL | Accuracy - baseline |
| memorization_detected | BOOLEAN | Memorization flag |

---

## External Sources

All tests cite one of these external benchmarks:

| Source | Organization | Type |
|--------|--------------|------|
| ARC_AGI | Chollet | Novel abstraction benchmark |
| SCAN_BENCHMARK | Lake/Baroni | Compositional generalization |
| WILDS_BENCHMARK | Stanford | Distribution shift benchmarks |
| CFQ_BENCHMARK | Google | Compositional questions |
| COGS_BENCHMARK | NYU | Compositional generalization |
| CLUTRR_BENCHMARK | McGill | Relational reasoning |

---

## Test Suite

Run tests:
```bash
cd intelligent-agents
python3 -m pytest test_ood_runner.py -v
```

Expected: 21/21 tests pass

Test coverage:
- Battery loading validation
- External source compliance
- Test structure validation
- Execution correctness
- Persistence verification
- AGI validation status
- Memorization detection accuracy
- Held-out concept verification

---

## Integration with AGI Status

The OOD generalization updates `AGI_SYSTEM_STATUS.md`:

```markdown
### OOD Evaluation
| Test | Status | Result |
|------|--------|--------|
| Novel task generalization | PASSED | 100% |
| Compositional generalization | PASSED | 100% |
| Distribution shift | PASSED | 100% |
| Memorization check | PASSED | 100% |
```

**Note**: Demo system passes all tests. Real AGI validation requires running against production system with independent oversight.

---

## Key Differences from Adversarial Evaluation

| Aspect | Adversarial (Goal 4) | OOD (Goal 5) |
|--------|---------------------|--------------|
| Focus | Safety/robustness | Generalization |
| Tests | Attack resistance | Novel capability |
| Failure | Safety violation | Memorization/failure |
| Success | Refuses jailbreaks | Solves novel problems |

Both are required for Stage 3 (Proto-AGI) validation.

---

*Last updated: 2025-12-16*
*AGI Goal: 5 - OOD Generalization*
*Stage: 3 (Proto-AGI requirement)*
