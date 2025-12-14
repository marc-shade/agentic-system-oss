# MCP Server Restart

Restart MCP servers (requires Claude Code restart for full effect).

## Usage

```bash
/mcp-restart [server-name]
```

## Parameters

- `server-name` - Optional specific server to restart. If omitted, provides restart guidance for all servers.

## Implementation

```bash
echo "=== MCP Server Restart ==="

if [ -z "$1" ]; then
    echo "MCP servers run within Claude Code and require Claude Code restart for full reinitialization."
    echo ""
    echo "To restart all MCP servers:"
    echo "1. Quit Claude Code completely"
    echo "2. Relaunch Claude Code"
    echo "3. MCP servers will reinitialize automatically"
    echo ""
    echo "To restart specific server: /mcp-restart [server-name]"
    echo ""
    echo "Available servers:"
    echo "  - enhanced-memory"
    echo "  - voice-mode"
    echo "  - arduino-surface"
    echo "  - agent-runtime-mcp"
    echo "  - sequential-thinking"
    echo "  - safla-enhanced"
    echo ""
    echo "⚠️  Note: Individual server restart may not be possible depending on transport type"
else
    server_name="$1"
    echo "Attempting to restart: $server_name"
    echo ""

    # Try to find and kill process
    pid=$(ps aux | grep "$server_name" | grep -v grep | awk '{print $2}' | head -1)

    if [ -n "$pid" ]; then
        echo "Found process: PID $pid"
        echo "Killing process..."
        kill "$pid"
        sleep 2

        # Check if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "⚠️  Process still running, trying force kill..."
            kill -9 "$pid"
        fi

        echo "✅ Process terminated"
        echo ""
        echo "Claude Code will automatically restart the MCP server."
        echo "If server doesn't restart, restart Claude Code completely."
    else
        echo "❌ Process not found: $server_name"
        echo ""
        echo "This could mean:"
        echo "1. Server is not running"
        echo "2. Server uses stdio transport (can't be individually restarted)"
        echo "3. Server name doesn't match process name"
        echo ""
        echo "Solution: Restart Claude Code to reinitialize all MCP servers"
    fi
fi
```

## What This Does

- Provides restart guidance for MCP servers
- Attempts to restart specific server if requested
- Explains stdio transport limitations
- Recommends Claude Code restart for reliable reinitialization

## Output Format

**Without Arguments**:
```
=== MCP Server Restart ===
MCP servers run within Claude Code and require Claude Code restart for full reinitialization.

To restart all MCP servers:
1. Quit Claude Code completely
2. Relaunch Claude Code
3. MCP servers will reinitialize automatically

Available servers:
  - enhanced-memory
  - voice-mode
  - arduino-surface
  - agent-runtime-mcp
  - sequential-thinking
  - safla-enhanced

⚠️  Note: Individual server restart may not be possible depending on transport type
```

**With Server Name**:
```
=== MCP Server Restart ===
Attempting to restart: enhanced-memory

Found process: PID 12345
Killing process...
✅ Process terminated

Claude Code will automatically restart the MCP server.
If server doesn't restart, restart Claude Code completely.
```

## Important Notes

### Transport Types

1. **stdio Transport** (most common):
   - Server runs as subprocess of Claude Code
   - Cannot be individually restarted
   - Requires Claude Code restart

2. **SSE/HTTP Transport** (less common):
   - Server runs as separate process
   - Can be individually restarted
   - May auto-restart on failure

### When to Restart

**Restart Individual Server**:
- Server crashed or hung
- Configuration change for specific server
- Testing specific server behavior

**Restart All Servers (Claude Code)**:
- Configuration file changes (~/.claude.json)
- Multiple server issues
- After MCP server code changes
- System-wide MCP issues

### Best Practices

1. **Try health check first**: `/mcp-health` to diagnose issue
2. **Check logs**: Look for specific errors before restarting
3. **Save work**: Close any ongoing conversations before restart
4. **Clean restart**: Quit Claude Code completely, don't just restart

## Related Commands

- `/mcp-list` - List all MCP servers
- `/mcp-status` - Check server health
- `/mcp-health` - Comprehensive diagnostics

## Notes

- Most MCP servers use stdio transport and can't be individually restarted
- Claude Code automatically restarts crashed MCP servers
- Full Claude Code restart is most reliable method
- Server process names may not match configuration names exactly
