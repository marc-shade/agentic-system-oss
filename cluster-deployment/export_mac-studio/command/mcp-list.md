# MCP Server List

List all configured MCP servers and their status.

## Usage

```bash
/mcp-list
```

## Implementation

```bash
# Parse ~/.claude.json for MCP server configuration
echo "=== User-Level MCP Servers (~/.claude.json) ==="
cat ~/.claude.json | jq -r '.mcpServers | keys[]' 2>/dev/null || echo "No servers configured"

echo -e "\n=== Project-Level MCP Servers (.mcp.json) ==="
cat ~/.mcp.json | jq -r '.mcpServers | keys[]' 2>/dev/null || echo "No project servers configured"

echo -e "\n=== Active Tier Configuration ==="
echo "Tier 0 (Essential):"
echo "  - enhanced-memory"
echo "  - voice-mode"
echo "  - arduino-surface"
echo "  - safla-enhanced"

echo -e "\nTier 1 (Cognitive):"
echo "  - agent-runtime-mcp"

echo -e "\nTier 2 (Reasoning):"
echo "  - sequential-thinking"
```

## What This Shows

- User-level MCP servers (from ~/.claude.json)
- Project-level MCP servers (from .mcp.json)
- Tier assignments (essential, cognitive, reasoning)
- Total server count

## Output Format

```
=== User-Level MCP Servers ===
agent-runtime-mcp
enhanced-memory
sequential-thinking
voice-mode
arduino-surface

=== Project-Level MCP Servers ===
semantic-file-search-mcp
visual-verification-mcp
chrome-devtools
safla-enhanced

=== Active Tier Configuration ===
Tier 0 (Essential):
  - enhanced-memory
  - voice-mode
  - arduino-surface
  - safla-enhanced

Tier 1 (Cognitive):
  - agent-runtime-mcp

Tier 2 (Reasoning):
  - sequential-thinking
```

## Related Commands

- `/mcp-status` - Check MCP server health
- `/mcp-health` - Comprehensive MCP diagnostics
- `/mcp-restart` - Restart MCP servers

## Notes

- Lists both user and project-level configurations
- Shows tier assignments for understanding architecture
- Identifies which servers are active
