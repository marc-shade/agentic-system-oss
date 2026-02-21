# Nuclei MCP Server - Quick Setup Guide

## Installation Complete

The Nuclei MCP server is now configured and ready to use.

## Activation

**IMPORTANT**: Restart Claude Code to load the new MCP server.

```bash
# The server will auto-start when Claude Code restarts
```

## Testing the Server

After restarting Claude Code, test with:

```python
# Simple test scan
mcp__nuclei-mcp__nuclei_scan_start(
    target="https://httpbin.org",
    severity="info"
)

# Production scan example
mcp__nuclei-mcp__nuclei_scan_start(
    target="https://your-app.com",
    severity="critical,high",
    template_tags=["cve", "exposure"]
)
```

## Available Parameters

- `target` (required): URL or IP to scan
- `severity`: critical, high, medium, low, info
- `templates`: List of template names
- `template_tags`: List of tags (e.g., ["xss", "sqli"])
- `output_format`: Default is "json"

## Configuration

MCP configuration is in: `~/.claude.json`

```json
{
  "nuclei-mcp": {
    "command": "uv",
    "args": ["--directory", "/path/to/mcp-servers/nuclei-mcp", "run", "main.py"],
    "env": {
      "NUCLEI_BIN_PATH": "~/go/bin/nuclei"
    }
  }
}
```

## Troubleshooting

### MCP Server Not Appearing
1. Restart Claude Code
2. Check MCP panel in Claude Code
3. Verify config: `cat ~/.claude.json`

### Binary Not Found
```bash
which nuclei
# or check your Go bin path
ls -l ~/go/bin/nuclei
```

### Template Issues
```bash
nuclei -update-templates
```

## Integration with Other Tools

This MCP server works alongside:
- **Checkov** for IaC scanning
- **Secret detection** via Checkov
- Your project's unified security scanning scripts

## Documentation

See the main README.md for full documentation.

---
**Status**: Ready for activation (restart required)
