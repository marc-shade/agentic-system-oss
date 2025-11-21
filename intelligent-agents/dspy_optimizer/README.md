# DSPy Optimizer Module

Production-ready DSPy integration for automatic prompt optimization, self-improving modules, and integration with the Darwin-Godel machine.

## Overview

This module provides:

- **Automatic Prompt Optimization**: Using DSPy's teleprompter optimizers (BootstrapFewShot, MIPRO)
- **Self-Improving Modules**: Prompts that evolve based on performance feedback
- **A/B Testing Framework**: Statistical comparison of prompt variants
- **Metrics Collection**: Performance tracking and analysis
- **Darwin-Godel Integration**: Evolutionary optimization with formal verification
- **PySR Integration**: Equation-driven prompt evolution

## Installation

```bash
cd /Volumes/SSDRAID0/agentic-system/intelligent-agents/dspy_optimizer
pip install -r requirements.txt
```

## Quick Start

### Basic Optimization

```python
import dspy
from dspy_optimizer import DSPyOptimizer, OptimizationConfig
from dspy_optimizer.modules import AgentReasoningModule

# Configure
config = OptimizationConfig(
    optimizer_type=OptimizerType.BOOTSTRAP_FEWSHOT,
    max_bootstrapped_demos=4,
    model_name="claude-sonnet-4-20250514"
)

optimizer = DSPyOptimizer(config)

# Create module and training data
module = AgentReasoningModule()
trainset = [
    dspy.Example(
        context="System is running slow",
        question="What could cause this?"
    ).with_inputs("context", "question")
]

# Define metric
def accuracy_metric(example, prediction):
    # Your evaluation logic
    return 1.0 if "relevant" in prediction.answer.lower() else 0.0

# Optimize
result = optimizer.optimize_module(module, trainset, accuracy_metric)
print(f"Improvement: {result.improvement_pct:.2f}%")
```

### Using Pre-built Modules

```python
from dspy_optimizer.modules import (
    ChainOfThoughtAgent,
    ReActAgent,
    CodeAnalysisModule,
    PromptEvolutionModule
)

# Chain-of-thought reasoning
cot = ChainOfThoughtAgent(max_steps=5)
result = cot(task="Analyze system performance", constraints="Focus on memory")

# ReAct agent with tools
react = ReActAgent(tools={
    "search": lambda q: f"Results for: {q}",
    "calculate": lambda x: eval(x)
})
result = react(goal="Find and calculate metrics")

# Code analysis
analyzer = CodeAnalysisModule()
result = analyzer(code="def foo(): pass", analysis_type="style")
```

### A/B Testing

```python
from dspy_optimizer import DSPyOptimizer

optimizer = DSPyOptimizer()

# Create A/B test
test_id = optimizer.create_ab_test(
    module_name="ReasoningModule",
    variant_a_id="prompt_v1",
    variant_b_id="prompt_v2"
)

# Record results during execution
optimizer.record_ab_result(test_id, winner="a")
optimizer.record_ab_result(test_id, winner="b")
optimizer.record_ab_result(test_id, winner="a")

# Check results
results = optimizer.get_ab_test_results(test_id)
print(f"Winner: Variant {results['winner']}")
print(f"Statistical significance: {results['statistical_significance']:.2f}")
```

### Darwin-Godel Evolution

```python
import asyncio
from dspy_optimizer.integration import DarwinGodelIntegration

async def evolve():
    integration = DarwinGodelIntegration(
        population_size=10,
        mutation_rate=0.3
    )

    result = await integration.evolve_prompt(
        module=my_module,
        baseline_prompt="Original prompt here",
        trainset=training_examples,
        metric=my_metric,
        max_generations=10
    )

    print(f"Best fitness: {result.best_candidate.fitness_score}")
    print(f"Improvement: {result.improvement_over_baseline}")
    print(f"PySR equations used: {result.pysr_equations_used}")

asyncio.run(evolve())
```

### Metrics Collection

```python
from dspy_optimizer.metrics import MetricsCollector, track_performance

collector = MetricsCollector()

# Manual recording
collector.record_execution(
    module_name="ReasoningModule",
    prompt_id="v1.2.3",
    latency_ms=150.5,
    token_count=500,
    success=True,
    score=0.85
)

# Get aggregated metrics
metrics = collector.get_aggregated_metrics("ReasoningModule", time_period="24h")
print(f"Success rate: {metrics.success_rate:.2%}")
print(f"P95 latency: {metrics.p95_latency_ms:.2f}ms")

# Compare prompts
comparison = collector.compare_prompts("prompt_v1", "prompt_v2")
print(f"Winner: {comparison['winner']}")

# Performance trend
trend = collector.get_performance_trend("ReasoningModule", time_period="7d")

# Decorator for automatic tracking
@track_performance(collector, "MyModule")
def my_function(input_data):
    # Your logic here
    return result
```

## Module Architecture

```
dspy_optimizer/
├── __init__.py          # Package exports
├── optimizer.py         # Main DSPy optimization engine
├── modules.py           # Reusable DSPy modules
├── metrics.py           # Performance tracking
├── integration.py       # Darwin-Godel machine integration
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## DSPy Signatures

### ReasoningSignature
- **Inputs**: context, question
- **Outputs**: reasoning, answer

### CodeAnalysisSignature
- **Inputs**: code, analysis_type
- **Outputs**: analysis, recommendations, severity

### PromptEvolutionSignature
- **Inputs**: original_prompt, performance_data, task_description
- **Outputs**: evolved_prompt, changes_made, expected_improvement

### ReActSignature
- **Inputs**: context, goal, available_tools
- **Outputs**: thought, action, observation_needed

## Database Schema

Stored in `/Volumes/SSDRAID0/agentic-system/databases/dspy_optimizer.db`:

- `optimization_results`: Optimization run history
- `prompt_versions`: Version-controlled prompts
- `ab_tests`: A/B test configurations and results
- `prompt_metrics`: Per-execution performance metrics
- `evolution_candidates`: Evolutionary population
- `evolution_cycles`: Evolution run history

## Integration Points

### Darwin-Godel Machine
The integration module connects to:
- `/Volumes/SSDRAID0/agentic-system/intelligent-agents/darwin_godel_machine.py`

### PySR Equations
Loads equations from:
- `/Volumes/SSDRAID0/agentic-system/databases/discovered_equations.db`

### Enhanced Memory
Can store optimized prompts in the enhanced-memory MCP for persistence.

## Configuration Options

```python
@dataclass
class OptimizationConfig:
    optimizer_type: OptimizerType = OptimizerType.BOOTSTRAP_FEWSHOT
    max_bootstrapped_demos: int = 4
    max_labeled_demos: int = 16
    max_rounds: int = 1
    num_candidate_programs: int = 10
    metric_threshold: float = 0.7
    temperature: float = 0.7
    max_tokens: int = 2048
    model_name: str = "claude-sonnet-4-20250514"
    save_optimized: bool = True
```

## Best Practices

1. **Start with BootstrapFewShot**: It's the most stable optimizer for most use cases.

2. **Collect enough examples**: Aim for 50-100 training examples for reliable optimization.

3. **Define clear metrics**: Your metric function should return values between 0 and 1.

4. **Use A/B testing**: Don't deploy without statistical validation.

5. **Monitor metrics continuously**: Performance can drift over time.

6. **Leverage PySR**: For complex optimization patterns, enable PySR-guided mutations.

## Troubleshooting

### "No improvement after optimization"
- Check your metric function is discriminative enough
- Try increasing `max_bootstrapped_demos`
- Verify training data quality

### "High latency"
- Reduce `max_tokens` in config
- Use smaller training sets for initial optimization
- Consider using BOOTSTRAP_FEWSHOT over MIPRO

### "A/B test shows no significance"
- Need at least 30 trials per variant
- Check that variants are actually different
- Ensure metric captures meaningful differences

## License

Internal use only - 2 Acre Studios
