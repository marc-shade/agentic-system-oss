# Security Architecture

[![Part of Agentic System](https://img.shields.io/badge/Part_of-Agentic_System-brightgreen)](https://github.com/marc-shade/agentic-system-oss)

The Agentic System implements defense-in-depth security through three complementary layers: runtime hook protection, dedicated security MCP servers, and encryption/PKI infrastructure.

## Layered Defense Model

```
┌─────────────────────────────────────────────────────────────────┐
│  Layer 3: Encryption & PKI (claude-code-security)              │
│  ├─ AES-256-GCM data encryption                                │
│  ├─ X.509 PKI for node authentication                          │
│  └─ Token vault for credential management                      │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Security MCP Servers (9 servers)                     │
│  ├─ Active Monitoring                                          │
│  │   ├─ network-scanner-mcp  : ARP discovery, port scanning   │
│  │   ├─ hids-mcp             : Host intrusion detection        │
│  │   └─ dos-detector-mcp     : DoS attack detection            │
│  ├─ Vulnerability Assessment                                    │
│  │   ├─ security-scanner-mcp : Nuclei vulnerability scanning   │
│  │   ├─ nuclei-mcp           : Template management             │
│  │   └─ web-vuln-scanner-mcp : OWASP web security testing      │
│  ├─ Intelligence                                                │
│  │   └─ threat-intel-mcp     : IOC feeds, threat scoring       │
│  └─ Analysis                                                    │
│      ├─ fraud-detection-mcp  : ML-based anomaly detection      │
│      └─ security-auditor-mcp : Policy enforcement              │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Runtime Hook Protection (pre/post tool hooks)        │
│  ├─ Dangerous command blocking                                  │
│  ├─ Injection detection (SQL, command, path traversal)         │
│  ├─ Credential leak prevention                                  │
│  └─ Audit logging                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Layer 1: Hook-Based Runtime Protection

Located in `claude-config/hooks/`, these Python scripts run on every tool call.

### Pre-Tool-Use Hook (`pre-tool-use.py`)

Validates tool calls **before** execution. Blocks dangerous operations and detects injection attempts.

**Capabilities:**
- Dangerous command detection: `rm -rf /`, `dd` to disk, fork bombs, `chmod 777 /`, pipe-to-shell patterns
- SQL injection detection: `UNION SELECT`, `DROP TABLE`, `DELETE FROM`, tautology patterns
- Command injection detection: shell metacharacters, command substitution, chaining
- Path traversal detection: `../../../` patterns, access to `/etc/passwd`, `/etc/shadow`
- Credential leak prevention: scans arguments for API keys (Anthropic, OpenAI, Groq, Google, GitHub, Slack), hardcoded passwords
- Sensitive path warnings: `.env`, `.ssh/`, credentials files, private keys

**Exit codes:**
- `0` = Allow execution
- `1` = Block execution (message shown to user via stderr)

### Post-Tool-Use Hook (`post-tool-use.py`)

Analyzes tool results **after** execution for security and operational insights.

**Capabilities:**
- Credential boundary scanning: detects if tool output contains API keys, passwords, private keys, bearer tokens, AWS keys
- Output size monitoring: warns on large outputs (>50K chars) and very large outputs (>200K chars)
- Slow operation tracking: logs operations exceeding 30 seconds
- Failure tracking: records tool failures with argument summaries for debugging
- Audit logging: all tool calls logged to `~/.claude/hooks/logs/` as JSONL files

**Log files:**
- `tool_usage_YYYYMMDD.jsonl` - Daily tool usage audit trail
- `slow_operations.jsonl` - Operations exceeding time thresholds
- `failures.jsonl` - Tool failure records

## Layer 2: Security MCP Servers

Nine dedicated MCP servers providing comprehensive security monitoring and assessment.

### Active Monitoring

#### network-scanner-mcp
Network awareness through device discovery and monitoring.
- **ARP scanning**: Discover all devices on the local network
- **Port scanning**: TCP port scanning with service fingerprinting
- **Cluster monitoring**: Track cluster node health with ping checks
- **Alert daemon**: Continuous monitoring with configurable alerts
- **Anomaly detection**: Alert on unknown devices joining the network

#### hids-mcp
Host-based intrusion detection system.
- **File integrity monitoring**: Detect unauthorized file modifications
- **Process monitoring**: Track suspicious process activity
- **Anomaly detection**: Baseline comparison for host behavior
- **Security assessment**: Evaluate host security posture

#### dos-detector-mcp
Denial-of-service attack detection.
- **Traffic analysis**: Monitor network traffic patterns
- **Attack recognition**: Detect SYN floods, HTTP floods, amplification attacks
- **Rate limiting**: Identify abnormal request rates
- **Mitigation triggers**: Automated response recommendations

### Vulnerability Assessment

#### security-scanner-mcp
Nuclei-based vulnerability scanning with embedding-based analysis.
- **Target scanning**: Scan URLs or IPs with customizable severity filters
- **Cluster scanning**: Batch scan all cluster nodes
- **Anomaly detection**: Embedding-based comparison to detect novel vulnerabilities
- **Priority scoring**: Semantic similarity scoring for remediation prioritization
- **Scan history**: Track and retrieve past scan results

#### nuclei-mcp
Direct Nuclei template management interface.
- **Template listing**: Browse available templates by tag and severity
- **Template updates**: Keep vulnerability signatures current
- **Scan orchestration**: Configure and execute targeted scans
- **Result analysis**: Parse and present scan findings

#### web-vuln-scanner-mcp
Web application security testing.
- **OWASP coverage**: Test for common web vulnerabilities
- **Automated scanning**: Configurable scan profiles
- **Report generation**: Structured vulnerability reports
- **Integration**: Works with security-scanner for comprehensive coverage

### Intelligence

#### threat-intel-mcp
Multi-source threat intelligence aggregation.
- **Feeds**: abuse.ch ThreatFox, URLhaus, CISA KEV, Feodo Tracker
- **IOC lookup**: Query by IP, domain, URL, or file hash
- **Threat scoring**: Risk assessment with confidence levels
- **Bulk analysis**: Process network scan results for threat correlation
- **Alert integration**: Voice and cluster notifications for critical threats

### Analysis

#### fraud-detection-mcp
ML-powered fraud and anomaly detection.
- **Feature engineering**: Extract 46 features from transactions
- **GNN detection**: Graph neural network for relationship-based fraud
- **Autoencoder**: PyTorch anomaly detection model
- **Explainability**: SHAP-based decision explanations
- **Async inference**: High-throughput prediction with caching

#### security-auditor-mcp
Security policy enforcement and compliance.
- **Policy validation**: Check configurations against security policies
- **Compliance auditing**: Automated security review procedures
- **Code review**: Security-focused code analysis
- **Report generation**: Audit reports with findings and recommendations

## Layer 3: Encryption and PKI

For data-at-rest encryption, PKI-based authentication, and secure credential management, see [claude-code-security](https://github.com/marc-shade/claude-code-security).

**Key capabilities:**
- AES-256-GCM encryption for sensitive data
- X.509 certificate-based PKI for inter-node authentication
- Token vault for centralized credential management
- Secure key generation and rotation

This layer is maintained as a separate repository to allow independent use and to keep cryptographic code focused and auditable.

## Configuration

### Enabling Security Hooks

Add hooks to your Claude Code settings (`~/.claude/settings.json`):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "type": "command",
        "command": "python3 /path/to/claude-config/hooks/pre-tool-use.py"
      }
    ],
    "PostToolUse": [
      {
        "type": "command",
        "command": "python3 /path/to/claude-config/hooks/post-tool-use.py"
      }
    ]
  }
}
```

### Enabling Security MCP Servers

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "threat-intel": {
      "command": "python3",
      "args": ["/path/to/mcp-servers/threat-intel-mcp/server.py"]
    },
    "security-scanner": {
      "command": "python3",
      "args": ["-m", "security_scanner.server"],
      "cwd": "/path/to/mcp-servers/security-scanner-mcp/src"
    },
    "network-scanner": {
      "command": "python3",
      "args": ["-m", "network_scanner_mcp.server"],
      "cwd": "/path/to/mcp-servers/network-scanner-mcp/src"
    },
    "security-auditor": {
      "command": "python3",
      "args": ["/path/to/mcp-servers/security-auditor-mcp/server.py"]
    }
  }
}
```

### Recommended Security Server Combinations

**Minimal Security Setup:**
- `threat-intel-mcp` (threat awareness)
- `security-scanner-mcp` (vulnerability scanning)
- Pre/post hooks (runtime protection)

**Full Security Stack:**
- All 9 security MCP servers
- Pre/post tool hooks
- [claude-code-security](https://github.com/marc-shade/claude-code-security) for encryption

**Network Operations:**
- `network-scanner-mcp` (discovery)
- `hids-mcp` (host monitoring)
- `dos-detector-mcp` (attack detection)
- `threat-intel-mcp` (threat correlation)

## Security Best Practices

1. **Always enable hooks** - The pre/post tool hooks are the first line of defense
2. **Keep threat feeds current** - Run `threat_sync` regularly to update IOC databases
3. **Scan periodically** - Schedule regular vulnerability scans across your infrastructure
4. **Review audit logs** - Check `~/.claude/hooks/logs/` for unusual patterns
5. **Rotate credentials** - Use the token vault for credential management, rotate regularly
6. **Network segmentation** - Use network-scanner to monitor for unauthorized devices
7. **All services on localhost** - Bind services to `127.0.0.1`, never `0.0.0.0`
8. **Parameterized queries** - Never use f-strings for SQL; always use parameterized queries
9. **No shell=True** - Use `subprocess` with `shell=False` and argument lists
10. **Fail closed** - Authentication checks should deny by default when modules are unavailable
