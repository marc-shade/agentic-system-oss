# CrewAI Orchestrator

Production-ready multi-agent orchestration for the agentic system using CrewAI framework.

## Installation

```bash
cd /Volumes/SSDRAID0/agentic-system/intelligent-agents/crewai_orchestrator
pip install -r requirements.txt
```

## Quick Start

```python
from crewai_orchestrator import CrewAIOrchestrator

orchestrator = CrewAIOrchestrator()

# Run development workflow
result = orchestrator.run_development(
    requirements="Implement a REST API with authentication",
    language="python"
)

# Run research workflow
result = orchestrator.run_research(
    topic="Best practices for distributed systems"
)

# Run optimization workflow
result = orchestrator.run_optimization(
    target="database query performance",
    goals=["reduce latency", "improve throughput"]
)
```

## Available Crews

### Development Crew
Full software development lifecycle with research, implementation, review, and documentation.

**Agents**: Researcher, Coder, Reviewer, Documenter

```python
orchestrator.run_development(
    requirements="Build a caching layer",
    language="python",
    include_docs=True
)
```

### Research Crew
Deep research and analysis on technical topics.

**Agents**: Researcher, Analyst

```python
orchestrator.run_research(
    topic="Machine learning optimization techniques",
    analysis_type="comprehensive"
)
```

### Optimization Crew
System and code optimization with analysis and validation.

**Agents**: Analyst, Coder, Reviewer

```python
orchestrator.run_optimization(
    target="API response times",
    goals=["reduce p99 latency", "improve cache hit rate"],
    constraints=["maintain backwards compatibility"]
)
```

## MCP Integration

The orchestrator integrates with:

- **enhanced-memory-mcp**: Knowledge persistence across sessions
- **agent-runtime-mcp**: Task persistence and tracking
- **voice-mode-mcp**: Status announcements

## CLI Usage

```bash
python -m crewai_orchestrator.orchestrator \
    --crew development \
    --input "Implement user authentication" \
    --output-dir ./output
```

## Configuration

Edit `config.yaml` to customize:

- Agent parameters (role, goals, backstory)
- Crew composition
- MCP integration settings
- Performance limits

## Architecture

```
crewai_orchestrator/
├── orchestrator.py      # Main entry point
├── tasks.py             # Reusable task definitions
├── tools.py             # MCP tool wrappers
├── agents/              # Agent definitions
│   ├── researcher.py
│   ├── coder.py
│   ├── reviewer.py
│   ├── documenter.py
│   └── analyst.py
└── crews/               # Pre-configured crews
    ├── development_crew.py
    ├── research_crew.py
    └── optimization_crew.py
```

## Performance Metrics

```python
# Get execution metrics
metrics = orchestrator.get_metrics()

# Get summary
summary = orchestrator.get_summary()
# Returns: total_runs, completed, failed, success_rate, average_execution_time
```
