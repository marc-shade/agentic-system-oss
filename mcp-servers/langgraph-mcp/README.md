# LangGraph MCP Server

Production-ready LangGraph integration for stateful agent workflows with persistence and human-in-the-loop capabilities.

## Features

- **Durable Agent Execution**: Checkpointing with automatic resume from failure
- **State Persistence**: SQLite-backed state storage at `databases/langgraph/`
- **Human Approval Workflows**: Integrated with Arduino Surface MCP for physical confirmation
- **Memory Management**: Short-term and long-term memory per thread
- **Graph Templates**: Research, code review, and autonomous task agents

## Installation

```bash
cd /Volumes/SSDRAID0/agentic-system/mcp-servers/langgraph-mcp
pip install -r requirements.txt
```

## MCP Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "langgraph-mcp": {
      "command": "python",
      "args": ["/Volumes/SSDRAID0/agentic-system/mcp-servers/langgraph-mcp/server.py"],
      "env": {
        "ANTHROPIC_API_KEY": "your-key"
      }
    }
  }
}
```

## Available Tools

### Graph Execution

| Tool | Description |
|------|-------------|
| `langgraph_run_research` | Multi-step research with source tracking |
| `langgraph_run_code_review` | Iterative code review with improvements |
| `langgraph_run_task` | Autonomous task completion |
| `langgraph_resume` | Resume paused/interrupted execution |

### State Management

| Tool | Description |
|------|-------------|
| `langgraph_list_checkpoints` | List all checkpoints for a thread |
| `langgraph_get_state` | Get current state of execution |
| `langgraph_visualize` | Generate graph structure visualization |

### Human-in-the-Loop

| Tool | Description |
|------|-------------|
| `langgraph_request_approval` | Request human approval (with Arduino) |
| `langgraph_list_pending_approvals` | List pending approvals |
| `langgraph_resolve_approval` | Resolve an approval request |

### Memory

| Tool | Description |
|------|-------------|
| `langgraph_save_memory` | Save memory entry |
| `langgraph_get_memories` | Retrieve memories for thread |

## Graph Templates

### Research Agent (`research_agent.py`)
Multi-step research workflow:
1. Plan research questions
2. Gather sources iteratively
3. Analyze findings
4. Synthesize report with citations

### Code Review Agent (`code_review_agent.py`)
Iterative code improvement:
1. Analyze code for issues
2. Suggest improvements
3. Apply improvements
4. Re-analyze (up to N iterations)

### Autonomous Task Agent (`autonomous_task.py`)
Self-directing task completion:
1. Plan steps from objective
2. Execute steps sequentially
3. Evaluate progress
4. Replan or complete

## Arduino Surface Integration

Physical approval workflow:
1. Message displayed on LCD
2. LED turns yellow (waiting)
3. Beep alerts user
4. User presses green (approve) or red (reject) button
5. LED changes to result color

Falls back to database-based approval if Arduino unavailable.

## Database Schema

Located at `/Volumes/SSDRAID0/agentic-system/databases/langgraph/state.db`:

- `graph_states`: Checkpoint storage
- `memory_store`: Thread memories
- `human_approvals`: Approval requests

## Integration with Enhanced Memory MCP

Store long-term learnings in enhanced-memory:

```python
# After research completion
mcp__enhanced-memory-mcp__create_entities([{
    "name": f"research-{thread_id}",
    "entityType": "research_outcome",
    "observations": [result["synthesis"]]
}])
```
