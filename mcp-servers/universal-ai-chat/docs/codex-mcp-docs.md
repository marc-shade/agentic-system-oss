# OpenAI Codex MCP Configuration Guide

> Source: https://developers.openai.com/codex/mcp/

## Overview

The Model Context Protocol (MCP) enables Codex to access third-party tools and contextual information. Configuration applies to both the Codex CLI and IDE extension through the `~/.codex/config.toml` file.

## Configuration Methods

### CLI-Based Setup

Add MCP servers using:
```bash
codex mcp add <server-name> --env VAR1=VALUE1 --env VAR2=VALUE2 -- <command>
```

Example with Context7:
```bash
codex mcp add context7 -- npx -y @upstash/context7-mcp
```

View active servers in the Terminal UI with `/mcp`.

### Direct Config File Editing

Modify `~/.codex/config.toml` for granular control. The IDE extension provides access via the settings gear icon → "MCP settings > Open config.toml".

## Server Configuration Options

### STDIO Servers

```toml
[mcp_servers.example_server]
command = "npx"
args = ["-y", "@example/mcp"]

[mcp_servers.example_server.env]
MY_VAR = "value"
```

**Parameters:**
- `command` (required): Launch command
- `args` (optional): Command arguments
- `env` (optional): Environment variables
- `env_vars` (optional): Whitelist for forwarding
- `cwd` (optional): Working directory

### HTTP Streamable Servers

```toml
[mcp_servers.figma]
url = "https://mcp.figma.com/mcp"
bearer_token_env_var = "FIGMA_OAUTH_TOKEN"
http_headers = { "X-Header" = "value" }
```

**Parameters:**
- `url` (required): Server endpoint
- `bearer_token_env_var` (optional): Auth token environment variable
- `http_headers` (optional): Static header mappings
- `env_http_headers` (optional): Dynamic headers from environment

### Universal Options

```toml
startup_timeout_sec = 10      # Server startup timeout (default: 10s)
tool_timeout_sec = 60         # Tool execution timeout (default: 60s)
enabled = true                # Enable/disable without deletion
enabled_tools = ["tool1"]     # Allow-list specific tools
disabled_tools = ["tool2"]    # Deny-list (applied after allow-list)
```

### OAuth Support

Enable the Rust MCP client for OAuth on streamable HTTP:
```toml
[features]
rmcp_client = true
```

(Alternative legacy flag: `experimental_use_rmcp_client`)

## Popular MCP Servers

- **Context7**: Developer documentation access
- **Figma**: Design file integration (local/remote options)
- **Playwright**: Browser automation and inspection
- **Chrome DevTools**: Chrome browser control
- **Sentry**: Error log access
- **GitHub**: Enhanced GitHub account management

## Running Codex as an MCP Server

Start Codex as a server accessible to other MCP clients:
```bash
codex mcp-server
```

Inspect with the MCP Inspector:
```bash
npx @modelcontextprotocol/inspector codex mcp-server
```

### Available Tools

**`codex`** tool properties:
- `prompt` (required): Initial user prompt
- `model`: Override model name (e.g., o3, o4-mini)
- `approval-policy`: Shell command approval (untrusted/on-failure/never)
- `sandbox`: Mode selection (read-only/workspace-write/danger-full-access)
- `config`: Override individual settings
- `cwd`: Working directory
- `include-plan-tool`: Boolean for plan tool inclusion

**`codex-reply`** tool properties:
- `prompt` (required): Continuation message
- `conversationId` (required): Session identifier

Note: Adjust MCP Inspector timeouts to 600000ms (10 minutes) for Codex execution.

## Cross-Platform Integration

Codex CLI MCP servers can be accessed by:
- Claude Code (via MCP client)
- Gemini CLI (via MCP client)
- Custom agents using OpenAI Agents SDK
- Any MCP-compatible client

## Key Files

- Configuration: `~/.codex/config.toml`
- Shared between CLI and IDE extension
