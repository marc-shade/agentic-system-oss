---
description: Distribute tasks across the AGI cluster
---

# Distributed Task Execution

Execute tasks across the AGI cluster with intelligent routing.

## Task Routing

Tasks are automatically routed to the best node based on:
- Task type (code, research, coordination)
- Node capabilities
- Current load
- Hardware requirements

## Routing Rules

| Task Type | Primary Node | Fallback |
|-----------|--------------|----------|
| Code Generation | macpro51 (Builder) | mac-studio |
| Research | macbook-air-m3 (Researcher) | mac-studio |
| Security Scan | macpro51 (Builder) | - |
| Coordination | mac-studio (Orchestrator) | - |

## Task Commands

### Decompose Goal
Break a high-level goal into node-specific tasks:
```
mcp__node-chat__decompose_goal --goal "<goal description>"
```

### Start Research Pipeline
Autonomous research-to-implementation:
```
mcp__node-chat__initiate_research_pipeline --research_topic "<topic>"
```

### Improvement Cycle
Distributed self-improvement:
```
mcp__node-chat__start_improvement_cycle --target_metric "<metric>"
```

## Claude Flow Orchestration

For complex multi-agent tasks:

### Initialize Swarm
```
mcp__claude-flow__swarm_init --topology hierarchical
```

### Spawn Agents
```
mcp__claude-flow__agent_spawn --type coordinator --name "task-coord"
```

### Orchestrate Task
```
mcp__claude-flow__task_orchestrate --task "<task>" --strategy parallel
```

## Example Workflows

### Distributed Code Review
1. Decompose: Split code review across nodes
2. Builder: Security and performance analysis
3. Researcher: Best practices research
4. Orchestrator: Synthesize findings

### Research-to-Implementation
1. Researcher: Find relevant papers
2. Orchestrator: Evaluate applicability
3. Builder: Implement if approved
4. All: Store learnings

## Usage

Describe the task you want to distribute, or choose:
1. **Decompose a goal** - Break into node tasks
2. **Start research** - Autonomous research flow
3. **Improve capability** - Self-improvement cycle

---

*Distributed execution powered by node-chat-mcp and claude-flow*
