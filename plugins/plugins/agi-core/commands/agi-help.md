---
description: Detailed help for AGI plugin features and usage
---

# AGI Plugin Help

## Overview

The AGI plugin system provides enhanced reasoning capabilities through specialized agents, behavioral patterns, and thinking modes.

## Using Specialized Agents

### @deep-thinker
**Best for**: Complex algorithms, novel problems, multi-step reasoning

```
@deep-thinker How can we optimize this recursive function that's
causing stack overflow on large inputs?
```

### @architect
**Best for**: System design, architecture decisions, planning

```
@architect Design a caching layer for our API that handles
10k requests/second with <10ms latency.
```

### @code-reviewer
**Best for**: Code quality, security review, best practices

```
@code-reviewer Review the authentication module for security
vulnerabilities and code quality issues.
```

### @debugger
**Best for**: Bug investigation, root cause analysis

```
@debugger The application crashes randomly under load. Memory
usage spikes before crash. Help investigate.
```

### @researcher
**Best for**: Technical research, knowledge synthesis

```
@researcher Research state-of-the-art approaches for real-time
recommendation systems handling millions of users.
```

## Thinking Modes

### Standard Mode (Default)
Normal conversational analysis.

### Deep Thinking
Trigger: Include "think" or "think harder" in your request.
```
Think through how we should structure this microservices migration.
```

### Ultra Thinking
Trigger: Include "ultrathink" in your request.
```
Ultrathink about the trade-offs between eventual consistency and
strong consistency for our distributed system.
```

## Behavioral Patterns

### Action Outcome Recording
For significant actions, I track:
- What was attempted and why
- Expected vs actual outcome
- Lessons for future similar situations

### Knowledge Gap Identification
When I encounter unfamiliar territory:
- I explicitly note what I don't know
- I state assumptions clearly
- I research when gaps are critical

### Meta-Prompting Workflow
For complex tasks, I:
1. Ask clarifying questions first
2. Break down into manageable steps
3. Plan the approach
4. Execute with verification at each step

### Metacognitive Monitoring
I continuously track:
- Confidence in my analysis
- Whether the current approach is working
- Complexity of the task
- When to seek help or change strategy

## Best Practices

### For Complex Problems
1. Start with `@deep-thinker` for initial analysis
2. Use `@architect` for system-level decisions
3. Use `@code-reviewer` before finalizing code
4. Document decisions and reasoning

### For Research Tasks
1. Start with `@researcher` for background
2. Use "ultrathink" for synthesis
3. Document findings systematically
4. Note gaps for future research

### For Debugging
1. Start with `@debugger` for systematic investigation
2. Use `@deep-thinker` for complex root cause analysis
3. Use `@code-reviewer` to verify fix quality
4. Document the bug pattern for future reference

## Plugin Tiers

### Tier 1: agi-core (Current)
- Specialized agents
- Behavioral patterns
- Thinking modes
- No infrastructure required

### Tier 2: agi-memory
Adds: SQLite persistence, goals, tasks, outcome recording
Requires: Python 3.10+

### Tier 3: agi-extended
Adds: Vector memory, research paper tools, video learning, voice
Requires: Docker, Qdrant

### Tier 4: agi-cluster
Adds: Multi-node distribution, inter-node communication
Requires: Multiple machines, SSH access

## Troubleshooting

### Agent Not Responding as Expected
- Ensure you're using the exact agent name (e.g., `@deep-thinker`)
- Try being more specific in your request
- Consider if a different agent is more appropriate

### Thinking Mode Not Activating
- Include the trigger word naturally in your request
- "think" or "think harder" for deep mode
- "ultrathink" for maximum depth

## Getting More Help

- Plugin documentation: Check the plugin's README
- Community: [GitHub Issues](https://github.com/your-org/agi-plugins)
- Upgrade: Install higher tier plugins for more capabilities

---

*AGI-Core v1.0.0 - Making Claude smarter through structured reasoning*
