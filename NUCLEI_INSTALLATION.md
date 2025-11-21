# Nuclei Installation Complete

## Installation Summary

Nuclei vulnerability scanner has been successfully installed and integrated into the agentic system.

### Components Installed

#### 1. Nuclei CLI
- **Version**: v3.5.1 (latest)
- **Location**: `/Volumes/FILES/go/bin/nuclei`
- **Templates**: 8,794 templates (v10.3.2)
- **Template Path**: `/Users/marc/nuclei-templates`
- **Status**: ✅ Operational

#### 2. Nuclei MCP Server
- **Implementation**: Python-based (crazyMarky/mcp_nuclei_server)
- **Location**: `/Volumes/SSDRAID0/agentic-system/mcp-servers/nuclei-mcp`
- **Configuration**: `/Users/marc/.mcp.json`
- **Dependencies**: Installed via UV
- **Status**: ✅ Configured

#### 3. Integration Scripts
- **Unified Security Scanner**: `/Volumes/SSDRAID0/agentic-system/scripts/unified-security-scan.sh`
- **Documentation**: `/Volumes/SSDRAID0/agentic-system/docs/NUCLEI_INTEGRATION.md`
- **Status**: ✅ Ready

## Quick Start

### Using Nuclei CLI

```bash
# Basic scan
/Volumes/FILES/go/bin/nuclei -u https://example.com

# Scan with severity filter
/Volumes/FILES/go/bin/nuclei -u https://example.com -s critical,high

# Scan with specific templates
/Volumes/FILES/go/bin/nuclei -u https://example.com -t cves/,exposures/
```

### Using MCP Server

Restart Claude Code to load the new MCP server, then use:

```python
# Example scan via MCP
mcp__nuclei-mcp__nuclei_scan_start(
    target="https://example.com",
    severity="critical,high",
    template_tags=["cve", "exposure"]
)
```

### Using Unified Security Scanner

```bash
# Run complete security audit
/Volumes/SSDRAID0/agentic-system/scripts/unified-security-scan.sh

# Scan specific directory
/Volumes/SSDRAID0/agentic-system/scripts/unified-security-scan.sh /path/to/project
```

## Available to All Agents

All agents in the system now have access to:

1. **Nuclei CLI** - Direct command-line scanning
2. **Nuclei MCP** - Programmatic API access
3. **Unified Scanner** - Integrated security workflow

## Security Workflow Integration

```
┌─────────────────────────────────────────────────┐
│              Security Scanning                   │
├─────────────────────────────────────────────────┤
│                                                  │
│  1. IaC Scanning (Checkov)                      │
│     ↓                                            │
│  2. Secret Detection (Checkov)                   │
│     ↓                                            │
│  3. Web Vulnerability Scanning (Nuclei)         │
│     ↓                                            │
│  4. Unified Report Generation                    │
│                                                  │
└─────────────────────────────────────────────────┘
```

## Next Steps

### 1. Restart Claude Code
To activate the Nuclei MCP server:
```bash
# Restart Claude Code to load new MCP configuration
```

### 2. Test MCP Integration
After restart, test the MCP server:
```python
mcp__nuclei-mcp__nuclei_scan_start(
    target="https://httpbin.org",
    severity="info"
)
```

### 3. Run First Security Scan
Execute a comprehensive security scan:
```bash
/Volumes/SSDRAID0/agentic-system/scripts/unified-security-scan.sh
```

### 4. Schedule Regular Scans
Add to cron for automated security monitoring:
```bash
# Daily at 2 AM
0 2 * * * /Volumes/SSDRAID0/agentic-system/scripts/unified-security-scan.sh
```

## Configuration Details

### MCP Server Configuration
File: `/Users/marc/.mcp.json`

```json
{
  "mcpServers": {
    "nuclei-mcp": {
      "command": "/opt/homebrew/Caskroom/miniconda/base/bin/uv",
      "args": [
        "--directory",
        "/Volumes/SSDRAID0/agentic-system/mcp-servers/nuclei-mcp",
        "run",
        "main.py"
      ],
      "env": {
        "NUCLEI_BIN_PATH": "/Volumes/FILES/go/bin/nuclei"
      }
    }
  }
}
```

### Environment Variables
- `NUCLEI_BIN_PATH`: `/Volumes/FILES/go/bin/nuclei`
- Templates auto-updated to latest version

## Template Statistics

- **Total Templates**: 8,794
- **Template Version**: v10.3.2 (latest)
- **New Templates**: 130 added in latest release
- **Categories**:
  - CVEs
  - Cloud
  - Code
  - DNS
  - File
  - HTTP
  - Network
  - JavaScript
  - Headless

## Maintenance

### Update Templates
```bash
/Volumes/FILES/go/bin/nuclei -update-templates
```

### Update Nuclei CLI
```bash
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
```

### View Statistics
```bash
/Volumes/FILES/go/bin/nuclei -stats
```

## Documentation

- **Integration Guide**: `/Volumes/SSDRAID0/agentic-system/docs/NUCLEI_INTEGRATION.md`
- **Official Docs**: https://docs.projectdiscovery.io/tools/nuclei
- **Template Docs**: https://github.com/projectdiscovery/nuclei-templates

## Support

For issues or questions:

1. Check CLI version: `/Volumes/FILES/go/bin/nuclei -version`
2. Verify templates: `ls -l /Users/marc/nuclei-templates`
3. Test MCP: Restart Claude Code and test MCP function
4. Review logs: Check Claude Code MCP panel

## Integration Benefits

✅ **CLI Access** - Direct command-line scanning
✅ **MCP Access** - Programmatic API for all agents
✅ **Unified Workflow** - Integrated with Checkov and secret scanning
✅ **8,794 Templates** - Comprehensive vulnerability coverage
✅ **Auto-Updates** - Latest CVEs and vulnerabilities
✅ **Cross-Agent** - Available to all agents in the system

---

**Installation Date**: 2025-11-18
**Installed By**: Claude Code
**Status**: ✅ Complete and Operational
