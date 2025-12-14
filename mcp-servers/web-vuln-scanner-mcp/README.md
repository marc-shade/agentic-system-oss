# Web Vulnerability Scanner MCP Server

OWASP Top 10 vulnerability detection for web applications.

## Features

- **SQL Injection Detection**: Test for SQLi vulnerabilities
- **XSS Detection**: Cross-Site Scripting checks
- **Security Headers Analysis**: Check for missing security headers
- **SSL/TLS Analysis**: Certificate and configuration checks
- **Directory Traversal**: Path traversal vulnerability testing
- **Information Disclosure**: Sensitive data exposure checks
- **CSRF Detection**: Cross-Site Request Forgery analysis

## Tools

| Tool | Description |
|------|-------------|
| `analyze_security_headers` | Check HTTP security headers |
| `check_ssl_config` | Analyze SSL/TLS configuration |
| `test_sqli_params` | Test URL parameters for SQL injection |
| `test_xss_reflection` | Test for reflected XSS |
| `scan_directories` | Find hidden directories and files |
| `check_info_disclosure` | Find information leakage |
| `generate_vuln_report` | Comprehensive vulnerability report |

## Security Headers Checked

- Content-Security-Policy (CSP)
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Strict-Transport-Security (HSTS)
- Referrer-Policy
- Permissions-Policy

## IMPORTANT: Authorized Use Only

This tool is for **authorized security testing only**:
- Only scan systems you own or have explicit permission to test
- Do not use against production systems without approval
- Follow responsible disclosure practices
