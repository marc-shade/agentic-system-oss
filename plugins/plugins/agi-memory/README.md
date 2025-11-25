# AGI-Memory Plugin

Persistent AGI memory with SQLite for Claude Code.

## Overview

This plugin extends agi-core with persistent storage capabilities:
- **Goal Management**: Create, decompose, and track goals
- **Task Queue**: Priority-based task management with dependencies
- **Action Learning**: Record outcomes for meta-learning
- **Quality Conscience**: Ember ensures production readiness

## Requirements

- agi-core plugin installed
- Python 3.10+
- Node.js 16+ (for Ember)

## Installation

```bash
# Install plugin
/plugin install agi-memory@agentic-marketplace

# Run setup
~/.claude/plugins/agi-memory/scripts/setup.sh
```

## MCP Servers

### agent-runtime
Goal decomposition and task queue management.

**Tools:**
- `create_goal` - Create a new goal
- `decompose_goal` - Break goal into tasks
- `create_task` - Create manual task
- `get_next_task` - Get highest priority task
- `update_task_status` - Update task progress
- `list_goals` / `list_tasks` - View items

### agi
Meta-learning and self-improvement engine.

**Tools:**
- `agi_record_outcome` - Record task results for learning
- `agi_recommend_agent` - Get best agent for task type
- `agi_detect_patterns` - Find optimization opportunities
- `agi_get_learning_summary` - View learning stats
- `agi_register_skill` - Register skill for A/B testing
- `agi_start_ab_test` - Compare skill versions

### ember
Quality conscience keeper.

**Tools:**
- `ember_check_violation` - Check action for issues
- `ember_consult` - Get advice on decisions
- `ember_feed_context` - Provide work context
- `ember_get_feedback` - Get behavioral feedback
- `ember_learn_from_correction` - Teach Ember from mistakes

## Commands

### /agi-goals
View and manage goals and tasks.

### /agi-consolidate
Run memory consolidation to extract patterns from recent experiences.

## Configuration

Edit `~/.claude/agi/config.yaml`:

```yaml
tier: memory

memory:
  database_path: ~/.claude/agi/databases

behaviors:
  action_recording:
    enabled: true
    store_to_db: true  # Requires agi-memory
```

## Database Schema

Databases are stored in `~/.claude/agi/databases/`:

- `agent_runtime.db` - Goals and tasks
- `agi_mcp.db` - Outcomes, patterns, skills
- `ember.db` - Quality checks and learning

## Upgrade Path

Install agi-extended for:
- Vector-based semantic memory (Qdrant)
- Research paper integration
- Video transcript learning
- Voice interaction

```bash
/plugin install agi-extended@agentic-marketplace
```

## Troubleshooting

### Database errors
```bash
# Reinitialize databases
~/.claude/plugins/agi-memory/scripts/init-databases.py --db-dir ~/.claude/agi/databases
```

### MCP server not starting
```bash
# Check Python path
which python3

# Test server manually
python3 ~/.claude/plugins/agi-memory/mcp/agent-runtime/server.py
```

### Ember not working
```bash
# Build Ember
cd ~/.claude/plugins/agi-memory/mcp/ember
npm install
npm run build
```
