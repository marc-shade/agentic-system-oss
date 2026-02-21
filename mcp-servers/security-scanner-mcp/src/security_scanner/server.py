#!/usr/bin/env python3
"""
Security Scanner MCP Server - Nuclei vulnerability scanning integration
Provides automated security scanning capabilities with cluster distribution

Integrates with text embeddings for:
- Anomaly detection in security findings
- Pattern recognition across scan results
- Importance scoring for vulnerability prioritization
"""
import platform

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastmcp import FastMCP


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        for candidate in [Path.home() / "agentic-system", Path("/opt/agentic-system")]:
            if candidate.exists():
                return candidate
    elif system == "Linux":
        for candidate in [Path.home() / "agentic-system", Path("/mnt/agentic-system")]:
            if candidate.exists():
                return candidate
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

# Embedding integration for anomaly detection
_TPU_AVAILABLE = False
_text_model = None

try:
    from sentence_transformers import SentenceTransformer
    _text_model = SentenceTransformer('all-MiniLM-L6-v2')
    _TPU_AVAILABLE = True  # We have embedding capability
except ImportError:
    pass  # Embedding features will be disabled

# Server configuration
NUCLEI_BIN = os.path.expanduser("~/go/bin/nuclei")
SCAN_RESULTS_DIR = Path(os.path.join(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)), "security-scans"))
SCAN_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Cluster nodes - loaded from environment or config file
def _load_cluster_nodes() -> dict:
    """
    Load cluster node configuration from environment variable.

    Set CLUSTER_NODES_JSON env var with JSON like:
    {"node1": "198.51.100.1", "node2": "198.51.100.2"}
    """
    import json
    env_config = os.environ.get("CLUSTER_NODES_JSON")
    if env_config:
        try:
            return json.loads(env_config)
        except json.JSONDecodeError:
            pass
    return {}

CLUSTER_NODES = _load_cluster_nodes()

# Initialize FastMCP server
mcp = FastMCP("security-scanner")


@mcp.tool()
async def scan_target(
    target: str,
    severity: Optional[str] = "medium,high,critical",
    rate_limit: int = 150,
    timeout: int = 300
) -> str:
    """
    Scan a target URL or IP with Nuclei vulnerability scanner.

    Args:
        target: Target URL or IP address to scan
        severity: Comma-separated severity levels (info, low, medium, high, critical)
        rate_limit: Requests per second (default: 150)
        timeout: Scan timeout in seconds (default: 300)

    Returns:
        JSON string with scan results
    """
    scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(target) % 10000}"
    output_file = SCAN_RESULTS_DIR / f"{scan_id}.jsonl"

    cmd = [
        NUCLEI_BIN,
        "-target", target,
        "-json",
        "-severity", severity,
        "-rate-limit", str(rate_limit),
        "-timeout", str(timeout),
        "-o", str(output_file)
    ]

    start_time = datetime.now()

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await asyncio.wait_for(process.communicate(), timeout=timeout + 30)

        duration = (datetime.now() - start_time).total_seconds()

        findings = []
        if output_file.exists():
            with open(output_file, 'r') as f:
                for line in f:
                    if line.strip():
                        findings.append(json.loads(line))

        severity_counts = {}
        for finding in findings:
            sev = finding.get("info", {}).get("severity", "info")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        metadata = {
            "scan_id": scan_id,
            "target": target,
            "timestamp": datetime.now().isoformat(),
            "output_file": str(output_file)
        }

        metadata_file = SCAN_RESULTS_DIR / f"{scan_id}_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        result = {
            "success": True,
            "scan_id": scan_id,
            "target": target,
            "total_findings": len(findings),
            "severity_breakdown": severity_counts,
            "duration_seconds": int(duration),
            "findings_preview": findings[:10],
            "output_file": str(output_file)
        }

        return json.dumps(result, indent=2)

    except asyncio.TimeoutError:
        return json.dumps({"success": False, "error": f"Scan timed out after {timeout} seconds"})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def scan_cluster_nodes(
    scan_type: str = "comprehensive",
    severity: str = "medium,high,critical"
) -> str:
    """
    Scan all nodes in the agentic cluster for vulnerabilities.

    Args:
        scan_type: Type of scan - "quick", "comprehensive", "full", "web", or "api"
        severity: Comma-separated severity levels to check

    Returns:
        JSON string with cluster scan results
    """
    results = []

    for node_name, node_ip in CLUSTER_NODES.items():
        result = await scan_target(node_ip, severity)
        result_data = json.loads(result)
        result_data["node_name"] = node_name
        results.append(result_data)

    total_findings = sum(r.get("total_findings", 0) for r in results)

    summary = {
        "cluster_scan_completed": True,
        "nodes_scanned": len(CLUSTER_NODES),
        "total_findings": total_findings,
        "scan_results": results,
        "timestamp": datetime.now().isoformat()
    }

    return json.dumps(summary, indent=2)


@mcp.tool()
async def list_templates(
    tag: Optional[str] = None,
    severity: Optional[str] = None
) -> str:
    """
    List available Nuclei templates by tag or severity.

    Args:
        tag: Filter by tag (e.g., cve, exposure, misconfiguration)
        severity: Filter by severity (info, low, medium, high, critical)

    Returns:
        JSON string with template list
    """
    cmd = [NUCLEI_BIN, "-tl"]

    if tag:
        cmd.extend(["-tags", tag])
    if severity:
        cmd.extend(["-severity", severity])

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()

        templates = [t.strip() for t in stdout.decode().strip().split('\n') if t.strip()]

        return json.dumps({
            "success": True,
            "total_templates": len(templates),
            "templates": templates[:200],
            "filters": {"tag": tag, "severity": severity}
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def update_templates() -> str:
    """
    Update Nuclei templates to latest version.

    Returns:
        JSON string with update result
    """
    try:
        process = await asyncio.create_subprocess_exec(
            NUCLEI_BIN, "-update-templates",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()

        return json.dumps({
            "success": True,
            "output": stdout.decode().strip()
        }, indent=2)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


@mcp.tool()
async def get_scan_results(
    scan_id: str,
    limit: int = 100
) -> str:
    """
    Retrieve results from a previous scan.

    Args:
        scan_id: Scan ID to retrieve
        limit: Maximum number of results to return (default: 100)

    Returns:
        JSON string with scan results
    """
    result_file = SCAN_RESULTS_DIR / f"{scan_id}.jsonl"
    metadata_file = SCAN_RESULTS_DIR / f"{scan_id}_metadata.json"

    if not result_file.exists():
        return json.dumps({"success": False, "error": "Scan not found"})

    results = []
    with open(result_file, 'r') as f:
        for line in f:
            if line.strip():
                results.append(json.loads(line))
                if len(results) >= limit:
                    break

    metadata = {}
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

    return json.dumps({
        "success": True,
        "scan_id": scan_id,
        "metadata": metadata,
        "findings": results,
        "total_returned": len(results)
    }, indent=2)


@mcp.tool()
async def list_scans(limit: int = 50) -> str:
    """
    List all previous security scans.

    Args:
        limit: Maximum number of scans to return (default: 50)

    Returns:
        JSON string with scan list
    """
    metadata_files = sorted(
        SCAN_RESULTS_DIR.glob("*_metadata.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    scans = []
    for metadata_file in metadata_files[:limit]:
        with open(metadata_file, 'r') as f:
            scans.append(json.load(f))

    return json.dumps({
        "success": True,
        "total_scans": len(scans),
        "scans": scans
    }, indent=2)


@mcp.tool()
async def detect_anomalous_findings(
    scan_id: str,
    baseline_scan_id: Optional[str] = None,
    threshold: float = 0.7
) -> str:
    """
    Use embedding-based analysis to detect anomalous security findings.

    Compares findings against a baseline (previous scans or expected patterns)
    to identify unusual or novel vulnerabilities that may need urgent attention.

    Args:
        scan_id: Current scan to analyze
        baseline_scan_id: Previous scan to compare against (optional)
        threshold: Similarity threshold - lower values = more anomalies detected

    Returns:
        JSON with anomalous findings and analysis
    """
    if not _TPU_AVAILABLE:
        return json.dumps({
            "success": False,
            "error": "Embedding features not available. Install sentence-transformers."
        })

    # Load current scan results
    result_file = SCAN_RESULTS_DIR / f"{scan_id}.jsonl"
    if not result_file.exists():
        return json.dumps({"success": False, "error": f"Scan {scan_id} not found"})

    current_findings = []
    with open(result_file, 'r') as f:
        for line in f:
            if line.strip():
                current_findings.append(json.loads(line))

    if not current_findings:
        return json.dumps({
            "success": True,
            "anomalies": [],
            "message": "No findings to analyze"
        })

    # Build baseline embeddings
    baseline_texts = []

    if baseline_scan_id:
        baseline_file = SCAN_RESULTS_DIR / f"{baseline_scan_id}.jsonl"
        if baseline_file.exists():
            with open(baseline_file, 'r') as f:
                for line in f:
                    if line.strip():
                        finding = json.loads(line)
                        text = _finding_to_text(finding)
                        baseline_texts.append(text)
    else:
        # Use common vulnerability patterns as baseline
        baseline_texts = [
            "SQL injection vulnerability allowing database access",
            "Cross-site scripting XSS in user input fields",
            "Open redirect vulnerability in URL parameters",
            "Information disclosure exposing server details",
            "Missing security headers Content-Security-Policy",
            "Outdated software version with known vulnerabilities",
            "Directory listing enabled exposing file structure",
            "CORS misconfiguration allowing unauthorized access",
            "SSL/TLS misconfiguration weak ciphers enabled",
            "Authentication bypass vulnerability"
        ]

    # Embed baseline
    baseline_embeddings = []
    if baseline_texts:
        baseline_embeddings = _text_model.encode(baseline_texts)

    # Analyze current findings
    anomalies = []
    import numpy as np

    for finding in current_findings:
        finding_text = _finding_to_text(finding)
        finding_emb = _text_model.encode(finding_text)

        # Calculate similarity to baseline
        if len(baseline_embeddings) > 0:
            similarities = []
            for base_emb in baseline_embeddings:
                sim = float(np.dot(finding_emb, base_emb) / (
                    np.linalg.norm(finding_emb) * np.linalg.norm(base_emb)
                ))
                similarities.append(sim)

            max_similarity = max(similarities)

            # Low similarity = anomalous (novel finding)
            if max_similarity < threshold:
                anomalies.append({
                    "finding": finding,
                    "anomaly_score": 1.0 - max_similarity,
                    "max_similarity_to_baseline": max_similarity,
                    "reason": "Novel finding not matching baseline patterns"
                })

    # Sort by anomaly score (most anomalous first)
    anomalies.sort(key=lambda x: x["anomaly_score"], reverse=True)

    return json.dumps({
        "success": True,
        "scan_id": scan_id,
        "baseline_scan_id": baseline_scan_id,
        "total_findings": len(current_findings),
        "anomalies_detected": len(anomalies),
        "threshold": threshold,
        "anomalies": anomalies[:20],  # Top 20 most anomalous
        "embedding_enabled": _TPU_AVAILABLE
    }, indent=2)


@mcp.tool()
async def prioritize_findings(scan_id: str) -> str:
    """
    Use embedding-based importance scoring to prioritize security findings.

    Scores each finding based on semantic similarity to critical security
    terms and patterns, helping focus remediation efforts.

    Args:
        scan_id: Scan ID to prioritize

    Returns:
        JSON with prioritized findings
    """
    if not _TPU_AVAILABLE:
        return json.dumps({
            "success": False,
            "error": "Embedding features not available"
        })

    result_file = SCAN_RESULTS_DIR / f"{scan_id}.jsonl"
    if not result_file.exists():
        return json.dumps({"success": False, "error": f"Scan {scan_id} not found"})

    findings = []
    with open(result_file, 'r') as f:
        for line in f:
            if line.strip():
                findings.append(json.loads(line))

    if not findings:
        return json.dumps({"success": True, "prioritized": [], "message": "No findings"})

    # Critical security terms for importance scoring
    critical_terms = [
        "remote code execution critical vulnerability",
        "authentication bypass unauthorized access",
        "SQL injection database compromise",
        "privilege escalation root access",
        "data breach sensitive information exposure",
        "zero-day exploit active exploitation"
    ]

    critical_embeddings = _text_model.encode(critical_terms)
    import numpy as np

    prioritized = []
    for finding in findings:
        finding_text = _finding_to_text(finding)
        finding_emb = _text_model.encode(finding_text)

        # Calculate max similarity to critical terms
        max_criticality = 0
        for crit_emb in critical_embeddings:
            sim = float(np.dot(finding_emb, crit_emb) / (
                np.linalg.norm(finding_emb) * np.linalg.norm(crit_emb)
            ))
            max_criticality = max(max_criticality, sim)

        # Combine with severity for priority score
        severity_scores = {
            "critical": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3, "info": 0.1
        }
        sev = finding.get("info", {}).get("severity", "info").lower()
        severity_weight = severity_scores.get(sev, 0.1)

        priority_score = (max_criticality * 0.6) + (severity_weight * 0.4)

        prioritized.append({
            "finding": finding,
            "priority_score": round(priority_score, 3),
            "criticality_score": round(max_criticality, 3),
            "severity": sev
        })

    # Sort by priority (highest first)
    prioritized.sort(key=lambda x: x["priority_score"], reverse=True)

    return json.dumps({
        "success": True,
        "scan_id": scan_id,
        "total_findings": len(findings),
        "prioritized": prioritized,
        "embedding_enabled": _TPU_AVAILABLE
    }, indent=2)


def _finding_to_text(finding: Dict[str, Any]) -> str:
    """Convert a security finding to text for embedding."""
    info = finding.get("info", {})
    parts = [
        info.get("name", ""),
        info.get("description", ""),
        info.get("severity", ""),
        finding.get("matcher-name", ""),
        finding.get("matched-at", "")
    ]
    return " ".join(filter(None, parts))


if __name__ == "__main__":
    mcp.run(transport="stdio")
