# Gemini CLI MCP Server Configuration Guide

> Source: https://google-gemini.github.io/gemini-cli/docs/tools/mcp-server.html

## Overview

The Gemini CLI integrates with Model Context Protocol (MCP) servers to extend functionality by exposing tools and resources. MCP servers act as bridges connecting the Gemini model to external systems, APIs, databases, and custom workflows.

## Core Capabilities

MCP servers enable the CLI to:
- **Discover tools** via standardized schema definitions
- **Execute tools** with defined arguments and structured responses
- **Access resources** for data interaction

## Configuration Structure

### settings.json Format

Configure MCP servers in your `~/.gemini/settings.json` file under the `mcpServers` object:

```json
{
  "mcp": {
    "allowed": ["trusted-server"],
    "excluded": ["experimental-server"]
  },
  "mcpServers": {
    "serverName": {
      "command": "path/to/server",
      "args": ["--arg1", "value1"],
      "env": {
        "API_KEY": "$MY_API_TOKEN"
      },
      "cwd": "./server-directory",
      "timeout": 30000,
      "trust": false,
      "includeTools": ["tool1", "tool2"],
      "excludeTools": ["dangerous_tool"]
    }
  }
}
```

### Global MCP Settings

The `mcp` object controls server-wide behavior:
- **`serverCommand`**: Global command to start an MCP server
- **`allowed`**: Whitelist of server names to connect
- **`excluded`**: Blacklist of servers to skip

## Supported Transport Types

### 1. Stdio Transport (Default)
Spawns a subprocess with stdin/stdout communication.

```json
{
  "mcpServers": {
    "pythonTools": {
      "command": "python",
      "args": ["-m", "my_mcp_server"],
      "cwd": "./mcp-servers/python",
      "env": {
        "DATABASE_URL": "$DB_CONNECTION_STRING"
      },
      "timeout": 15000
    }
  }
}
```

### 2. SSE Transport
Connects to Server-Sent Events endpoints.

```json
{
  "mcpServers": {
    "sseServer": {
      "url": "https://api.example.com/sse",
      "headers": {
        "Authorization": "Bearer token"
      }
    }
  }
}
```

### 3. HTTP Streaming Transport
Uses HTTP streaming for communication.

```json
{
  "mcpServers": {
    "httpServer": {
      "httpUrl": "http://localhost:3000/mcp",
      "headers": {
        "Authorization": "Bearer api-token"
      },
      "timeout": 5000
    }
  }
}
```

## Configuration Properties

### Required (one of)
- **`command`**: Executable path for stdio transport
- **`url`**: SSE endpoint URL
- **`httpUrl`**: HTTP streaming URL

### Optional Properties
| Property | Type | Purpose |
|----------|------|---------|
| `args` | string[] | Command-line arguments |
| `headers` | object | Custom HTTP headers |
| `env` | object | Environment variables (supports `$VAR` syntax) |
| `cwd` | string | Working directory for stdio |
| `timeout` | number | Request timeout in milliseconds (default: 600,000) |
| `trust` | boolean | Bypass tool confirmation dialogs |
| `includeTools` | string[] | Allowlist specific tools |
| `excludeTools` | string[] | Blocklist specific tools |

## OAuth Support

### Automatic Discovery
For servers supporting OAuth discovery, minimal configuration is needed:

```json
{
  "mcpServers": {
    "discoveredServer": {
      "url": "https://api.example.com/sse"
    }
  }
}
```

The CLI automatically detects 401 responses, discovers OAuth endpoints, and handles the authentication flow.

### Authentication Flow
1. Initial connection fails with 401 Unauthorized
2. OAuth endpoints are discovered from server metadata
3. Browser opens for user authentication
4. Authorization code exchanges for access tokens
5. Tokens stored securely in `~/.gemini/mcp-oauth-tokens.json`
6. Connection retries with valid tokens

### Provider Types

**Dynamic Discovery** (default):
```json
{
  "mcpServers": {
    "server": {
      "url": "https://api.example.com/sse",
      "authProviderType": "dynamic_discovery"
    }
  }
}
```

**Google Credentials**:
```json
{
  "mcpServers": {
    "googleCloudServer": {
      "httpUrl": "https://service.run.app/mcp",
      "authProviderType": "google_credentials",
      "oauth": {
        "scopes": ["https://www.googleapis.com/auth/userinfo.email"]
      }
    }
  }
}
```

**Service Account Impersonation**:
```json
{
  "mcpServers": {
    "iapServer": {
      "url": "https://my-iap-service.run.app/sse",
      "authProviderType": "service_account_impersonation",
      "targetAudience": "CLIENT_ID.apps.googleusercontent.com",
      "targetServiceAccount": "sa@project.iam.gserviceaccount.com"
    }
  }
}
```

## CLI Management Commands

### Add Server
```bash
gemini mcp add [options] <name> <commandOrUrl> [args...]
```

Options:
- `-s, --scope`: user or project scope
- `-t, --transport`: stdio, sse, or http
- `-e, --env`: Environment variables
- `-H, --header`: HTTP headers
- `--timeout`: Connection timeout
- `--trust`: Bypass confirmations
- `--include-tools`: Comma-separated tool allowlist
- `--exclude-tools`: Comma-separated tool blocklist

Examples:
```bash
# Stdio server
gemini mcp add python-server python server.py --port 8080

# HTTP server
gemini mcp add --transport http http-server https://api.example.com/mcp

# SSE server
gemini mcp add --transport sse sse-server https://api.example.com/sse \
  --header "Authorization: Bearer abc123"
```

### List Servers
```bash
gemini mcp list
```

### Remove Server
```bash
gemini mcp remove <name>
```

## Rich Content Support

MCP tools can return diverse content types in a single response:

```json
{
  "content": [
    {
      "type": "text",
      "text": "Here is the logo you requested."
    },
    {
      "type": "image",
      "data": "BASE64_ENCODED_IMAGE_DATA",
      "mimeType": "image/png"
    }
  ]
}
```

Supported content block types:
- `text`
- `image`
- `audio`
- `resource` (embedded content)
- `resource_link`

## MCP Prompts as Slash Commands

MCP servers can expose predefined prompts executable as slash commands:

```typescript
server.registerPrompt(
  'poem-writer',
  {
    title: 'Poem Writer',
    description: 'Write a haiku',
    argsSchema: { title: z.string(), mood: z.string().optional() }
  },
  ({ title, mood }) => ({
    messages: [{
      role: 'user',
      content: {
        type: 'text',
        text: `Write a haiku ${mood ? `with mood ${mood}` : ''} called ${title}`
      }
    }]
  })
);
```

Invoke with: `/poem-writer --title="Gemini CLI" --mood="reverent"`

## Tool Execution Flow

1. **Invocation**: Model generates `FunctionCall` with tool name and arguments
2. **Confirmation**: Trust settings determine if user confirmation is required
3. **Execution**: Parameters validated; MCP server called with original tool name
4. **Response Processing**: Results formatted for LLM context and user display

## Status Monitoring

### Check Status
```bash
/mcp
```

### Server States
- **`DISCONNECTED`**: Not connected or has errors
- **`CONNECTING`**: Connection attempt in progress
- **`CONNECTED`**: Ready for use

## Cross-Platform Integration

Gemini CLI MCP servers can communicate with:
- Claude Code (via shared MCP servers)
- OpenAI Codex CLI (via shared MCP servers)
- Any MCP-compatible client

## Key Files

- Configuration: `~/.gemini/settings.json`
- OAuth tokens: `~/.gemini/mcp-oauth-tokens.json`
