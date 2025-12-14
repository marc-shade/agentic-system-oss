#!/usr/bin/env python3
"""
Web Vulnerability Scanner MCP Server

OWASP Top 10 vulnerability detection for web applications.
For authorized security testing only.
"""

import json
import re
import ssl
import socket
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, urljoin, parse_qs, urlencode

import aiohttp
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("web-vuln-scanner")

# Security headers to check
SECURITY_HEADERS = {
    "Content-Security-Policy": {
        "severity": "high",
        "description": "Prevents XSS, clickjacking, and code injection"
    },
    "X-Content-Type-Options": {
        "severity": "medium",
        "expected": "nosniff",
        "description": "Prevents MIME type sniffing"
    },
    "X-Frame-Options": {
        "severity": "medium",
        "expected": ["DENY", "SAMEORIGIN"],
        "description": "Prevents clickjacking attacks"
    },
    "X-XSS-Protection": {
        "severity": "low",
        "expected": "1; mode=block",
        "description": "Legacy XSS filter (deprecated but still useful)"
    },
    "Strict-Transport-Security": {
        "severity": "high",
        "description": "Enforces HTTPS connections"
    },
    "Referrer-Policy": {
        "severity": "low",
        "description": "Controls referrer information"
    },
    "Permissions-Policy": {
        "severity": "medium",
        "description": "Controls browser features"
    }
}

# SQL injection test payloads (safe - detection only)
SQLI_PAYLOADS = [
    "'",
    "\"",
    "' OR '1'='1",
    "\" OR \"1\"=\"1",
    "' OR 1=1--",
    "1' ORDER BY 1--",
    "1 UNION SELECT NULL--",
    "'; DROP TABLE--",
]

# SQL error patterns
SQLI_ERRORS = [
    r"SQL syntax.*MySQL",
    r"Warning.*mysql_",
    r"PostgreSQL.*ERROR",
    r"ORA-\d{5}",
    r"Microsoft.*ODBC.*SQL Server",
    r"SQLite.*error",
    r"sqlite_",
    r"Unclosed quotation mark",
    r"quoted string not properly terminated",
]

# XSS test payloads (safe - detection only)
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "<svg/onload=alert('XSS')>",
    "javascript:alert('XSS')",
    "'><script>alert('XSS')</script>",
    "\"><script>alert('XSS')</script>",
]

# Common sensitive paths
SENSITIVE_PATHS = [
    "/.git/config",
    "/.env",
    "/.htaccess",
    "/wp-config.php",
    "/config.php",
    "/admin/",
    "/phpinfo.php",
    "/server-status",
    "/robots.txt",
    "/sitemap.xml",
    "/.svn/entries",
    "/backup/",
    "/db/",
    "/sql/",
    "/logs/",
    "/debug/",
]


async def fetch_url(url: str, timeout: int = 10, method: str = "GET", data: dict = None) -> dict:
    """Fetch URL and return response details."""
    try:
        async with aiohttp.ClientSession() as session:
            kwargs = {"timeout": aiohttp.ClientTimeout(total=timeout), "ssl": False}
            if data:
                kwargs["data"] = data

            async with getattr(session, method.lower())(url, **kwargs) as response:
                text = await response.text()
                return {
                    "success": True,
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": text[:50000],  # Limit body size
                    "url": str(response.url)
                }
    except aiohttp.ClientError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@mcp.tool()
async def analyze_security_headers(url: str) -> str:
    """
    Analyze HTTP security headers for a URL.

    Args:
        url: Target URL to analyze

    Returns:
        JSON with security header analysis
    """
    response = await fetch_url(url)

    if not response["success"]:
        return json.dumps({"success": False, "error": response["error"]})

    headers = {k.lower(): v for k, v in response["headers"].items()}
    findings = []
    score = 100

    for header, config in SECURITY_HEADERS.items():
        header_lower = header.lower()
        present = header_lower in headers
        value = headers.get(header_lower, "")

        finding = {
            "header": header,
            "present": present,
            "value": value if present else None,
            "severity": config["severity"],
            "description": config["description"]
        }

        if not present:
            finding["issue"] = f"Missing {header} header"
            if config["severity"] == "high":
                score -= 20
            elif config["severity"] == "medium":
                score -= 10
            else:
                score -= 5
        elif "expected" in config:
            expected = config["expected"]
            if isinstance(expected, list):
                if value not in expected:
                    finding["issue"] = f"Unexpected value: {value}"
                    score -= 5
            elif value != expected:
                finding["issue"] = f"Expected '{expected}', got '{value}'"
                score -= 5

        findings.append(finding)

    # Check for information disclosure headers
    info_headers = ["server", "x-powered-by", "x-aspnet-version"]
    for h in info_headers:
        if h in headers:
            findings.append({
                "header": h.title(),
                "present": True,
                "value": headers[h],
                "severity": "low",
                "issue": "Information disclosure - reveals server technology",
                "description": "Should be removed or obscured"
            })
            score -= 5

    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"

    return json.dumps({
        "success": True,
        "url": url,
        "score": max(0, score),
        "grade": grade,
        "findings": findings,
        "recommendations": [
            f["issue"] for f in findings if "issue" in f
        ]
    }, indent=2)


@mcp.tool()
async def check_ssl_config(hostname: str, port: int = 443) -> str:
    """
    Check SSL/TLS configuration for a host.

    Args:
        hostname: Target hostname
        port: SSL port (default: 443)

    Returns:
        JSON with SSL/TLS configuration analysis
    """
    findings = []
    score = 100

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection((hostname, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert(binary_form=True)
                protocol = ssock.version()
                cipher = ssock.cipher()

        # Check protocol version
        protocol_scores = {
            "TLSv1.3": 0,
            "TLSv1.2": 0,
            "TLSv1.1": -20,
            "TLSv1": -30,
            "SSLv3": -50,
            "SSLv2": -50
        }

        protocol_deduction = protocol_scores.get(protocol, -10)
        score += protocol_deduction

        findings.append({
            "check": "Protocol Version",
            "value": protocol,
            "status": "good" if protocol in ("TLSv1.3", "TLSv1.2") else "warning" if protocol == "TLSv1.1" else "critical",
            "note": "TLS 1.2 or 1.3 recommended"
        })

        # Check cipher suite
        if cipher:
            cipher_name = cipher[0]
            findings.append({
                "check": "Cipher Suite",
                "value": cipher_name,
                "status": "info",
                "note": "Review cipher strength"
            })

            # Check for weak ciphers
            weak_ciphers = ["RC4", "DES", "3DES", "MD5", "NULL", "EXPORT"]
            for weak in weak_ciphers:
                if weak in cipher_name.upper():
                    findings.append({
                        "check": "Weak Cipher",
                        "value": cipher_name,
                        "status": "critical",
                        "note": f"Weak cipher: {weak}"
                    })
                    score -= 20

        # Try to get certificate details via higher-level check
        try:
            context2 = ssl.create_default_context()
            with socket.create_connection((hostname, port), timeout=10) as sock2:
                with context2.wrap_socket(sock2, server_hostname=hostname) as ssock2:
                    cert_info = ssock2.getpeercert()

                    if cert_info:
                        # Check expiration
                        not_after = cert_info.get('notAfter')
                        if not_after:
                            exp_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                            days_until_expiry = (exp_date - datetime.now()).days

                            findings.append({
                                "check": "Certificate Expiration",
                                "value": not_after,
                                "days_until_expiry": days_until_expiry,
                                "status": "good" if days_until_expiry > 30 else "warning" if days_until_expiry > 0 else "critical"
                            })

                            if days_until_expiry <= 0:
                                score -= 50
                            elif days_until_expiry <= 30:
                                score -= 20

                        # Check subject
                        subject = dict(x[0] for x in cert_info.get('subject', []))
                        findings.append({
                            "check": "Certificate Subject",
                            "value": subject.get('commonName', 'unknown'),
                            "status": "info"
                        })

        except ssl.SSLCertVerificationError as e:
            findings.append({
                "check": "Certificate Validation",
                "value": str(e),
                "status": "warning",
                "note": "Certificate validation failed"
            })
            score -= 15
        except Exception:
            pass

    except socket.timeout:
        return json.dumps({"success": False, "error": "Connection timeout"})
    except socket.gaierror:
        return json.dumps({"success": False, "error": "DNS resolution failed"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

    grade = "A" if score >= 90 else "B" if score >= 80 else "C" if score >= 70 else "D" if score >= 60 else "F"

    return json.dumps({
        "success": True,
        "hostname": hostname,
        "port": port,
        "score": max(0, score),
        "grade": grade,
        "findings": findings,
        "recommendations": [
            "Upgrade to TLS 1.3 if possible",
            "Disable TLS 1.0 and 1.1",
            "Use strong cipher suites",
            "Enable HSTS header"
        ] if score < 90 else ["SSL configuration looks good"]
    }, indent=2)


@mcp.tool()
async def test_sqli_params(
    url: str,
    test_params: Optional[list] = None,
    timeout: int = 10
) -> str:
    """
    Test URL parameters for SQL injection vulnerabilities.

    AUTHORIZED TESTING ONLY - only test systems you own or have permission to test.

    Args:
        url: Target URL with parameters (e.g., http://example.com/page?id=1)
        test_params: Specific parameters to test (default: all)
        timeout: Request timeout in seconds

    Returns:
        JSON with SQLi test results
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    params = parse_qs(parsed.query)

    if not params:
        return json.dumps({
            "success": False,
            "error": "No URL parameters found to test"
        })

    if test_params:
        params = {k: v for k, v in params.items() if k in test_params}

    findings = []
    vulnerable_params = []

    # Get baseline response
    baseline = await fetch_url(url, timeout)
    if not baseline["success"]:
        return json.dumps({"success": False, "error": f"Could not reach target: {baseline['error']}"})

    baseline_status = baseline["status"]
    baseline_length = len(baseline["body"])

    for param, values in params.items():
        original_value = values[0] if values else ""

        for payload in SQLI_PAYLOADS:
            # Build test URL
            test_params_dict = {k: v[0] for k, v in params.items()}
            test_params_dict[param] = original_value + payload
            test_url = f"{base_url}?{urlencode(test_params_dict)}"

            response = await fetch_url(test_url, timeout)

            if response["success"]:
                body = response["body"]

                # Check for SQL error patterns
                for pattern in SQLI_ERRORS:
                    if re.search(pattern, body, re.IGNORECASE):
                        findings.append({
                            "type": "sql_error",
                            "parameter": param,
                            "payload": payload,
                            "evidence": pattern,
                            "severity": "high"
                        })
                        if param not in vulnerable_params:
                            vulnerable_params.append(param)
                        break

                # Check for significant response changes
                length_diff = abs(len(body) - baseline_length)
                if length_diff > baseline_length * 0.5:  # >50% change
                    findings.append({
                        "type": "response_anomaly",
                        "parameter": param,
                        "payload": payload,
                        "baseline_length": baseline_length,
                        "test_length": len(body),
                        "severity": "medium",
                        "note": "Significant response change - investigate manually"
                    })

    return json.dumps({
        "success": True,
        "url": url,
        "parameters_tested": list(params.keys()),
        "payloads_tested": len(SQLI_PAYLOADS),
        "vulnerable_parameters": vulnerable_params,
        "findings": findings,
        "risk_level": "high" if vulnerable_params else "low",
        "note": "AUTHORIZED TESTING ONLY - manual verification recommended"
    }, indent=2)


@mcp.tool()
async def test_xss_reflection(
    url: str,
    test_params: Optional[list] = None
) -> str:
    """
    Test for reflected XSS vulnerabilities.

    AUTHORIZED TESTING ONLY - only test systems you own or have permission to test.

    Args:
        url: Target URL with parameters
        test_params: Specific parameters to test (default: all)

    Returns:
        JSON with XSS test results
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    params = parse_qs(parsed.query)

    if not params:
        return json.dumps({
            "success": False,
            "error": "No URL parameters found to test"
        })

    if test_params:
        params = {k: v for k, v in params.items() if k in test_params}

    findings = []
    vulnerable_params = []

    for param, values in params.items():
        original_value = values[0] if values else ""

        for payload in XSS_PAYLOADS:
            # Build test URL
            test_params_dict = {k: v[0] for k, v in params.items()}
            test_params_dict[param] = payload
            test_url = f"{base_url}?{urlencode(test_params_dict)}"

            response = await fetch_url(test_url)

            if response["success"]:
                body = response["body"]

                # Check if payload is reflected unencoded
                if payload in body:
                    findings.append({
                        "type": "reflected_xss",
                        "parameter": param,
                        "payload": payload,
                        "severity": "high",
                        "note": "Payload reflected unencoded in response"
                    })
                    if param not in vulnerable_params:
                        vulnerable_params.append(param)
                    break

                # Check for partial reflection (might indicate encoding bypass needed)
                payload_part = payload[:10]
                if payload_part in body and payload not in body:
                    findings.append({
                        "type": "partial_reflection",
                        "parameter": param,
                        "payload": payload,
                        "severity": "medium",
                        "note": "Partial reflection - some encoding applied, may be bypassable"
                    })

    return json.dumps({
        "success": True,
        "url": url,
        "parameters_tested": list(params.keys()),
        "payloads_tested": len(XSS_PAYLOADS),
        "vulnerable_parameters": vulnerable_params,
        "findings": findings,
        "risk_level": "high" if vulnerable_params else "low",
        "recommendations": [
            "Implement Content-Security-Policy header",
            "Use context-aware output encoding",
            "Validate and sanitize all user input"
        ] if vulnerable_params else ["No reflected XSS found - test with additional payloads for comprehensive coverage"],
        "note": "AUTHORIZED TESTING ONLY"
    }, indent=2)


@mcp.tool()
async def scan_sensitive_paths(url: str, custom_paths: Optional[list] = None) -> str:
    """
    Scan for sensitive/exposed paths and files.

    Args:
        url: Base URL to scan
        custom_paths: Additional paths to check

    Returns:
        JSON with discovered sensitive paths
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    paths_to_check = SENSITIVE_PATHS.copy()
    if custom_paths:
        paths_to_check.extend(custom_paths)

    discovered = []
    interesting = []

    for path in paths_to_check:
        full_url = urljoin(base_url, path)
        response = await fetch_url(full_url)

        if response["success"]:
            status = response["status"]
            size = len(response["body"])

            result = {
                "path": path,
                "url": full_url,
                "status": status,
                "size": size
            }

            if status == 200:
                result["severity"] = "high" if any(s in path for s in [".git", ".env", "config", "sql"]) else "medium"
                result["note"] = "Accessible - review contents"
                discovered.append(result)
            elif status in (301, 302, 403):
                result["severity"] = "low"
                result["note"] = f"Exists but {status}"
                interesting.append(result)

    return json.dumps({
        "success": True,
        "base_url": base_url,
        "paths_checked": len(paths_to_check),
        "discovered": discovered,
        "interesting": interesting[:20],
        "risk_level": "high" if discovered else "low",
        "recommendations": [
            "Remove or protect discovered sensitive files",
            "Add proper access controls",
            "Review web server configuration"
        ] if discovered else ["No obvious sensitive paths found"]
    }, indent=2)


@mcp.tool()
async def check_info_disclosure(url: str) -> str:
    """
    Check for information disclosure vulnerabilities.

    Args:
        url: Target URL to analyze

    Returns:
        JSON with information disclosure findings
    """
    response = await fetch_url(url)

    if not response["success"]:
        return json.dumps({"success": False, "error": response["error"]})

    body = response["body"]
    headers = response["headers"]

    findings = []

    # Check headers for info disclosure
    disclosure_headers = {
        "Server": "Web server version disclosed",
        "X-Powered-By": "Technology stack disclosed",
        "X-AspNet-Version": "ASP.NET version disclosed",
        "X-AspNetMvc-Version": "ASP.NET MVC version disclosed"
    }

    for header, message in disclosure_headers.items():
        if header in headers:
            findings.append({
                "type": "header_disclosure",
                "header": header,
                "value": headers[header],
                "severity": "low",
                "message": message
            })

    # Check body for sensitive patterns
    patterns = [
        (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\'][^"\']+["\']', "Hardcoded password", "high"),
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][^"\']+["\']', "API key exposed", "high"),
        (r'(?i)(secret[_-]?key|secretkey)\s*[=:]\s*["\'][^"\']+["\']', "Secret key exposed", "high"),
        (r'(?i)(aws[_-]?access|aws[_-]?secret)', "AWS credentials", "high"),
        (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', "Internal IP address", "low"),
        (r'(?i)stack\s*trace|exception|error.*line\s*\d+', "Stack trace/debug info", "medium"),
        (r'(?i)<!-- .*TODO.*-->', "Developer comments", "low"),
        (r'(?i)/home/[a-z0-9_]+/', "Server path disclosure", "medium"),
        (r'(?i)c:\\\\[a-z0-9_\\\\]+', "Windows path disclosure", "medium"),
    ]

    for pattern, description, severity in patterns:
        matches = re.findall(pattern, body)
        if matches:
            findings.append({
                "type": "content_disclosure",
                "pattern": description,
                "matches": len(matches) if len(matches) > 5 else matches,
                "severity": severity
            })

    return json.dumps({
        "success": True,
        "url": url,
        "findings": findings,
        "risk_level": "high" if any(f["severity"] == "high" for f in findings) else "medium" if findings else "low",
        "recommendations": [
            "Remove or obfuscate server version headers",
            "Review and remove hardcoded credentials",
            "Disable debug/stack trace output in production",
            "Remove developer comments from production code"
        ] if findings else ["No obvious information disclosure found"]
    }, indent=2)


@mcp.tool()
async def generate_vuln_report(url: str) -> str:
    """
    Generate comprehensive vulnerability scan report.

    Args:
        url: Target URL for full scan

    Returns:
        JSON with complete vulnerability report
    """
    parsed = urlparse(url)
    hostname = parsed.netloc.split(':')[0]

    report = {
        "success": True,
        "target": url,
        "scan_date": datetime.now().isoformat(),
        "summary": {
            "total_checks": 0,
            "high_severity": 0,
            "medium_severity": 0,
            "low_severity": 0
        },
        "sections": []
    }

    # Security Headers
    headers_result = json.loads(await analyze_security_headers(url))
    if headers_result["success"]:
        report["sections"].append({
            "name": "Security Headers",
            "grade": headers_result.get("grade", "N/A"),
            "findings": headers_result.get("findings", [])
        })
        for f in headers_result.get("findings", []):
            if "issue" in f:
                if f["severity"] == "high":
                    report["summary"]["high_severity"] += 1
                elif f["severity"] == "medium":
                    report["summary"]["medium_severity"] += 1
                else:
                    report["summary"]["low_severity"] += 1
        report["summary"]["total_checks"] += 1

    # SSL/TLS (if HTTPS)
    if parsed.scheme == "https":
        ssl_result = json.loads(await check_ssl_config(hostname))
        if ssl_result["success"]:
            report["sections"].append({
                "name": "SSL/TLS Configuration",
                "grade": ssl_result.get("grade", "N/A"),
                "findings": ssl_result.get("findings", [])
            })
            report["summary"]["total_checks"] += 1

    # Information Disclosure
    info_result = json.loads(await check_info_disclosure(url))
    if info_result["success"]:
        report["sections"].append({
            "name": "Information Disclosure",
            "risk_level": info_result.get("risk_level", "unknown"),
            "findings": info_result.get("findings", [])
        })
        for f in info_result.get("findings", []):
            if f["severity"] == "high":
                report["summary"]["high_severity"] += 1
            elif f["severity"] == "medium":
                report["summary"]["medium_severity"] += 1
            else:
                report["summary"]["low_severity"] += 1
        report["summary"]["total_checks"] += 1

    # Sensitive Paths
    paths_result = json.loads(await scan_sensitive_paths(url))
    if paths_result["success"]:
        report["sections"].append({
            "name": "Sensitive Paths",
            "risk_level": paths_result.get("risk_level", "unknown"),
            "discovered": paths_result.get("discovered", [])
        })
        report["summary"]["high_severity"] += len(paths_result.get("discovered", []))
        report["summary"]["total_checks"] += 1

    # Overall risk
    total_issues = report["summary"]["high_severity"] + report["summary"]["medium_severity"] + report["summary"]["low_severity"]

    if report["summary"]["high_severity"] > 0:
        report["overall_risk"] = "HIGH"
    elif report["summary"]["medium_severity"] > 2:
        report["overall_risk"] = "MEDIUM"
    elif total_issues > 0:
        report["overall_risk"] = "LOW"
    else:
        report["overall_risk"] = "MINIMAL"

    report["recommendations"] = [
        "Address high severity findings immediately",
        "Review and remediate medium severity issues",
        "Consider low severity findings for defense in depth"
    ] if total_issues > 0 else ["No critical findings - continue monitoring"]

    return json.dumps(report, indent=2)


def main():
    """Run the web vulnerability scanner MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
