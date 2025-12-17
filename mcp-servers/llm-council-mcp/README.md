# LLM Council MCP Server

Multi-provider LLM deliberation system exposed via Model Context Protocol (MCP).

## Overview

LLM Council enables sophisticated multi-model deliberation where multiple LLMs collaboratively answer questions through a 3-stage process:

1. **Stage 1 (Collect)**: All council models independently respond to the question
2. **Stage 2 (Rank)**: Models anonymously evaluate and rank each other's responses
3. **Stage 3 (Synthesize)**: Chairman model synthesizes the final answer

The key innovation is **anonymized peer review** in Stage 2, which prevents models from playing favorites.

## Features

- **3-Stage Deliberation**: Collect → Rank → Synthesize
- **9 Deliberation Patterns**: debate, socratic, red_team, tree_of_thought, and more
- **Multi-Provider Support**: Claude Code, Codex CLI, Gemini CLI
- **Anonymized Ranking**: Prevents model bias in peer evaluation
- **Parallel Execution**: Fast response collection

## Installation

```bash
pip install .

# Or with OpenRouter support
pip install ".[openrouter]"
```

## Prerequisites

Install at least one CLI tool:

- **Claude Code**: `npm install -g @anthropic-ai/claude-code`
- **Codex CLI**: `npm install -g codex-cli`
- **Gemini CLI**: `pip install gemini-cli`

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PROVIDER_MODE` | `cli` | `cli` or `openrouter` |
| `CLI_COUNCIL_MODELS` | `claude,codex,gemini` | Comma-separated providers |
| `CLI_CHAIRMAN_MODEL` | `codex` | Model for final synthesis |
| `LLM_COUNCIL_DATA_DIR` | `~/.llm-council` | Data storage directory |
| `CLAUDE_TIMEOUT` | `120` | Claude CLI timeout (seconds) |
| `CODEX_TIMEOUT` | `120` | Codex CLI timeout (seconds) |
| `GEMINI_TIMEOUT` | `120` | Gemini CLI timeout (seconds) |

## MCP Tools

### council_deliberate

Run full 3-stage deliberation on a question.

```json
{
  "question": "What is the best programming language for beginners?",
  "save": true
}
```

### council_quick_query

Query a single provider for fast response.

```json
{
  "provider": "claude",
  "prompt": "Explain recursion",
  "timeout": 60
}
```

### council_get_providers

List available CLI providers and current configuration.

### council_list_patterns

List all 9 deliberation patterns with descriptions.

### council_run_pattern

Run a specific deliberation pattern.

```json
{
  "pattern": "debate",
  "question": "Should AI be regulated?",
  "rounds": 2
}
```

**Available patterns:**
- `deliberation` - Standard 3-stage process
- `debate` - Adversarial debate between models
- `devils_advocate` - One model challenges consensus
- `socratic` - Progressive questioning dialogue
- `red_team` - Security/flaw focused analysis
- `tree_of_thought` - Explore multiple solution branches
- `self_consistency` - Multiple attempts, majority vote
- `round_robin` - Sequential refinement
- `expert_panel` - Domain-specific expert roles

### council_compare_providers

Compare all providers on the same prompt.

```json
{
  "prompt": "Write a haiku about programming"
}
```

## Usage with Claude Code

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "llm-council": {
      "command": "python3",
      "args": ["/path/to/llm-council-mcp/server.py"]
    }
  }
}
```

## Example Session

```
User: Compare the responses of different AI models on climate change solutions

Claude: I'll use the council to deliberate on this question.

[Uses council_deliberate tool]

Stage 1: Collected responses from Claude, Codex, and Gemini
Stage 2: Models ranked each other (anonymized)
  - Response B ranked highest (avg: 1.3)
  - Response A ranked second (avg: 2.0)
  - Response C ranked third (avg: 2.7)
Stage 3: Chairman synthesized comprehensive answer...
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Council MCP Server                    │
├─────────────────────────────────────────────────────────────┤
│  server.py          MCP interface and tool definitions      │
├─────────────────────────────────────────────────────────────┤
│  backend/                                                    │
│  ├── config.py      Environment-based configuration         │
│  ├── council.py     3-stage deliberation logic              │
│  ├── cli_providers.py  Async CLI subprocess wrappers        │
│  └── patterns.py    9 deliberation pattern implementations  │
├─────────────────────────────────────────────────────────────┤
│  CLI Providers                                               │
│  ├── Claude Code    claude -p "prompt" --print              │
│  ├── Codex CLI      codex "prompt"                          │
│  └── Gemini CLI     gemini -p "prompt"                      │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

```
User Question
     │
     ▼
┌─────────────────┐
│   Stage 1       │  Parallel queries to all council models
│   Collect       │  → [claude_response, codex_response, gemini_response]
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Stage 2       │  Anonymize as Response A, B, C
│   Rank          │  Models evaluate and rank peers
│                 │  → Rankings + label_to_model mapping
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Aggregate     │  Calculate average rank positions
│   Rankings      │  → Sorted list by quality
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Stage 3       │  Chairman synthesizes final answer
│   Synthesize    │  Using ranked responses + context
└────────┬────────┘
         │
         ▼
    Final Answer
```

## License

MIT License
