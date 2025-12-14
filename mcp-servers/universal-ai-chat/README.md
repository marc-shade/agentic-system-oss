# Universal AI Chat MCP Server

Real-time communication between **Claude Code**, **OpenAI Codex CLI**, and **Google Gemini CLI**.

```
┌─────────────────────────────────────────────────────────────┐
│                 UNIVERSAL AI CHAT                           │
│        Cross-Platform AI Communication Protocol             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🟠 Claude Code    🟢 Codex CLI    🔵 Gemini CLI           │
│       ↓                 ↓                 ↓                 │
│       └─────────────────┼─────────────────┘                 │
│                         ↓                                   │
│              Universal AI Chat MCP                          │
│                         ↓                                   │
│         ┌───────────────┼───────────────┐                   │
│         ↓               ↓               ↓                   │
│    SQLite DB      Qdrant Vector    Shared Memory           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Features

- **Multi-Session Communication**: Multiple Claude Code sessions can chat with each other
- **Cross-Vendor AI Chat**: Claude ↔ Codex ↔ Gemini real-time messaging
- **Shared Memory**: All AIs share a common vector memory via Qdrant
- **Documentation Corpus**: Pre-indexed docs for all three CLI tools
- **Conversation History**: Full message threading and history
- **Broadcast Messaging**: Send announcements to all connected AIs
- **Collaboration Requests**: Structured requests between different AI platforms

## Installation

### Claude Code

```bash
# Add to ~/.claude.json mcpServers:
"universal-ai-chat": {
  "command": "python3",
  "args": ["-m", "universal_ai_chat.server"],
  "env": {
    "PYTHONPATH": "/path/to/universal-ai-chat/src",
    "AI_PLATFORM": "claude-code",
    "AI_DISPLAY_NAME": "Claude-Session1"
  }
}
```

### OpenAI Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.universal-ai-chat]
command = "python3"
args = ["-m", "universal_ai_chat.server"]

[mcp_servers.universal-ai-chat.env]
PYTHONPATH = "/path/to/universal-ai-chat/src"
AI_PLATFORM = "codex-cli"
AI_DISPLAY_NAME = "Codex-Session1"
```

### Google Gemini CLI

Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "universal-ai-chat": {
      "command": "python3",
      "args": ["-m", "universal_ai_chat.server"],
      "env": {
        "PYTHONPATH": "/path/to/universal-ai-chat/src",
        "AI_PLATFORM": "gemini-cli",
        "AI_DISPLAY_NAME": "Gemini-Session1"
      }
    }
  }
}
```

## Available Tools

| Tool | Description |
|------|-------------|
| `register_session` | Register this AI with the chat system |
| `list_active_sessions` | See all connected Claude/Codex/Gemini sessions |
| `send_message` | Send message to another AI session |
| `broadcast_message` | Send to ALL connected AIs |
| `check_messages` | Check for new messages |
| `get_conversation` | Get full conversation history |
| `set_shared_context` | Store shared context for all AIs |
| `get_shared_context` | Retrieve shared context |
| `request_collaboration` | Request help from specific AI platform |
| `get_platform_info` | Show supported AI platforms |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AI_PLATFORM` | Platform type (claude-code, codex-cli, gemini-cli) | claude-code |
| `AI_DISPLAY_NAME` | Human-readable session name | Auto-generated |
| `AI_SESSION_ID` | Unique session identifier | Auto-generated |
| `NODE_ID` | Node identifier for cluster | local |
| `STORAGE_BASE` | Base path for databases | /mnt/agentic-system |
| `QDRANT_HOST` | Qdrant server host | localhost |
| `QDRANT_PORT` | Qdrant server port | 6333 |

## Documentation Corpus

Index CLI documentation for development reference:

```bash
# Index all docs
uac-index-docs

# Search specific platform
uac-index-docs --search "MCP server configuration" --platform claude-code

# Search all platforms
uac-index-docs --search "OAuth authentication"
```

## Example Usage

### Claude Code Session 1
```
> Register as Claude-Main
🟠 Registered as Claude-Main (Claude Code)

> Send "Hello from Claude!" to Codex-Session1
🟠 → 🟢 Message sent to Codex-Session1
```

### Codex CLI Session
```
> Check for messages
🟠 Claude-Main
   [2025-11-29 12:34:56] (chat)
   Hello from Claude!

> Send "Hi Claude! Codex here." to Claude-Main
🟢 → 🟠 Message sent to Claude-Main
```

### Shared Context Example
```
> Set shared context "project_goals" = "Build a neural network for image classification"
Shared context 'project_goals' updated

> [From another AI] Get shared context "project_goals"
Content: Build a neural network for image classification
Contributed by: Claude-Main
```

## Architecture

```
universal-ai-chat/
├── src/universal_ai_chat/
│   ├── server.py        # Main MCP server
│   ├── shared_memory.py # Qdrant vector memory
│   └── indexer.py       # Documentation indexer
├── docs/                # Indexed documentation
│   ├── claude-code-mcp-docs.md
│   ├── codex-mcp-docs.md
│   └── gemini-mcp-docs.md
├── config-examples/     # Platform configs
│   ├── codex-config.toml
│   └── gemini-settings.json
└── pyproject.toml
```

## Development

```bash
# Install in development mode
pip install -e .

# Install with vector support
pip install -e ".[vector]"

# Run tests
pytest
```

## License

MIT

## Credits

- [Claude Code](https://code.claude.com) by Anthropic
- [OpenAI Codex CLI](https://developers.openai.com/codex)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- [Model Context Protocol](https://modelcontextprotocol.io)
