# Security Auditor MCP Server

AI-powered security vulnerability scanning and remediation for codebases.

## Features

- **Codebase Scanning**: Detect security vulnerabilities in files and directories
- **Change Validation**: Verify proposed code changes don't introduce security issues
- **Patch Generation**: Automatically generate fixes for identified vulnerabilities
- **Severity Classification**: Issues categorized as critical/high/medium/low

## MCP Tools

| Tool | Description |
|------|-------------|
| `scan_codebase` | Scan a directory or file for security vulnerabilities |
| `validate_change` | Check if a proposed code change is safe |
| `generate_patch` | Generate a code patch to fix a specific vulnerability |

## Vulnerability Detection

Detects common security issues including:
- SQL injection
- Cross-site scripting (XSS)
- Command injection
- Path traversal
- Hardcoded credentials
- Insecure configurations

## Requirements

- Python 3.10+
- mcp SDK

## Installation

```bash
pip install mcp
```

## Usage

```bash
python server.py
```

## Integration

Works with Claude Code, Gemini CLI, and other MCP-compatible AI assistants to provide automated security auditing during development.

## License

MIT
