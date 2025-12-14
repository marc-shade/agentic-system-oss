# /adaptive-evolution

Deploy the Adaptive Agent Evolution system for dynamic agent optimization and evolution.

## Usage
```
/adaptive-evolution [evolution-type] [parameters]
```

## Evolution Types

### agent-optimization
Optimize existing agent performance based on metrics
```
/adaptive-evolution agent-optimization "lead-generator" --metric="conversion-rate"
```

### capability-expansion  
Evolve agent capabilities based on new requirements
```
/adaptive-evolution capability-expansion "seo-analyzer" --add-capability="backlink-analysis"
```

### behavioral-adaptation
Adapt agent behavior based on user patterns
```
/adaptive-evolution behavioral-adaptation "executive-assistant" --user-profile="4/6-projector"
```

### performance-evolution
Evolve performance characteristics over time
```
/adaptive-evolution performance-evolution "distributed-orchestrator" --optimize-for="latency"
```

## Options
- `--metric`: Performance metric to optimize
- `--generation-count`: Number of evolution generations (default: 10)
- `--mutation-rate`: Rate of mutation in evolution (0.0-1.0, default: 0.2)
- `--selection-pressure`: How strongly to select for fitness (default: 0.7)
- `--population-size`: Size of agent population (default: 20)

## Examples

```
# Evolve lead generator for better conversion
/adaptive-evolution agent-optimization "lead-generator" --metric="quality-score" --generation-count=20

# Expand SEO analyzer capabilities
/adaptive-evolution capability-expansion "seo-analyzer" --add-capability="competitor-analysis" --add-capability="keyword-research"

# Adapt to user's working style
/adaptive-evolution behavioral-adaptation "task-manager" --user-profile="splenic-projector" --work-hours="4-5"

# Optimize for speed
/adaptive-evolution performance-evolution "image-generator" --optimize-for="generation-speed" --constraint="quality>0.8"
```

## MCP Tools Used
- `mcp__adaptive-agent-evolution__start_evolution`
- `mcp__adaptive-agent-evolution__get_evolution_status`
- `mcp__adaptive-agent-evolution__apply_evolution`
- `mcp__adaptive-agent-evolution__rollback_evolution`
- `mcp__adaptive-agent-evolution__get_fitness_metrics`