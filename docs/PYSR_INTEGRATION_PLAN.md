# PySR Integration Plan for Agentic System

**Date:** 2025-11-19
**Status:** Planning Phase
**Goal:** Integrate symbolic regression to discover interpretable equations for agentic system optimization

## Executive Summary

PySR (Python Symbolic Regression) will enhance the agentic system's self-improvement capabilities by discovering interpretable mathematical equations from performance data. Instead of using hardcoded heuristics, the system will learn optimal formulas for:

1. Performance prediction and improvement estimation
2. Agent selection and task routing
3. Skill evolution scoring
4. System optimization patterns

## Research Findings

### PySR Capabilities
- **High-performance symbolic regression** using evolutionary algorithms
- **Interpretable equations** (human-readable math, not black boxes)
- **Symbolic distillation** - convert neural networks to equations
- **Multi-population evolution** with JIT compilation (near C++ speeds)
- **Applications**: Scientific discovery, equation extraction, performance optimization

### Key Insight from Research
From "Automated Scientific Discovery" paper:
> "AI systems capable of making Nobel-quality scientific discoveries highly autonomously... require integrating: hypothesis generation, experimental design, and result interpretation"

**Application to Agentic Systems:**
- **Hypothesis generation** = PySR discovers performance equations
- **Experimental design** = Darwin Gödel proposes modifications
- **Result interpretation** = Meta-learning validates and promotes

## Current System Analysis

### 1. Darwin Gödel Machine (`darwin_godel_machine.py`)

**Current Limitations:**
- Line 415-429: `_estimate_improvement()` uses simple code size ratio heuristic
- Line 250-295: `measure_performance()` tracks metrics but doesn't model relationships
- Line 371-402: `_generate_proof()` uses structural analysis, not learned patterns

**Performance Data Available:**
- Modification proposals with expected improvements
- Actual performance measurements (task_success_rate, execution_time, resource_efficiency)
- Safety scores and complexity metrics
- Complete modification history in database

**PySR Integration Opportunity:**
```python
# Current: Simple heuristic
size_ratio = len(code_before) / max(len(code_after), 1)
if size_ratio > 1.2:
    return min(0.3, (size_ratio - 1.0) * 0.5)

# After PySR: Discovered equation
# Example: improvement = 0.15 * complexity_reduction + 0.08 * log(size_ratio) - 0.03 * safety_penalty
```

### 2. Meta-Learning Engine (`meta_learning_engine.py`)

**Current Limitations:**
- Line 219-257: `recommend_agent()` uses fixed 50/50 weighting of success_rate and quality_score
- Line 296-382: `detect_patterns()` uses manual pattern rules
- Line 534: Score calculation `score_a = (metric_a.success_rate * 0.5 + metric_a.avg_quality_score * 0.5)` is arbitrary

**Performance Data Available:**
- 100+ task outcomes per agent/task-type combination
- Success rates, execution times, quality scores
- Time-based performance variations
- Agent specialization patterns

**PySR Integration Opportunity:**
```python
# Current: Fixed weights
performance_score = (success_rate * 0.5 + avg_quality_score * 0.5)

# After PySR: Discovered equation
# Example: score = 0.63 * success_rate + 0.37 * quality - 0.12 * log(exec_time)
```

### 3. Skill Evolution System (`skill_evolution_system.py`)

**Current Limitations:**
- Line 533-535: A/B test scoring uses fixed 50/50 weighting
- Line 539: Confidence calculation `min(1.0, difference * 5)` is oversimplified
- No consideration of execution time vs quality tradeoffs

**Performance Data Available:**
- Per-version metrics: success_rate, avg_execution_time_ms, avg_quality_score
- Total executions for statistical significance
- Historical promotion/demotion decisions

**PySR Integration Opportunity:**
```python
# Current: Simple weighted average
score = (success_rate * 0.5 + avg_quality_score * 0.5)

# After PySR: Discovered equation considering speed/quality tradeoff
# Example: score = 0.55 * success_rate + 0.35 * quality - 0.10 * (exec_time / baseline)
```

### 4. Autonomous Improvement Daemon

**Current State:**
- Runs hourly improvement cycles (197 cycles completed)
- Logs contain: cycle duration, meta_learning results, skill_evolution status, darwin_godel modifications
- Rich temporal data for pattern discovery

**PySR Integration Opportunity:**
- Discover optimal cycle timing based on system load
- Predict improvement potential before running expensive cycles
- Learn when different improvement strategies are most effective

## Integration Architecture

### Phase 1: Foundation (Week 1)

**1.1 Install and Test PySR**
```bash
# Install PySR
pip install pysr

# Verify Julia installation (auto-installs on first import)
python3 -c "import pysr; print(pysr.__version__)"
```

**1.2 Create PySR Manager Module**
New file: `intelligent-agents/symbolic_regression_manager.py`

Responsibilities:
- Data extraction from Darwin Gödel, Meta-Learning, and Skill Evolution databases
- Feature engineering (complexity metrics, temporal patterns, etc.)
- PySR model training and equation discovery
- Equation validation and safety checks
- Integration with existing systems

**1.3 Data Pipeline**
```python
class SymbolicRegressionManager:
    def extract_darwin_godel_data(self) -> pd.DataFrame:
        """Extract modification data for improvement estimation"""
        # Features: code_before_complexity, code_after_complexity,
        #           safety_score, modification_type_encoded
        # Target: actual_improvement (measured performance change)

    def extract_meta_learning_data(self) -> pd.DataFrame:
        """Extract agent performance data for selection optimization"""
        # Features: agent_type, task_complexity, historical_success_rate,
        #           avg_execution_time, context_features
        # Target: quality_score

    def extract_skill_evolution_data(self) -> pd.DataFrame:
        """Extract skill version performance for scoring optimization"""
        # Features: success_rate, avg_execution_time_ms, total_executions,
        #           code_complexity, version_age
        # Target: long_term_quality (validated over time)
```

### Phase 2: Equation Discovery (Week 2)

**2.1 Darwin Gödel Enhancement**

Discover equation for `_estimate_improvement()`:
```python
from pysr import PySRRegressor

# Configure for interpretability over accuracy
model = PySRRegressor(
    niterations=100,
    binary_operators=["+", "*", "-", "/"],
    unary_operators=["exp", "log", "sqrt"],
    constraints={'exp': 4, 'log': 4},  # Limit complexity
    maxsize=15,  # Max equation size
    parsimony=0.01,  # Favor simplicity
)

# Train on historical modifications
X = df[['complexity_reduction', 'size_ratio', 'safety_score', 'modification_type']]
y = df['actual_improvement']
model.fit(X, y)

# Get best equation
best_equation = model.sympy()
print(f"Discovered: improvement = {best_equation}")
```

**2.2 Meta-Learning Enhancement**

Discover optimal agent selection formula:
```python
# Train on agent performance data
X = df[['agent_success_rate', 'agent_quality', 'avg_exec_time', 'task_complexity']]
y = df['actual_performance']

model = PySRRegressor(
    niterations=150,
    binary_operators=["+", "*", "-", "/", "max", "min"],
    unary_operators=["log", "sqrt"],
    maxsize=20,
)
model.fit(X, y)

# Discovered equation example:
# score = 0.63 * success_rate + 0.37 * quality - 0.12 * log(1 + exec_time/1000)
```

**2.3 Skill Evolution Enhancement**

Discover A/B test scoring formula:
```python
X = df[['success_rate', 'quality_score', 'exec_time_ms', 'total_executions']]
y = df['validated_performance']  # Long-term validated quality

model = PySRRegressor(
    niterations=100,
    binary_operators=["+", "*", "-", "/"],
    unary_operators=["log", "sqrt"],
    maxsize=12,
)
model.fit(X, y)
```

### Phase 3: Integration and Validation (Week 3)

**3.1 Safe Equation Deployment**

Create equation validator:
```python
class EquationValidator:
    def validate_safety(self, equation: sp.Expr) -> bool:
        """Ensure equation is safe to execute"""
        # Check for division by zero potential
        # Verify bounded output range
        # Test on edge cases
        # Ensure monotonicity where expected

    def validate_performance(self, equation: sp.Expr,
                           test_data: pd.DataFrame) -> float:
        """Compare equation predictions vs actual outcomes"""
        # Calculate MSE, R², and interpretability score
```

**3.2 A/B Testing of Equations**

Run equations through skill evolution A/B testing:
```python
# Version A: Current heuristic
# Version B: PySR-discovered equation
# Metric: Actual system performance improvement over 1 week
```

**3.3 Rollback Safety**

Use Darwin Gödel's existing rollback mechanism:
```python
# If PySR equation causes performance degradation
# Automatic rollback to previous heuristic
# Log failure for future learning
```

### Phase 4: Advanced Features (Week 4)

**4.1 Continuous Equation Evolution**

Auto-retrain equations weekly:
```python
class EquationEvolutionDaemon:
    async def run_evolution_cycle(self):
        """Periodically retrain equations with new data"""
        # Extract latest performance data (last 7 days)
        # Retrain PySR models
        # Validate new equations
        # Propose as Darwin Gödel modifications
        # A/B test vs current equations
```

**4.2 Multi-Objective Optimization**

Discover equations balancing multiple objectives:
```python
# Optimize for: accuracy AND interpretability AND speed
model = PySRRegressor(
    multiobjective=True,
    objectives=["accuracy", "complexity"],
    weights=[0.7, 0.3],  # 70% accuracy, 30% simplicity
)
```

**4.3 Equation Explanation System**

Generate human-readable explanations:
```python
def explain_equation(equation: sp.Expr, feature_names: List[str]) -> str:
    """Convert symbolic equation to natural language explanation"""
    # Example output:
    # "Performance improves by 63% of success rate, plus 37% of quality score,
    #  minus a logarithmic penalty for execution time"
```

## Implementation Tasks

### Week 1: Foundation
- [x] Research PySR capabilities and integration patterns
- [ ] Install PySR and verify Julia backend
- [ ] Create `symbolic_regression_manager.py` skeleton
- [ ] Implement data extraction pipelines
- [ ] Write unit tests for data extraction

### Week 2: Equation Discovery
- [ ] Extract Darwin Gödel modification history
- [ ] Train PySR model for improvement estimation
- [ ] Extract Meta-Learning performance data
- [ ] Train PySR model for agent selection
- [ ] Extract Skill Evolution A/B test data
- [ ] Train PySR model for skill scoring
- [ ] Document discovered equations

### Week 3: Integration & Validation
- [ ] Implement `EquationValidator` with safety checks
- [ ] Create integration points in Darwin Gödel Machine
- [ ] Create integration points in Meta-Learning Engine
- [ ] Create integration points in Skill Evolution System
- [ ] Run A/B tests: heuristics vs PySR equations
- [ ] Implement rollback mechanisms
- [ ] Create performance monitoring dashboard

### Week 4: Advanced Features
- [ ] Implement `EquationEvolutionDaemon`
- [ ] Add continuous retraining pipeline
- [ ] Implement multi-objective optimization
- [ ] Create equation explanation system
- [ ] Store equations in enhanced-memory MCP
- [ ] Integration testing across all systems
- [ ] Documentation and knowledge transfer

## Success Metrics

### Quantitative
1. **Improvement Prediction Accuracy**: R² > 0.7 for Darwin Gödel equations
2. **Agent Selection Performance**: 10-15% improvement in task success rate
3. **Skill Evolution Efficiency**: 20% faster convergence to optimal versions
4. **Equation Interpretability**: Max complexity score < 15 (human-readable)
5. **System Overhead**: < 5% increase in computation time

### Qualitative
1. **Interpretability**: Engineers can understand discovered equations
2. **Trustworthiness**: Equations match domain expertise when validated
3. **Stability**: No performance regressions during A/B testing
4. **Maintainability**: Clear path for equation updates and versioning

## Risk Mitigation

### Risk 1: Overfitting
**Mitigation**:
- Use train/validation/test splits (60/20/20)
- Regularization via parsimony parameter
- Complexity constraints (maxsize < 15)
- Cross-validation across time periods

### Risk 2: Unstable Equations
**Mitigation**:
- Equation validator checks for division by zero
- Bounded output ranges enforced
- Sanity tests on edge cases
- Gradual rollout via A/B testing

### Risk 3: Performance Degradation
**Mitigation**:
- Darwin Gödel automatic rollback
- Continuous monitoring of key metrics
- Human-in-the-loop for critical changes
- Weekly performance reviews

### Risk 4: Complexity Creep
**Mitigation**:
- Hard limits on equation size (maxsize=15)
- Parsimony penalty favoring simpler equations
- Multi-objective optimization (accuracy + simplicity)
- Regular equation audits for interpretability

## Expected Outcomes

### Short-term (1 month)
- PySR integrated into 3 core systems
- 3-5 production-ready equations discovered
- 10-15% improvement in agent selection accuracy
- Complete A/B test validation framework

### Medium-term (3 months)
- Autonomous equation evolution daemon running 24/7
- 80%+ of heuristics replaced with discovered equations
- Comprehensive equation explanation system
- Integration with enhanced-memory for equation versioning

### Long-term (6 months)
- Self-improving equation discovery (PySR discovers equations about PySR)
- Multi-domain equation transfer learning
- Automated scientific paper generation from discoveries
- Contribution to PySR open source project with agentic use cases

## Technical Specifications

### Dependencies
```txt
pysr>=0.16.0
sympy>=1.12
pandas>=2.0.0
numpy>=1.24.0
scikit-learn>=1.3.0
matplotlib>=3.7.0  # For equation visualization
```

### Database Schema Extensions

**New table: `discovered_equations`**
```sql
CREATE TABLE discovered_equations (
    equation_id TEXT PRIMARY KEY,
    system_component TEXT NOT NULL,  -- darwin_godel, meta_learning, etc.
    purpose TEXT NOT NULL,
    sympy_expr TEXT NOT NULL,
    features TEXT NOT NULL,  -- JSON array
    performance_r2 REAL NOT NULL,
    complexity_score INTEGER NOT NULL,
    discovered_at TEXT NOT NULL,
    deployed_at TEXT,
    deprecated_at TEXT,
    training_data_size INTEGER,
    validation_metrics TEXT  -- JSON object
);
```

### Configuration
```python
# Default PySR configuration
PYSR_CONFIG = {
    "niterations": 100,
    "populations": 20,
    "binary_operators": ["+", "*", "-", "/"],
    "unary_operators": ["log", "exp", "sqrt"],
    "maxsize": 15,
    "parsimony": 0.01,
    "timeout_in_seconds": 3600,  # 1 hour max
}
```

## Integration with Existing Systems

### Enhanced-Memory MCP
Store discovered equations as entities:
```python
mcp__enhanced-memory-mcp__create_entities([{
    "name": f"pysr-equation-{equation_id}",
    "entityType": "discovered_equation",
    "observations": [
        f"system: {system_component}",
        f"purpose: {purpose}",
        f"equation: {sympy_expr}",
        f"performance: R²={r2:.3f}",
        f"complexity: {complexity}",
        f"features: {', '.join(features)}"
    ]
}])
```

### Agent Runtime MCP
Track equation evolution as persistent goals:
```python
goal = mcp__agent-runtime-mcp__create_goal({
    "name": "Equation Evolution - Agent Selection",
    "description": "Continuously improve agent selection equation using PySR"
})
```

### Sequential Thinking MCP
Deep reasoning about equation validity:
```python
mcp__sequential-thinking__sequentialthinking({
    "thought": "Analyzing discovered equation for agent selection...",
    "thoughtNumber": 1,
    "totalThoughts": 5,
    "nextThoughtNeeded": true
})
```

## Next Steps

1. **Immediate**: Review and approve this plan
2. **This Week**: Install PySR and create symbolic_regression_manager.py
3. **Week 1 End**: Complete data extraction pipelines
4. **Week 2 End**: Discover first production equations
5. **Week 3 End**: Deploy equations with A/B testing
6. **Week 4 End**: Launch autonomous equation evolution daemon

## References

- PySR Documentation: https://astroautomata.com/PySR/
- PySR Paper: "Interpretable Machine Learning for Science with PySR and SymbolicRegression.jl"
- Automated Scientific Discovery: https://arxiv.org/html/2305.02251
- Darwin Gödel Machine: Based on Schmidhuber's Gödel Machine concept
