# Sequential Thinking MCP Server

Deep reasoning chains for complex problem-solving.

## Installation

Sequential Thinking is an npm package from the MCP community:

```bash
# Install globally
npm install -g @anthropics/mcp-server-sequential-thinking

# Or use npx directly (no installation)
npx @anthropics/mcp-server-sequential-thinking
```

## Claude Code CLI Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "sequential-thinking": {
      "command": "npx",
      "args": ["-y", "@anthropics/mcp-server-sequential-thinking"]
    }
  }
}
```

## Features

- Multi-step analysis with hypothesis generation
- Chain-of-thought reasoning
- Self-verification of conclusions
- Branching exploration paths

## Usage

The server provides the `sequentialthinking` tool for deep reasoning:

```
Parameters:
- thought: Current thinking step
- thoughtNumber: Current number in sequence
- totalThoughts: Estimated total thoughts needed
- nextThoughtNeeded: Whether more thinking is required
- isRevision: Whether this revises previous thinking
- needsMoreThoughts: If more analysis is needed
```

## Integration with Agentic System

Sequential Thinking integrates with the memory and task systems:

1. Reasoning chains are stored in semantic memory
2. Complex tasks trigger deep thinking automatically
3. Conclusions feed back into goal planning

## License

MIT License - See Anthropic MCP repository for details.
