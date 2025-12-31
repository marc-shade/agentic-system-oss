# Claude Code 2025 Feature Integration

This document tracks the integration of Claude Code 2.0+ features into the agentic system.

## Current Version: 2.0.74

## Newly Integrated Features

### 1. Enhanced Hooks System (9 Event Types)

**Previously Active (5):**
- `SessionStart` - Load context at session start
- `SessionEnd` - Cleanup and analytics
- `PreToolUse` - Pre-execution validation
- `PostToolUse` - Post-execution processing
- `SubagentStop` - Subagent completion handling

**Newly Added (3):**
- `PreCompact` - Context preservation before compaction (`~/.claude/hooks/pre-compact.py`)
- `PermissionRequest` - Intelligent auto-approval (`~/.claude/hooks/permission-request.py`)
- `UserPromptSubmit` - Prompt augmentation (`~/.claude/hooks/user-prompt-submit.py`)

**Configuration Location:** `~/.claude/settings.local.json`

### 2. Checkpoint & Session Management

**New Commands:**
- `/checkpoint` - Create, list, restore session checkpoints
- `/fork` - Fork session for parallel exploration
- `/rewind` - Quick undo of recent changes (built-in)

**Features Leveraged:**
- Session forking with `--fork-session --session-id`
- Named sessions with `/rename`
- Resume with `--resume`

### 3. Background Agent System

**Existing Commands (from background-agents skill):**
- `/bg-start` - Start background agent
- `/bg-status` - Check background tasks
- `/bg-worktree` - Create git worktree
- `/bg-parallel` - Run parallel reviews
- `/bg-cleanup` - Clean up worktrees

**Key Patterns:**
- `Ctrl+B` - Push current agent to background
- `/tasks` - List all running/completed tasks
- `run_in_background=true` - Task tool parameter

### 4. MCP Server Enhancements

**Active Servers (12):**
1. enhanced-memory - 4-tier memory with RAG
2. voice-mode - TTS/STT communication
3. sequential-thinking - Deep reasoning
4. chrome-devtools - Browser automation
5. arduino-surface - Physical hardware interface
6. ember-mcp - Quality enforcement
7. agent-runtime-mcp - Persistent tasks
8. cluster-execution-mcp - Distributed execution
9. node-chat-mcp - Inter-node communication
10. safla-mcp - Hybrid memory (1.75M+ ops/sec)
11. research-paper-mcp - Academic research
12. video-transcript-mcp - YouTube extraction

**Wildcard Permissions Pattern:**
```
mcp__enhanced-memory__*  # All enhanced-memory tools
mcp__agent-runtime-mcp__* # All agent-runtime tools
```

### 5. Permission Auto-Approval System

**Trusted Patterns (automatic approval):**
- Reads from agentic-system paths
- Writes to agentic-system paths (excluding .env, credentials)
- Safe bash commands (ls, cat, git status, etc.)
- All trusted MCP servers

**Blocked Patterns (automatic denial):**
- `rm -rf /`
- Fork bombs
- Curl/wget piped to shell
- dd to /dev/sd*

### 6. Context Management

**PreCompact Hook:**
- Preserves critical context before compaction
- Logs compaction events for analysis
- Stores preserved context in `~/.claude/preserved_context.json`

**UserPromptSubmit Hook:**
- Adds relevant context based on prompt keywords
- Injects system reminders (production-only policy, etc.)
- Logs prompts for pattern analysis

## Usage Patterns

### Parallel Development Workflow

```bash
# Fork for exploration
/fork approach-a "Test REST design"

# Background tasks
/bg-parallel security performance quality

# Monitor progress
/bg-status

# Compare and merge
/checkpoint create pre-merge
```

### Safe Experimentation

```bash
# Create checkpoint before risky changes
/checkpoint create pre-experiment

# Make experimental changes
...

# If things go wrong
/checkpoint rewind
# or
/checkpoint restore pre-experiment
```

### Distributed Execution

```python
# Use cluster-execution-mcp
mcp__cluster-execution-mcp__cluster_bash(command="make build")

# Or Python API
from cluster_offload import offload
result = offload("pytest tests/")
```

## File Locations

| File | Purpose |
|------|---------|
| `~/.claude/settings.local.json` | Hook configuration |
| `~/.claude/hooks/pre-compact.py` | PreCompact hook |
| `~/.claude/hooks/permission-request.py` | PermissionRequest hook |
| `~/.claude/hooks/user-prompt-submit.py` | UserPromptSubmit hook |
| `~/.claude/commands/checkpoint.md` | Checkpoint command |
| `~/.claude/commands/fork.md` | Fork command |
| `~/.claude/compaction_log.jsonl` | Compaction event log |
| `~/.claude/permission_log.jsonl` | Permission decision log |
| `~/.claude/prompt_log.jsonl` | Prompt pattern log |

## Upcoming Considerations

### Plugin Marketplace
- `/plugin install` - Install from marketplace
- `/plugin marketplace` - Browse available plugins
- Auto-updates for installed plugins

### Prompt-Based Hooks
For complex decisions requiring AI reasoning:
```json
{
  "type": "prompt",
  "prompt": "Evaluate if this operation is safe given the context..."
}
```

### Enterprise Features
- Managed settings for organizational policies
- MCP allowlist/denylist at enterprise level
- `allowManagedHooksOnly` for security

## Integration with Existing System

### AGI Orchestrator
Background agents work seamlessly with the 6-phase AGI workflow:
1. Goal Decomposition (can spawn parallel subagents)
2. Context Synthesis (leverages PreCompact for preservation)
3. Multi-Agent Coordination (background agents)
4. Meta-Learning (logged in enhanced-memory)
5. Skill Evolution (checkpoints for A/B testing)
6. Darwin Godel (safe experimentation with /fork)

### Cluster Deployment
Session forking enables parallel exploration across cluster nodes:
- Fork → Execute on different nodes → Compare results
- Background agents for parallel research
- Checkpoints before distributed operations

## Exo Distributed Inference

**Status**: Configured and running on localhost:8000

**Available Models**: 73 (including DeepSeek R1, Llama 3.x, Qwen 2.5)

**MCP Integration**:
- `exo_models` - List available models
- `exo_status` - Get cluster status (uses fallback for OpenAI-compatible API)
- `exo_load_model` - Load a model into the cluster
- `exo_chat` - Run inference on loaded model

**Usage** (no loading required - just call directly):
```python
# List available models
mcp__exo-inference-mcp__exo_models()

# Run inference (no loading step needed)
mcp__exo-inference-mcp__exo_chat(
    messages=[{"role": "user", "content": "Hello!"}],
    model="llama-3.2-1b"
)

# With system prompt
mcp__exo-inference-mcp__exo_chat(
    messages=[
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Explain X"}
    ],
    model="llama-3.2-1b",
    temperature=0.7,
    max_tokens=500
)
```

## Changelog

- **2025-12-19**: Initial integration of Claude Code 2.0.74 features
  - Added PreCompact, PermissionRequest, UserPromptSubmit hooks
  - Created /checkpoint and /fork commands
  - Documented background agent patterns
  - Set up permission auto-approval system
  - Fixed exo-inference-mcp status tool for OpenAI-compatible API
  - Verified Exo running with 73 models available
