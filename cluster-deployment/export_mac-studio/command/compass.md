# COMPASS Mission Command

Execute complex, long-horizon tasks using Google's COMPASS framework with three-agent hierarchy and two-loop architecture.

## Usage

```bash
/compass [task description]
```

## What is COMPASS?

**COMPASS** = **CO**gnitive **M**anagement for **P**ersistent **A**gent **S**ystem**S**

A three-agent framework that solves the "context crisis" in long-horizon AI tasks:

```
        COMPASS Orchestrator
              |
    +---------+---------+
    |         |         |
Main Agent | Meta    | Context
(Worker)   | Thinker | Manager
```

### The Problem COMPASS Solves

- **Context Overload**: After 20-30 steps, context becomes chaotic (10K-100K tokens)
- **Looping**: Agents repeat failed approaches indefinitely
- **Constraint Drift**: Forgetting original requirements
- **Wasted Execution**: Continuing when stuck or already complete

### The COMPASS Solution

1. **Context Manager**: Compresses full history into concise briefs (10-50x compression)
2. **Meta Thinker**: Detects loops, drift, and completion (strategic oversight)
3. **Main Agent**: Executes with focused context (one tool at a time)
4. **Two-Loop Architecture**: Fast tactical execution + strategic oversight

## Task Description

Provide a clear, detailed description of your complex task:

**Good Examples**:
- "Implement user authentication system with JWT tokens, bcrypt password hashing, refresh token rotation, and rate limiting"
- "Research and compare top 5 authentication libraries, create comparison matrix with pros/cons, and recommend best option with justification"
- "Refactor the API layer to use async/await, add comprehensive error handling, implement request/response logging, and create unit tests"

**Less Effective**:
- "Build auth" (too vague)
- "Fix the bug" (not specific enough)
- "Make it better" (no clear objective)

## What You Get

### Real-Time Coordination

Every turn includes:
- **Meta Thinker Analysis**: Continue/Pivot/Verify/Terminate signal
- **Context Brief**: Concise (500-2K token) execution guidance
- **Main Agent Execution**: Focused single-step progress
- **Performance Metrics**: Compression ratio, detection latency, progress

### Strategic Oversight

- **Anomaly Detection**: Loops detected in 2-3 turns
- **Constraint Adherence**: 100% requirement compliance
- **Smart Pivots**: Course corrections when needed
- **Clean Completion**: Accurate termination detection

### Persistence

All mission data stored for analysis:
- Turn-by-turn execution logs
- Context briefs and meta signals
- Pivot decisions and rationale
- Success patterns for future learning

## Example Execution

```bash
$ /compass "Implement JWT authentication with refresh tokens"

🧭 COMPASS Orchestrator: Mission initialized
   - Goal: JWT authentication implementation
   - Main Agent: Swarm Coder
   - Estimated: 30-40 turns

Turn 1:
   🧭 Meta Thinker: Continue (0.90 confidence)
   🧭 Context Manager: Brief synthesized (compression: 25x)
   🧭 Swarm Coder: Created User model with email/password fields

Turn 2:
   🧭 Meta Thinker: Continue (0.91 confidence)
   🧭 Context Manager: Brief synthesized (compression: 22x)
   🧭 Swarm Coder: Installed bcrypt, implemented password hashing

...

Turn 19:
   🧭 Meta Thinker: PIVOT (0.93 confidence) - Loop detected
      Reasoning: 3 failed attempts at refresh token rotation
      Recommendation: Simplify - implement basic refresh first
   🧭 Context Manager: Adapted brief with simplified approach
   🧭 Swarm Coder: Implementing basic refresh token logic

...

Turn 42:
   🧭 Meta Thinker: TERMINATE (0.96 confidence) - Task complete
   🧭 Mission Summary:
      - Total turns: 42
      - Pivots: 2
      - Context compression: 18x average
      - Constraint adherence: 100%
      - Success factors: Early pivot, systematic breakdown

✅ Mission completed successfully
```

## When to Use COMPASS

**Perfect For**:
- Complex implementations (30+ steps)
- Multi-file refactoring
- Research with synthesis
- Long debugging sessions
- Feature development with dependencies
- Any task where you've hit loops or drift

**Not Needed For**:
- Simple single-file edits
- Quick questions or explanations
- Straightforward tasks (<10 steps)
- Tasks better suited for specialized agents

## Integration with Existing Tools

COMPASS works alongside your ecosystem:

- **BMAD Method**: Use COMPASS for Phase 2 (Implementation)
- **Swarm Coordinator**: Orchestrate multiple COMPASS missions in parallel
- **AIME Coordinator**: Use COMPASS for tactical execution of strategic plans
- **Voice Mode**: Get real-time audio updates on pivots and completion

## Performance Expectations

| Metric | Improvement |
|--------|-------------|
| Context Size | 10-50x compression |
| Anomaly Detection | 2-3 turns (vs never) |
| Long-Horizon Success | 3-5x higher |
| Constraint Adherence | 100% (zero drift) |

## Storage Location

Mission data stored at:
```
/Volumes/SSDRAID0/agentic-system/agent-memory/compass-contexts/
```

Each mission includes:
- Turn-by-turn execution logs
- Context briefs and meta signals
- Performance metrics
- Success patterns

## Technical Details

- **Framework**: Google COMPASS (Oct 2025)
- **Agents**: 3 (Context Manager, Meta Thinker, Orchestrator)
- **MCP Integration**: enhanced-memory, sequential-thinking
- **Storage**: Hot tier (SSDRAID0) for performance
- **Status**: Production Ready

---

**Ready to Execute?**

Just provide your complex task description, and COMPASS will handle the rest through strategic context management and tactical execution.

The framework that transforms impossible long-horizon tasks into focused, successful missions.
