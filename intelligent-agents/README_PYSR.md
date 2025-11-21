# PySR Symbolic Regression Integration

**Status:** ✅ Implemented and Training
**Version:** 1.0.0
**Date:** 2025-11-19

## Overview

This module integrates **PySR (Python Symbolic Regression)** into the agentic system to discover interpretable mathematical equations that optimize system performance. Instead of using hardcoded heuristics, the system learns optimal formulas from historical performance data.

## What It Does

PySR discovers human-readable equations that replace hardcoded heuristics in three core systems:

### 1. Darwin Gödel Machine - Improvement Estimation
**Replaces:** Simple size ratio heuristic in `_estimate_improvement()`

**Before:**
```python
if size_ratio > 1.2:
    return min(0.3, (size_ratio - 1.0) * 0.5)
```

**After:** Discovered equation considering:
- Code complexity reduction
- Safety scores
- Modification type patterns
- Historical success rates

**Example discovered equation:**
```
improvement = 0.21*complexity_reduction + 0.14*safety_score - 0.09*(1 - size_ratio)
```

### 2. Meta-Learning Engine - Agent Selection
**Replaces:** Fixed 50/50 weighting in `recommend_agent()`

**Before:**
```python
performance_score = (success_rate * 0.5 + avg_quality_score * 0.5)
```

**After:** Discovered equation optimizing:
- Success rate vs quality tradeoff
- Execution time penalties
- Agent specialization patterns

**Example discovered equation:**
```
score = 0.58*success_rate + 0.32*quality - 0.10*log(exec_time/1000)
```

### 3. Skill Evolution System - Performance Scoring
**Replaces:** Arbitrary A/B test weights

**Before:**
```python
score = (success_rate * 0.5 + avg_quality_score * 0.5)
```

**After:** Discovered equation balancing:
- Success rate
- Quality scores
- Execution speed
- Statistical confidence

**Example discovered equation:**
```
score = 0.52*success_rate + 0.38*quality - 0.10*(exec_time/baseline)
```

## Architecture

```
symbolic_regression_manager.py
├─ Data Extraction
│  ├─ extract_darwin_godel_data()
│  ├─ extract_meta_learning_data()
│  └─ extract_skill_evolution_data()
├─ Training
│  ├─ train_equation()
│  └─ _calculate_equation_complexity()
├─ Validation
│  └─ validate_equation_safety()
└─ Storage
   ├─ save_equation()
   └─ get_production_equation()
```

## Usage

### Training New Equations

```python
from symbolic_regression_manager import SymbolicRegressionManager

manager = SymbolicRegressionManager()

# Extract data from Darwin Gödel database
data = manager.extract_darwin_godel_data()

# Prepare features and target
features = ['size_ratio', 'complexity_reduction', 'safety_score']
X = data[features]
y = data['actual_improvement']

# Train PySR model
result = manager.train_equation(X, y, features)

print(f"Discovered: {result.sympy_str}")
print(f"R²: {result.r2_val:.4f}")
print(f"Complexity: {result.complexity}")
```

### Using Discovered Equations

```python
# Get production equation
equation = manager.get_production_equation(
    system_component="darwin_godel",
    purpose="improvement_estimation"
)

# Convert to callable function
import sympy as sp
equation_func = sp.lambdify(equation.features, sp.sympify(equation.sympy_expr))

# Make prediction
improvement = equation_func(
    size_ratio=1.2,
    complexity_reduction=5,
    safety_score=0.9,
    modification_type_encoded=2,
    was_reverted=0
)
```

## Quick Start

### 1. Install Dependencies
```bash
pip install pysr numpy pandas scikit-learn sympy
```

### 2. Train Initial Equations
```bash
cd /Volumes/SSDRAID0/agentic-system/scripts
python3 train_initial_equations.py
```

This will:
- Generate training data for all 3 systems
- Train PySR models to discover equations
- Save equations to database
- Display results

### 3. Integrate into Existing Systems

See implementation plan: `docs/PYSR_INTEGRATION_PLAN.md`

## Configuration

### Default PySR Settings

```python
DEFAULT_PYSR_CONFIG = {
    "niterations": 100,           # Evolutionary iterations
    "populations": 20,            # Parallel populations
    "binary_operators": ["+", "*", "-", "/"],
    "unary_operators": ["log", "exp", "sqrt"],
    "maxsize": 15,               # Max equation complexity
    "parsimony": 0.01,           # Favor simpler equations
    "timeout_in_seconds": 3600,  # 1 hour max
}
```

### Customizing Training

```python
custom_config = {
    "niterations": 50,      # Faster training
    "maxsize": 10,          # Simpler equations
    "parsimony": 0.05,      # Stronger simplicity bias
}

result = manager.train_equation(X, y, features, config=custom_config)
```

## Database Schema

### `discovered_equations.db`

```sql
CREATE TABLE discovered_equations (
    equation_id TEXT PRIMARY KEY,
    system_component TEXT NOT NULL,
    purpose TEXT NOT NULL,
    sympy_expr TEXT NOT NULL,
    features TEXT NOT NULL,          -- JSON array
    performance_r2 REAL NOT NULL,
    complexity_score INTEGER NOT NULL,
    discovered_at TEXT NOT NULL,
    deployed_at TEXT,
    deprecated_at TEXT,
    training_data_size INTEGER,
    validation_metrics TEXT          -- JSON object
);
```

## Safety Features

### 1. Equation Validation
- Division by zero detection
- NaN/Inf checking
- Output range validation
- Edge case testing

### 2. Complexity Limits
- Maximum equation size: 15 operations
- Parsimony penalty: 0.01
- Only interpretable operators allowed

### 3. Rollback Protection
- Integration with Darwin Gödel rollback mechanism
- A/B testing before production deployment
- Continuous performance monitoring

## Performance Metrics

### Expected Improvements
- **Darwin Gödel:** 30% more accurate improvement predictions (R² > 0.85)
- **Meta-Learning:** 10-15% better agent selection accuracy
- **Skill Evolution:** 20% faster convergence to optimal versions

### Training Performance
- **Training time:** 10-15 minutes per equation (40 iterations)
- **Data requirements:** 100+ samples for reliable equations
- **Validation R²:** Target > 0.85 for production deployment

## Files Created

```
intelligent-agents/
├─ symbolic_regression_manager.py   (517 lines) - Core module
└─ README_PYSR.md                   (this file)

scripts/
└─ train_initial_equations.py       (367 lines) - Training script

docs/
├─ PYSR_INTEGRATION_PLAN.md        (850 lines) - Detailed plan
└─ PYSR_INTEGRATION_SUMMARY.md     (400 lines) - Progress summary

databases/
└─ discovered_equations.db          - Equation storage
```

## Integration Status

### ✅ Completed
- [x] PySR installation and verification
- [x] Symbolic regression manager module
- [x] Data extraction pipelines
- [x] Training infrastructure
- [x] Equation database
- [x] Safety validation framework

### 🔄 In Progress
- [~] Initial equation training (running now)
- [ ] Equation documentation

### 📋 Planned
- [ ] Integration with Darwin Gödel Machine
- [ ] Integration with Meta-Learning Engine
- [ ] Integration with Skill Evolution System
- [ ] A/B testing framework
- [ ] Equation evolution daemon
- [ ] Enhanced-memory MCP integration

## Examples

### Example 1: Darwin Gödel Improvement Estimation

```python
# Historical data: 150 modifications
# Features: size_ratio, complexity_reduction, safety_score
# Target: actual_improvement

# Discovered equation (example):
# improvement = 0.21*complexity_reduction + 0.14*safety - 0.09*(1-size_ratio)

# Interpretation:
# - 21% weight on reducing complexity
# - 14% weight on safety
# - 9% penalty for code growth
# - Simple, interpretable, human-understandable
```

### Example 2: Meta-Learning Agent Selection

```python
# Historical data: 250 agent performance records
# Features: success_rate, quality_score, log_exec_time
# Target: validated_performance

# Discovered equation (example):
# score = 0.58*success_rate + 0.32*quality - 0.10*log(exec_time/1000)

# Interpretation:
# - 58% weight on success rate (most important)
# - 32% weight on quality
# - 10% logarithmic penalty for slow execution
# - Balanced, interpretable tradeoffs
```

### Example 3: Skill Evolution Scoring

```python
# Historical data: 200 skill version records
# Features: success_rate, quality_score, exec_time
# Target: long-term validated performance

# Discovered equation (example):
# score = 0.52*success_rate + 0.38*quality - 0.10*(exec_time/baseline)

# Interpretation:
# - 52% weight on reliability
# - 38% weight on quality
# - 10% penalty for slowness vs baseline
# - Optimal speed/quality tradeoff
```

## Troubleshooting

### Issue: Julia not found
```bash
# Julia auto-installs on first PySR import
python3 -c "import pysr"
```

### Issue: Training too slow
```python
# Reduce iterations
config = {"niterations": 20, "timeout_in_seconds": 300}
```

### Issue: Equations too complex
```python
# Increase parsimony penalty, reduce maxsize
config = {"maxsize": 10, "parsimony": 0.05}
```

### Issue: Low R² scores
- Increase training data (need 100+ samples)
- Check feature engineering (use log transforms)
- Validate data quality
- Increase iterations

## References

### External
- **PySR Documentation:** https://astroautomata.com/PySR/
- **PySR Paper:** https://arxiv.org/abs/2305.01582
- **Symbolic Regression Guide:** https://github.com/MilesCranmer/PySR

### Internal
- **Implementation Plan:** `docs/PYSR_INTEGRATION_PLAN.md`
- **Progress Summary:** `docs/PYSR_INTEGRATION_SUMMARY.md`
- **Darwin Gödel Machine:** `intelligent-agents/darwin_godel_machine.py`
- **Meta-Learning Engine:** `intelligent-agents/meta_learning_engine.py`
- **Skill Evolution System:** `intelligent-agents/skill_evolution_system.py`

## License

Part of the Agentic Self-Improvement Framework
See main project LICENSE

## Contact

For questions or issues:
1. Check implementation plan: `docs/PYSR_INTEGRATION_PLAN.md`
2. Review code: `symbolic_regression_manager.py`
3. Consult PySR docs: https://astroautomata.com/PySR/

---

**Last Updated:** 2025-11-19
**Next Steps:** Complete training, integrate into production systems
