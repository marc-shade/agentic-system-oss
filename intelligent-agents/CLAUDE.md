# Intelligent Agents - Context

**Location:** `/mnt/agentic-system/intelligent-agents/`
**Purpose:** Core Python agents for AGI development

## Architecture Overview

```
Orchestration:
  agi_orchestrator.py          - Main coordination (START HERE)
  multi_agent_coordinator.py   - Agent communication

Self-Improvement:
  darwin_godel_machine.py      - Recursive self-modification
  auto_implementation_engine.py - Code generation
  autonomous_improvement_daemon.py - Continuous improvement

Support:
  sandbox_testing_environment.py - Safe execution
  self_evaluation_system.py      - Quality metrics
  knowledge_synthesis_engine.py  - Learning integration
```

## Key Patterns

All agents follow patterns in `agentic_patterns.py` (85KB, comprehensive):
- Action selection
- Memory integration
- Error handling
- Logging conventions

## Creating a New Agent

1. **Use Existing Patterns:**
```python
from agentic_patterns import (
    ReflectionPattern,      # Self-evaluation
    PlanningPattern,        # Multi-step planning
    ToolUsePattern,         # External tool integration
    ReActPattern,           # Reasoning + Acting
    MetaPromptingPattern,   # Dynamic prompting
)

# Example: Create a reflection-based agent
pattern = ReflectionPattern(name="my_agent", max_iterations=3)
result = await pattern.execute(context={"task": "analyze code"})
```

2. **Register if Production:**
Add to `agi_orchestrator.py` agent registry

## Important Files

| File | Lines | Purpose |
|------|-------|---------|
| `agi_orchestrator.py` | 1-500 | Main loop, agent dispatch |
| `agentic_patterns.py` | 1-2000+ | Pattern library (20+ patterns) |
| `action_orchestrator.py` | - | Voice action orchestration |

## Testing

```bash
cd /mnt/agentic-system
source .venv/bin/activate
python -m pytest intelligent-agents/tests/
```

## Safety Notes

- Sandbox REQUIRED for new code execution
- Git rollback enabled by default
- Never modify `agi_orchestrator.py` without testing
