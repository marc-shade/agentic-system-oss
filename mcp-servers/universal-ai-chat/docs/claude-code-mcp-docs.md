# Claude Code MCP Server Configuration Guide

> Source: https://code.claude.com/docs/en/mcp

## Overview
Claude Code connects to external tools through the Model Context Protocol (MCP), an open standard for AI-tool integrations. MCP servers provide access to databases, APIs, and tools.

## Installation Methods

### HTTP Servers (Recommended)
```bash
claude mcp add --transport http <name> <url>
claude mcp add --transport http notion https://mcp.notion.com/mcp
claude mcp add --transport http secure-api https://api.example.com/mcp \
  --header "Authorization: Bearer your-token"
```

### SSE Servers (Deprecated)
```bash
claude mcp add --transport sse <name> <url>
claude mcp add --transport sse asana https://mcp.asana.com/sse
```

### Local Stdio Servers
```bash
claude mcp add --transport stdio <name> -- <command> [args...]
claude mcp add --transport stdio airtable --env AIRTABLE_API_KEY=YOUR_KEY \
  -- npx -y airtable-mcp-server
```

**Note on double-dash:** "The `--` separates Claude's own CLI flags from the command and arguments that get passed to the MCP server."

## Configuration Scopes

### Local Scope (Default)
- Private to individual user in current project
- Stored in project-specific user settings
- Ideal for personal/experimental configurations

```bash
claude mcp add --transport http stripe https://mcp.stripe.com
```

### Project Scope
- Shared via `.mcp.json` at project root
- Checked into version control for team collaboration
- Requires approval before first use

```bash
claude mcp add --transport http paypal --scope project https://mcp.paypal.com/mcp
```

**Standard `.mcp.json` format:**
```json
{
  "mcpServers": {
    "shared-server": {
      "command": "/path/to/server",
      "args": [],
      "env": {}
    }
  }
}
```

### User Scope
- Available across all projects on your machine
- Remains private to your account
- Best for personal utilities

```bash
claude mcp add --transport http hubspot --scope user https://mcp.hubspot.com/anthropic
```

## Scope Precedence
When servers share names across scopes, priority is: **Local > Project > User**

## Environment Variable Expansion

`.mcp.json` supports variable expansion using `${VAR}` or `${VAR:-default}` syntax:

```json
{
  "mcpServers": {
    "api-server": {
      "type": "http",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

Expansion works in: `command`, `args`, `env`, `url`, and `headers` fields.

## OAuth Authentication

Many cloud-based servers require OAuth 2.0:

```bash
# Add server requiring authentication
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp

# Authenticate within Claude Code
> /mcp
```

"Authentication tokens are stored securely and refreshed automatically." Use the `/mcp` menu to manage and revoke access.

## JSON Configuration Method

```bash
claude mcp add-json weather-api \
  '{"type":"http","url":"https://api.weather.com/mcp","headers":{"Authorization":"Bearer token"}}'

claude mcp add-json local-weather \
  '{"type":"stdio","command":"/path/to/weather-cli","args":["--api-key","abc123"],"env":{"CACHE_DIR":"/tmp"}}'
```

## Management Commands

```bash
claude mcp list              # List all servers
claude mcp get github        # Get specific server details
claude mcp remove github     # Remove a server
/mcp                         # Check status within Claude Code
```

## Enterprise Configuration

System administrators can deploy centralized MCP configurations:

**Platform locations:**
- macOS: `/Library/Application Support/ClaudeCode/managed-mcp.json`
- Windows: `C:\ProgramData\ClaudeCode\managed-mcp.json`
- Linux: `/etc/claude-code/managed-mcp.json`

**Enterprise managed servers example:**
```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    },
    "company-internal": {
      "type": "stdio",
      "command": "/usr/local/bin/company-mcp-server",
      "args": ["--config", "/etc/company/mcp-config.json"],
      "env": {
        "COMPANY_API_URL": "https://internal.company.com"
      }
    }
  }
}
```

## Access Control

In `managed-settings.json`, administrators can restrict MCP server access:

```json
{
  "allowedMcpServers": [
    { "serverName": "github" },
    { "serverName": "sentry" }
  ],
  "deniedMcpServers": [
    { "serverName": "filesystem" }
  ]
}
```

## Claude Code as MCP Server

You can expose Claude Code's tools to other MCP clients:

```bash
claude mcp serve
```

Add to Claude Desktop's `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "claude-code": {
      "type": "stdio",
      "command": "/full/path/to/claude",
      "args": ["mcp", "serve"]
    }
  }
}
```

Find the executable path: `which claude`

## Output Management

- **Warning threshold:** 10,000 tokens
- **Default maximum:** 25,000 tokens
- **Configure:** `export MAX_MCP_OUTPUT_TOKENS=50000`

## Practical Examples

### Sentry Error Monitoring
```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
> /mcp  # Authenticate
> "What are the most common errors in the last 24 hours?"
```

### GitHub Integration
```bash
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
> /mcp  # Authenticate if needed
> "Review PR #456 and suggest improvements"
```

### PostgreSQL Database
```bash
claude mcp add --transport stdio db -- npx -y @bytebase/dbhub \
  --dsn "postgresql://readonly:pass@host:5432/analytics"
> "What's our total revenue this month?"
```

## Windows Considerations

Native Windows (non-WSL) requires `cmd /c` wrapper for `npx` commands:

```bash
claude mcp add --transport stdio my-server -- cmd /c npx -y @some/package
```

## Cross-Platform Integration

Claude Code can communicate with other AI CLIs via shared MCP servers:
- OpenAI Codex CLI (via universal-ai-chat MCP)
- Gemini CLI (via universal-ai-chat MCP)
- Custom agents (via any MCP-compatible client)

## Key Files

- User config: `~/.claude.json`
- Project config: `.mcp.json` in project root
- Enterprise config: `/etc/claude-code/managed-mcp.json` (Linux)
