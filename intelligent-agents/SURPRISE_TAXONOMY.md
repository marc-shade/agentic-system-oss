# Surprise Taxonomy Framework - AGI Goal 7

**Purpose**: Validates system ability to detect, measure, and respond appropriately to surprising information using mathematically grounded surprise metrics from information theory.

**Critical Principle**: All tests use **external criteria** from published research, NOT self-defined metrics.

---

## Overview

The Surprise Taxonomy framework implements AGI Goal 7 requirements:
- Multiple mathematical surprise measures (Bayesian, Shannon, Novelty, Anomaly)
- Appropriate response calibration to surprise levels
- Contradiction detection for belief revision triggers
- Information-theoretic foundations from peer-reviewed research

## Components

### 1. surprise_taxonomy_runner.py
Core framework with types, data classes, and base functionality:
- `SurpriseTestType` enum (5 types)
- `ExternalSurpriseSource` enum (4 sources)
- `SurpriseTest`, `SurpriseTestResult`, `SurpriseBattery` dataclasses
- Calculation functions for each surprise type
- Demo system implementation

### 2. test_surprise_runner.py
Test suite (54 tests) validating:
- Data structure creation
- Surprise calculation accuracy
- Battery loading
- External source compliance
- Demo system behavior
- Battery execution
- AGI validation status
- Report generation
- Result persistence
- Response appropriateness

---

## Surprise Types and Formulas

### 1. BAYESIAN_SURPRISE (Itti & Baldi, 2009)

**Formula**: KL Divergence from prior to posterior
```
S = KL(posterior || prior) = sum(P_post(x) * log(P_post(x) / P_prior(x)))
```

**Interpretation**:
- S > 0.5: Highly surprising (large belief shift)
- S < 0.1: Not surprising (beliefs unchanged)
- Measures how much new evidence changes beliefs

**Reference**: Itti, L., & Baldi, P. (2009). Bayesian surprise attracts human attention. Vision Research, 49(10), 1295-1306.

### 2. SHANNON_SURPRISE (Shannon, 1948)

**Formula**: Self-information (negative log probability)
```
S = -log2(P(observation))
```

**Interpretation**:
- S > 3.32 bits: Very surprising (P < 0.1)
- S = 1 bit: Coin flip outcome (P = 0.5)
- S < 0.1 bits: Highly expected (P > 0.93)

**Reference**: Shannon, C. E. (1948). A mathematical theory of communication. Bell System Technical Journal, 27(3), 379-423.

### 3. NOVELTY_DETECTION (MIRAS/Titans, 2024)

**Formula**: Inverse of maximum similarity to known patterns
```
N = 1 - max(similarity(obs, pattern) for pattern in known_patterns)
```

**Interpretation**:
- N > 0.8: Highly novel (no similar patterns)
- N < 0.2: Familiar (very similar to known)
- Measures semantic distance from experience

**Reference**: MIRAS/Titans surprise-based memory consolidation research (2024). Contextual memory retention for autonomous agents.

### 4. ANOMALY_DETECTION (Chandola et al., 2009)

**Formula**: Standard deviations from mean (Z-score)
```
A = |observation - mean| / std_dev
```

**Interpretation**:
- A > 3.0: Highly anomalous (3-sigma event)
- A > 2.0: Moderately anomalous
- A < 1.0: Within normal range

**Reference**: Chandola, V., Banerjee, A., & Kumar, V. (2009). Anomaly detection: A survey. ACM Computing Surveys, 41(3), 1-58.

### 5. CONTRADICTION_DETECTION

**Formula**: Boolean check for logical inconsistency
```
C = any(contradicts(obs, belief) for belief in existing_beliefs)
```

**Interpretation**:
- True: Observation contradicts existing beliefs
- False: No contradiction detected
- Triggers belief revision when True

---

## Test Batteries

### Itti-Baldi Bayesian Surprise - Information-Theoretic Surprise (3 tests)
| Test | Description | Expected Surprise Range |
|------|-------------|------------------------|
| bayes_001 | High KL Divergence Detection | 0.4-2.0 (high surprise) |
| bayes_002 | Low Surprise Baseline | 0.0-0.1 (should be ignored) |
| bayes_003 | Multi-outcome Distribution Shift | 0.3-1.5 (moderate-high) |

**Reference**: https://doi.org/10.1016/j.visres.2008.09.007

### Shannon Information Theory - Self-Information Surprise (3 tests)
| Test | Description | Expected Surprise Range (bits) |
|------|-------------|-------------------------------|
| shannon_001 | High Self-Information (rare event) | 3.0-7.0 bits |
| shannon_002 | Low Self-Information (common event) | 0.0-1.0 bits |
| shannon_003 | Information Content Scaling | 1.5-4.0 bits |

**Reference**: Shannon, C. E. (1948). Bell System Technical Journal.

### MIRAS/Titans Novelty Detection - Semantic Novelty (3 tests)
| Test | Description | Expected Novelty Range |
|------|-------------|----------------------|
| novelty_001 | High Novelty Detection | 0.7-1.0 |
| novelty_002 | Familiar Pattern Recognition | 0.0-0.3 |
| novelty_003 | Partial Novelty Assessment | 0.3-0.7 |

**Reference**: MIRAS/Titans contextual memory research (2024).

### Chandola Anomaly Detection - Statistical Anomalies (3 tests)
| Test | Description | Expected Anomaly Range (std devs) |
|------|-------------|----------------------------------|
| anomaly_001 | High Anomaly (3+ sigma) | 2.5-10.0 |
| anomaly_002 | Normal Range Observation | 0.0-1.5 |
| anomaly_003 | Moderate Anomaly Detection | 1.5-3.0 |

**Reference**: https://doi.org/10.1145/1541880.1541882

---

## Usage

### Running Tests

```python
from surprise_taxonomy_runner import SurpriseTestRunner, demo_system

# Initialize runner
runner = SurpriseTestRunner(db_path="surprise_results.db")

# Run single battery
results = await runner.run_test_battery("bayesian_surprise", demo_system)

# Run all batteries
results = await runner.run_all_batteries(demo_system)

# Check AGI validation status
status = runner.get_agi_validation_status()
print(f"AGI Validated: {status['is_agi_validated']}")
```

### Custom System Under Test

```python
def custom_system(test_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    # Your implementation
    # Must return: surprise_score, response_appropriate, details

    if test_type == "BAYESIAN_SURPRISE":
        prior = input_data.get("prior", {})
        posterior = input_data.get("posterior", {})
        surprise = calculate_bayesian_surprise(prior, posterior)
        response_appropriate = surprise > 0.1  # Noticed high surprise
        return {
            "surprise_score": surprise,
            "response_appropriate": response_appropriate,
            "details": {"method": "kl_divergence"}
        }
    # ... handle other types

results = await runner.run_all_batteries(custom_system)
```

### Generate Report

```python
report = runner.generate_report()
print(report)
```

---

## Response Appropriateness Logic

A key component of surprise taxonomy is measuring whether the system responds appropriately:

### High Surprise (expect_high_surprise=True)
- System SHOULD notice and respond
- response_appropriate = surprise_score > threshold (0.1)
- Failure: Missing important information

### Low Surprise (expect_high_surprise=False)
- System SHOULD ignore (not waste resources)
- response_appropriate = surprise_score < threshold (0.1)
- Failure: Wasting attention on mundane data

```python
# In demo_system:
if expect_high_surprise:
    response_appropriate = surprise_score > 0.1  # High surprise should be noticed
else:
    response_appropriate = surprise_score < 0.1  # Low surprise should be ignored
```

---

## AGI Validation Requirements

To claim AGI validation for Goal 7, ALL must be true:

```python
{
    "external_test_criteria": True,       # Tests from external sources
    "bayesian_surprise_passed": True,     # >80% pass rate on Itti-Baldi tests
    "shannon_surprise_passed": True,      # >80% pass rate on Shannon tests
    "novelty_detection_passed": True,     # >80% pass rate on MIRAS/Titans tests
    "anomaly_detection_passed": True,     # >80% pass rate on Chandola tests
    "appropriate_response_rate": True     # >80% response appropriateness
}
```

**Threshold**: 80% pass rate per battery (configurable)

---

## Scoring

| Result | Meaning | Criteria |
|--------|---------|----------|
| PASS | Successful operation | Surprise in expected range AND response appropriate |
| PARTIAL | Marginal performance | Surprise in expected range OR response appropriate |
| FAIL | Failed operation | Neither criterion met |
| INCONCLUSIVE | Cannot determine | Error or invalid response |

---

## Database Schema

### surprise_runs
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
| appropriate_response_rate | REAL | Response appropriateness percentage |
| results | TEXT | JSON blob |

### surprise_individual_results
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Auto-increment |
| run_id | TEXT | FK to surprise_runs |
| test_id | TEXT | Test identifier |
| test_name | TEXT | Human name |
| test_type | TEXT | SurpriseTestType |
| result | TEXT | PASS/FAIL/PARTIAL |
| surprise_score | REAL | Measured surprise |
| expected_min | REAL | Expected range minimum |
| expected_max | REAL | Expected range maximum |
| response_appropriate | BOOLEAN | Appropriate response |
| execution_time_ms | REAL | Execution time |

---

## External Sources

All tests cite one of these external research sources:

| Source | Organization | Citation |
|--------|--------------|----------|
| ITTI_BALDI_BAYESIAN | USC/Caltech | Itti & Baldi 2009 - Bayesian Surprise |
| SHANNON_INFORMATION | Bell Labs | Shannon 1948 - Information Theory |
| MIRAS_TITANS | AI Research | MIRAS/Titans 2024 - Contextual Memory |
| CHANDOLA_ANOMALY | UMN | Chandola et al. 2009 - Anomaly Detection Survey |

---

## Test Suite

Run tests:
```bash
cd intelligent-agents
python3 -m pytest test_surprise_runner.py -v
# Or directly:
python3 test_surprise_runner.py
```

Expected: 54/54 tests pass

Test coverage:
- Data structure validation (SurpriseTest, SurpriseTestResult, SurpriseBattery)
- Surprise calculation accuracy (Bayesian, Shannon, Novelty, Anomaly)
- Battery loading validation
- External source compliance
- Demo system behavior
- Battery execution correctness
- AGI validation status
- Report generation
- Result persistence
- Response appropriateness handling

---

## Integration with AGI Status

The Surprise Taxonomy updates `AGI_SYSTEM_STATUS.md`:

```markdown
### Surprise Evaluation
| Test | Status | Result |
|------|--------|--------|
| Bayesian surprise | PASSED | 100% |
| Shannon surprise | PASSED | 100% |
| Novelty detection | PASSED | 100% |
| Anomaly detection | PASSED | 100% |
```

**Note**: Demo system passes all tests. Real AGI validation requires running against production system with independent oversight.

---

## Key Differences from Other Goals

| Aspect | Adversarial (Goal 4) | OOD (Goal 5) | Provenance (Goal 6) | Surprise (Goal 7) |
|--------|---------------------|--------------|---------------------|-------------------|
| Focus | Safety/robustness | Generalization | Self-improvement | Information processing |
| Tests | Attack resistance | Novel capability | L-Score tracking | Surprise detection |
| Failure | Safety violation | Memorization | Broken provenance | Missed information |
| Success | Refuses jailbreaks | Solves novel problems | Improves over time | Calibrated responses |

All are required for Stage 3 (Proto-AGI) validation.

---

## Demo System Behavior

The demo_system handles different test types:

1. **Bayesian Surprise**: Calculates KL divergence from prior to posterior
2. **Shannon Surprise**: Calculates -log2(probability) self-information
3. **Novelty Detection**: Returns 1 - max_similarity for observation
4. **Anomaly Detection**: Calculates z-score (standard deviations from mean)
5. **Contradiction Detection**: Checks for logical inconsistencies

Response appropriateness is calibrated per test:
- High-surprise tests: appropriate if surprise detected (> 0.1)
- Low-surprise tests: appropriate if surprise ignored (< 0.1)

---

## Mathematical Foundations

### Why Multiple Surprise Measures?

Different surprise types capture different aspects of information:

1. **Bayesian**: Measures belief change magnitude (epistemological surprise)
2. **Shannon**: Measures event rarity (probabilistic surprise)
3. **Novelty**: Measures semantic distance (conceptual surprise)
4. **Anomaly**: Measures statistical deviation (distributional surprise)

An AGI system should handle all types appropriately.

### Information-Theoretic Connections

```
Shannon Surprise: S = -log2(P(x))
Bayesian Surprise: S = KL(P_post || P_prior)
Cross-Entropy: H(P,Q) = E_P[-log Q(x)]

Relationship: KL(P||Q) = H(P,Q) - H(P)
```

The framework validates that the system correctly implements these relationships.

---

*Last updated: 2025-12-16*
*AGI Goal: 7 - Surprise Taxonomy*
*Stage: 3 (Proto-AGI requirement)*
