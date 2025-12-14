# Security Scanner MCP Server

Comprehensive security scanning integration using Nuclei vulnerability scanner with cluster-wide capabilities.

## Features

- **Single Target Scanning**: Scan individual URLs or IPs with customizable severity and templates
- **Network Scanning**: Batch scan multiple targets or CIDR ranges
- **Cluster Integration**: Scan all nodes in the agentic cluster
- **Template Management**: List, filter, and update Nuclei templates
- **Scan History**: Retrieve and analyze previous scan results
- **Scheduled Scans**: Configure periodic security assessments
- **Multiple Output Formats**: JSON, JSONL, or Markdown reports

## Installation

```bash
cd /mnt/agentic-system/mcp-servers/security-scanner-mcp
source /mnt/agentic-system/.venv/bin/activate
pip install -e .
```

## MCP Configuration

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "security-scanner": {
      "command": "/mnt/agentic-system/.venv/bin/python",
      "args": ["-m", "security_scanner.server"],
      "env": {
        "NUCLEI_BIN": "/home/marc/go/bin/nuclei",
        "SCAN_RESULTS_DIR": "/mnt/agentic-system/security-scans"
      }
    }
  }
}
```

## Available Tools

### scan_target
Scan a single target with Nuclei vulnerability scanner.

**Parameters:**
- `target` (required): URL or IP address
- `severity`: Array of severity levels ["info", "low", "medium", "high", "critical"]
- `templates`: Specific template paths or tags
- `rate_limit`: Requests per second (default: 150)
- `timeout`: Scan timeout in seconds (default: 300)
- `output_format`: "json", "jsonl", or "markdown"

**Example:**
```python
{
  "target": "https://example.com",
  "severity": ["high", "critical"],
  "rate_limit": 100
}
```

### scan_network
Scan multiple targets from a list or CIDR range.

**Parameters:**
- `targets`: Array of target URLs/IPs
- `target_file`: Path to file with targets (one per line)
- `severity`: Severity filter
- `parallel`: Number of concurrent scans (default: 5)
- `rate_limit`: Requests per second per target

### scan_cluster_nodes
Scan all nodes in the agentic cluster for vulnerabilities.

**Parameters:**
- `scan_type`: "network", "web", "api", or "full"
- `severity`: Severity levels to check

### list_templates
List available Nuclei templates by tag, severity, or author.

**Parameters:**
- `tag`: Filter by tag (e.g., "cve", "exposure")
- `severity`: Filter by severity level
- `author`: Filter by template author

### update_templates
Update Nuclei templates to the latest version.

### get_scan_results
Retrieve results from a previous scan by scan_id.

**Parameters:**
- `scan_id` (required): Scan identifier
- `limit`: Max results to return (default: 100)
- `severity`: Filter by severity levels

### list_scans
List all previous security scans.

**Parameters:**
- `limit`: Maximum number of scans to return
- `target`: Filter by target

### schedule_periodic_scan
Schedule recurring security scans (requires agent runtime).

**Parameters:**
- `targets` (required): List of targets to scan
- `interval_hours`: Scan interval (default: 24)
- `severity_threshold`: Minimum severity to report (default: "medium")
- `notify_on_new`: Alert on new vulnerabilities (default: true)

## Integration with Agentic System

### Cluster-Wide Scanning

The security scanner automatically detects and scans all nodes in the agentic cluster.
Cluster nodes are loaded from configuration:
- builder - Linux build node
- orchestrator - Coordination node
- coordinator - Multi-node coordinator
- files - File server

### Autonomous Agent Integration

Combine with the autonomous security scanning agent for:
- Automated vulnerability assessment
- Continuous security monitoring
- Intelligent threat prioritization
- Automatic remediation recommendations

### Enhanced Memory Integration

Scan results are stored in enhanced-memory for:
- Historical vulnerability tracking
- Pattern recognition across scans
- Causal relationship analysis
- Learning from remediation outcomes

## Scan Results

Results are stored in `/mnt/agentic-system/security-scans/`:
- `scan_YYYYMMDD_HHMMSS_ID.json` - Scan findings
- `scan_YYYYMMDD_HHMMSS_ID_metadata.json` - Scan metadata

## Example Usage

### Scan a single target
```bash
# Via Claude Code
scan_target({
  "target": "192.168.1.87",
  "severity": ["high", "critical"],
  "templates": ["network", "exposure"]
})
```

### Scan entire cluster
```bash
scan_cluster_nodes({
  "scan_type": "full",
  "severity": ["medium", "high", "critical"]
})
```

### Review previous scans
```bash
list_scans({"limit": 10})
get_scan_results({"scan_id": "scan_20251118_110000_1234"})
```

## Security Considerations

- Scans generate network traffic - coordinate with network admin
- Rate limiting prevents overwhelming targets
- Results may contain sensitive information - restrict access
- Authorized scanning only - verify permission before scanning external targets

## Dependencies

- Nuclei v3.5.1+
- Python 3.10+
- asyncio
- aiofiles
- pydantic

## References

- [Nuclei](https://github.com/projectdiscovery/nuclei) - Main vulnerability scanner
- [nuclei-mcp](https://github.com/addcontent/nuclei-mcp) - Reference MCP implementation
- [ExternalAttacker-MCP](https://github.com/MorDavid/ExternalAttacker-MCP) - Security testing MCP

## License

MIT License - Part of the Mac Pro 5,1 Agentic System
