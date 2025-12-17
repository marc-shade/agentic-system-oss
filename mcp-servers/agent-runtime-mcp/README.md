# Agent Runtime MCP Server - OSS Edition

Persistent task management for AI agents with goal decomposition, relay pipelines, and circuit breakers.

## Features

- **Goal Management**: Create and track high-level objectives
- **Task Decomposition**: Break goals into hierarchical tasks
- **Relay Pipelines**: 48-agent sequential execution with structured handoffs
- **Circuit Breakers**: Fault tolerance for agent failures

## Performance Targets

| Operation | Target | Tolerance |
|-----------|--------|-----------|
| Task Decomposition | 1200 ms | ±25% |
| Baton Handoff | 89 ms | ±50% |

## Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Test the server
python3 server.py
```

## Claude Code CLI Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "agent-runtime": {
      "command": "python3",
      "args": ["/path/to/mcp-servers/agent-runtime-mcp/server.py"]
    }
  }
}
```

## Available Tools

### Goals
- `create_goal` - Create persistent goals
- `get_goal` - Get goal details with tasks
- `list_goals` - List all goals

### Tasks
- `create_task` - Create manual tasks
- `decompose_goal` - AI task decomposition
- `get_next_task` - Get highest priority task
- `update_task_status` - Update task state
- `list_tasks` - List tasks with filters
- `get_task` - Get task details

### Relay Pipelines
- `create_relay_pipeline` - Create multi-agent pipeline
- `get_relay_status` - Pipeline progress
- `advance_relay` - Pass the baton
- `get_relay_baton` - Get handoff context
- `list_relay_pipelines` - List all pipelines

### Circuit Breakers
- `circuit_breaker_status` - Check agent health
- `circuit_breaker_record_failure` - Track failures
- `circuit_breaker_reset` - Reset circuit

## Architecture

```
┌─────────────────────────────────────────┐
│           Claude Code CLI               │
├─────────────────────────────────────────┤
│        MCP Protocol (stdio)             │
├─────────────────────────────────────────┤
│      Agent Runtime MCP Server           │
├──────────────┬──────────────────────────┤
│    Goals     │        Tasks             │
├──────────────┼──────────────────────────┤
│   Relay      │    Circuit               │
│  Pipelines   │    Breakers              │
├──────────────┴──────────────────────────┤
│            SQLite Backend               │
└─────────────────────────────────────────┘
```

## Relay Pipeline Flow

```
Agent 1 → Agent 2 → Agent 3 → ... → Agent N
   │         │         │              │
   └── Baton ┴── Baton ┴── Baton ────┘
        (context, quality score, L-score)
```

## License

MIT License - See LICENSE file in repository root.
