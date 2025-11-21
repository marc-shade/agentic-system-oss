# Nuclei Integration Guide

## Overview

Nuclei has been integrated into the agentic system, providing both CLI and MCP access for vulnerability scanning across all agents.

## Installation Summary

- **Nuclei CLI**: v3.5.1 installed at `/Volumes/FILES/go/bin/nuclei`
- **Nuclei MCP Server**: Python-based server at `/Volumes/SSDRAID0/agentic-system/mcp-servers/nuclei-mcp`
- **Templates**: Latest templates installed at `/Users/marc/nuclei-templates`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Scanning Layer                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Checkov    │  │    Nuclei    │  │  Secret Scan │      │
│  │     IaC      │  │  Web Vulns   │  │   Detection  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│                   ┌────────▼────────┐                       │
│                   │  Unified Script │                       │
│                   └────────┬────────┘                       │
│                            │                                 │
├────────────────────────────┼─────────────────────────────────┤
│                    MCP Integration Layer                     │
├────────────────────────────┼─────────────────────────────────┤
│                            │                                 │
│                   ┌────────▼────────┐                       │
│                   │  Nuclei MCP     │                       │
│                   │    Server       │                       │
│                   └────────┬────────┘                       │
│                            │                                 │
├────────────────────────────┼─────────────────────────────────┤
│                       Agent Access                           │
├────────────────────────────┼─────────────────────────────────┤
│                            │                                 │
│  All agents can use:       │                                 │
│  - nuclei_scan_start()    ◄┘                                │
│  - CLI via Bash tool                                         │
│  - Unified security script                                   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Usage

### 1. CLI Access

All agents can use Nuclei directly via the Bash tool:

```bash
/Volumes/FILES/go/bin/nuclei -u https://example.com -j
```

### 2. MCP Access

Use the Nuclei MCP server for programmatic scanning:

```python
# Scan a target with specific severity
mcp__nuclei-mcp__nuclei_scan_start(
    target="https://example.com",
    severity="critical,high"
)

# Scan with specific templates
mcp__nuclei-mcp__nuclei_scan_start(
    target="https://api.example.com",
    templates=["cves", "exposures", "vulnerabilities"]
)

# Scan with tags
mcp__nuclei-mcp__nuclei_scan_start(
    target="https://example.com",
    template_tags=["xss", "sqli", "rce"]
)
```

### 3. Unified Security Scan

Run comprehensive security scanning:

```bash
# Scan current directory
/Volumes/SSDRAID0/agentic-system/scripts/unified-security-scan.sh

# Scan specific directory
/Volumes/SSDRAID0/agentic-system/scripts/unified-security-scan.sh /path/to/project

# Custom output directory
OUTPUT_DIR=/path/to/reports ./scripts/unified-security-scan.sh
```

## MCP Server Configuration

Located in `/Users/marc/.mcp.json`:

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

## Tool Parameters

### nuclei_scan_start

- **target** (required): Target URL or IP address to scan
- **templates** (optional): List of specific template names to use
- **severity** (optional): Filter by severity (critical, high, medium, low, info)
- **template_tags** (optional): List of template tags to filter
- **output_format** (default: "json"): Output format

### Return Format

```json
{
  "success": true,
  "target": "https://example.com",
  "time_cost_seconds": 12.5,
  "results": [
    {
      "template": "cve-2021-12345",
      "severity": "critical",
      "matched_at": "https://example.com/vulnerable",
      "info": {
        "name": "CVE-2021-12345",
        "description": "Remote Code Execution"
      }
    }
  ]
}
```

## Integration with Existing Workflows

### Checkov Integration

The unified security scan combines:

1. **IaC Scanning** (Checkov): Infrastructure misconfigurations
2. **Secret Detection** (Checkov): Hardcoded credentials
3. **Web Vulnerabilities** (Nuclei): Application security issues

### CI/CD Integration

Add to your CI/CD pipeline:

```yaml
security-scan:
  script:
    - /Volumes/SSDRAID0/agentic-system/scripts/unified-security-scan.sh
  artifacts:
    paths:
      - security-reports/
```

## Template Management

### Update Templates

```bash
/Volumes/FILES/go/bin/nuclei -update-templates
```

### List Templates

```bash
/Volumes/FILES/go/bin/nuclei -tl
```

### Template Categories

- **CVEs**: Known CVE vulnerabilities
- **Exposures**: Configuration exposures
- **Vulnerabilities**: Web application vulnerabilities
- **Misconfigurations**: Common misconfigurations
- **Technologies**: Technology detection

## Best Practices

1. **Regular Updates**: Update templates weekly
   ```bash
   /Volumes/FILES/go/bin/nuclei -update-templates
   ```

2. **Severity Filtering**: Start with critical/high
   ```python
   nuclei_scan_start(target="...", severity="critical,high")
   ```

3. **Targeted Scanning**: Use specific templates for focused scans
   ```python
   nuclei_scan_start(target="...", templates=["cves/2024"])
   ```

4. **Rate Limiting**: Respect target systems
   ```bash
   nuclei -u target -rate-limit 10
   ```

5. **Compliance**: Ensure authorized scanning only

## Troubleshooting

### MCP Server Not Starting

Check configuration:
```bash
cat /Users/marc/.mcp.json
```

Verify binary path:
```bash
ls -l /Volumes/FILES/go/bin/nuclei
```

### Template Issues

Reset templates:
```bash
rm -rf ~/nuclei-templates
/Volumes/FILES/go/bin/nuclei -update-templates
```

### Permission Errors

Ensure correct permissions:
```bash
chmod +x /Volumes/FILES/go/bin/nuclei
chmod +x /Volumes/SSDRAID0/agentic-system/scripts/unified-security-scan.sh
```

## Advanced Usage

### Custom Templates

Create custom templates in `~/nuclei-templates/custom/`:

```yaml
id: custom-check
info:
  name: Custom Security Check
  severity: medium
requests:
  - method: GET
    path:
      - "{{BaseURL}}/api/sensitive"
    matchers:
      - type: word
        words:
          - "sensitive data"
```

### Automated Scanning

Set up cron job for regular scans:

```bash
# Daily security scan at 2 AM
0 2 * * * /Volumes/SSDRAID0/agentic-system/scripts/unified-security-scan.sh /path/to/project
```

## Security Considerations

1. **Authorized Testing Only**: Only scan systems you own or have permission to test
2. **Rate Limiting**: Use appropriate rate limits to avoid DoS
3. **Credentials**: Never commit Nuclei reports with sensitive data
4. **Network Impact**: Be aware of network traffic generated
5. **False Positives**: Validate findings before acting

## Resources

- **Nuclei Documentation**: https://docs.projectdiscovery.io/tools/nuclei
- **Template Library**: https://github.com/projectdiscovery/nuclei-templates
- **MCP Documentation**: https://modelcontextprotocol.io/
- **ProjectDiscovery**: https://projectdiscovery.io/

## Support

For issues or questions:

1. Check Nuclei logs: `~/.config/nuclei/nuclei.log`
2. Verify MCP server status: Check Claude Code MCP panel
3. Test CLI directly: `/Volumes/FILES/go/bin/nuclei -version`
4. Review integration script: `/Volumes/SSDRAID0/agentic-system/scripts/unified-security-scan.sh`

## Updates

To update Nuclei:

```bash
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
```

To update templates:

```bash
/Volumes/FILES/go/bin/nuclei -update-templates
```

---

**Last Updated**: 2025-11-18
**Nuclei Version**: v3.5.1
**MCP Server Version**: 1.0.0
