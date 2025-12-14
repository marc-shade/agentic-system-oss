# MCP Server Status

Check the health and availability of all MCP servers.

## Usage

```bash
/mcp-status
```

## Implementation

```bash
echo "=== MCP Server Health Check ==="

# Check if Claude Code is running (MCP host)
ps aux | grep -i "claude" | grep -v grep > /dev/null && echo "✅ Claude Code: Running" || echo "⚠️  Claude Code: Not detected"

# Check key MCP server processes
echo -e "\n=== MCP Server Processes ==="

# enhanced-memory-mcp (Node.js)
ps aux | grep "enhanced-memory" | grep -v grep > /dev/null && echo "✅ enhanced-memory-mcp: Running" || echo "❌ enhanced-memory-mcp: Not running"

# voice-mode (Python)
ps aux | grep "voice-mode" | grep -v grep > /dev/null && echo "✅ voice-mode: Running" || echo "❌ voice-mode: Not running"

# arduino-surface (Python)
ps aux | grep "arduino_surface_mcp" | grep -v grep > /dev/null && echo "✅ arduino-surface: Running" || echo "❌ arduino-surface: Not running"

# agent-runtime-mcp (Node.js)
ps aux | grep "agent-runtime" | grep -v grep > /dev/null && echo "✅ agent-runtime-mcp: Running" || echo "❌ agent-runtime-mcp: Not running"

# sequential-thinking (Node.js)
ps aux | grep "sequential-thinking" | grep -v grep > /dev/null && echo "✅ sequential-thinking: Running" || echo "❌ sequential-thinking: Not running"

# Check MCP databases
echo -e "\n=== MCP Databases ==="
ls -lh /Volumes/SSDRAID0/agentic-system/databases/mcp/*.db 2>/dev/null | wc -l | xargs echo "Database files:"
du -sh /Volumes/SSDRAID0/agentic-system/databases/mcp/ 2>/dev/null || echo "Database directory not accessible"

# Check MCP state directories
echo -e "\n=== MCP State Directories ==="
ls -d /Volumes/SSDRAID0/agentic-system/mcp-state/* 2>/dev/null | wc -l | xargs echo "State directories:"
du -sh /Volumes/SSDRAID0/agentic-system/mcp-state/ 2>/dev/null || echo "State directory not accessible"

echo -e "\n=== Summary ==="
total_servers=6
running_servers=$(ps aux | grep -E "enhanced-memory|voice-mode|arduino_surface|agent-runtime|sequential-thinking" | grep -v grep | wc -l | tr -d ' ')
echo "$running_servers/$total_servers MCP servers running"

if [ "$running_servers" -eq "$total_servers" ]; then
    echo "✅ All MCP servers operational"
elif [ "$running_servers" -gt 0 ]; then
    echo "⚠️  Partial MCP service ($running_servers active)"
else
    echo "❌ MCP system down - restart Claude Code"
fi
```

## What This Shows

- Claude Code host process status
- Individual MCP server processes
- Database file status and size
- State directory status
- Overall MCP system health summary

## Output Format

```
=== MCP Server Health Check ===
✅ Claude Code: Running

=== MCP Server Processes ===
✅ enhanced-memory-mcp: Running
✅ voice-mode: Running
✅ arduino-surface: Running
✅ agent-runtime-mcp: Running
✅ sequential-thinking: Running

=== MCP Databases ===
Database files: 3
911M    /Volumes/SSDRAID0/agentic-system/databases/mcp/

=== MCP State Directories ===
State directories: 5
45M     /Volumes/SSDRAID0/agentic-system/mcp-state/

=== Summary ===
5/6 MCP servers running
⚠️  Partial MCP service (5 active)
```

## Related Commands

- `/mcp-list` - List all MCP servers
- `/mcp-health` - Comprehensive MCP diagnostics
- `/mcp-restart` - Restart MCP servers

## Notes

- Checks both process status and file system health
- Requires Claude Code to be running for accurate results
- Some servers may not show in process list if using stdio transport
