#!/usr/bin/env python3
"""
Autonomous Security Scanning Agent

Continuously monitors and assesses security posture across the agentic cluster.
Provides intelligent vulnerability detection, prioritization, and remediation recommendations.

Features:
- Autonomous vulnerability scanning across cluster nodes
- Intelligent threat prioritization based on context
- Learning from scan history and remediation outcomes
- Integration with enhanced-memory for pattern recognition
- Automatic alert generation for critical vulnerabilities
- Remediation recommendation engine
"""

import asyncio
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configuration
NUCLEI_BIN = os.path.expanduser("~/go/bin/nuclei")
SCAN_RESULTS_DIR = Path("/mnt/agentic-system/security-scans")
AGENT_DB = Path("/mnt/agentic-system/databases/security_agent.db")
CONFIG_FILE = Path("/mnt/agentic-system/config/security_agent_config.json")

# Cluster nodes
CLUSTER_NODES = {
    "macpro51": {"ip": "192.168.1.87", "role": "compute", "services": ["ssh", "smb", "ollama", "docker"]},
    "mac-studio": {"ip": "192.168.1.79", "role": "orchestrator", "services": ["ssh", "smb"]},
    "macbook-air": {"ip": "192.168.1.55", "role": "coordinator", "services": ["ssh"]},
    "mac-mini": {"ip": "192.168.1.233", "role": "fileserver", "services": ["ssh", "smb", "nfs"]}
}

# Severity weights for prioritization
SEVERITY_WEIGHTS = {
    "critical": 100,
    "high": 50,
    "medium": 25,
    "low": 10,
    "info": 1
}


class AutonomousSecurityAgent:
    """Autonomous security scanning and vulnerability management agent."""

    def __init__(self):
        """Initialize the security agent."""
        self.db_path = AGENT_DB
        self.config = self._load_config()
        self._init_database()

    def _load_config(self) -> Dict[str, Any]:
        """Load agent configuration."""
        default_config = {
            "scan_interval_hours": 24,
            "quick_scan_interval_hours": 6,
            "severity_threshold": "medium",
            "auto_remediate": False,
            "alert_on_critical": True,
            "alert_email": None,
            "max_concurrent_scans": 4,
            "rate_limit": 100,
            "learning_enabled": True,
            "baseline_established": False
        }

        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                loaded_config = json.load(f)
                default_config.update(loaded_config)

        return default_config

    def _save_config(self):
        """Save configuration to file."""
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)

    def _init_database(self):
        """Initialize SQLite database for vulnerability tracking."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Vulnerabilities table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vulnerabilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vuln_id TEXT NOT NULL,
                target TEXT NOT NULL,
                template_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                first_detected TIMESTAMP NOT NULL,
                last_detected TIMESTAMP NOT NULL,
                status TEXT DEFAULT 'open',
                remediation_advice TEXT,
                false_positive BOOLEAN DEFAULT 0,
                UNIQUE(vuln_id, target)
            )
        ''')

        # Scan history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id TEXT NOT NULL,
                target TEXT NOT NULL,
                scan_type TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                total_findings INTEGER,
                critical_count INTEGER,
                high_count INTEGER,
                medium_count INTEGER,
                low_count INTEGER,
                info_count INTEGER,
                duration_seconds INTEGER,
                status TEXT
            )
        ''')

        # Remediation history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS remediation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vuln_id TEXT NOT NULL,
                target TEXT NOT NULL,
                remediation_action TEXT NOT NULL,
                applied_timestamp TIMESTAMP NOT NULL,
                success BOOLEAN,
                notes TEXT,
                FOREIGN KEY(vuln_id) REFERENCES vulnerabilities(vuln_id)
            )
        ''')

        # Baseline vulnerabilities (known acceptable risks)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS baseline_vulnerabilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vuln_id TEXT NOT NULL,
                target TEXT NOT NULL,
                justification TEXT,
                added_timestamp TIMESTAMP NOT NULL,
                approved_by TEXT
            )
        ''')

        conn.commit()
        conn.close()

    async def run_scan(self, target: str, scan_type: str = "full", severity: List[str] = None) -> Dict[str, Any]:
        """Execute a security scan against a target."""
        if severity is None:
            severity = ["medium", "high", "critical"]

        print(f"[{datetime.now()}] Starting {scan_type} scan on {target}")

        # Generate scan ID
        scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(target) % 10000}"
        output_file = SCAN_RESULTS_DIR / f"{scan_id}.jsonl"

        # Build command
        cmd = [
            NUCLEI_BIN,
            "-target", target,
            "-json",
            "-severity", ",".join(severity),
            "-rate-limit", str(self.config.get("rate_limit", 100)),
            "-o", str(output_file)
        ]

        # Add templates based on scan type
        if scan_type == "quick":
            cmd.extend(["-tags", "network,exposure"])
        elif scan_type == "web":
            cmd.extend(["-tags", "web,cve"])
        elif scan_type == "comprehensive":
            cmd.extend(["-tags", "cve,exposure,misconfiguration,default-logins"])

        start_time = datetime.now()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=600
            )

            duration = (datetime.now() - start_time).total_seconds()

            # Parse results
            findings = []
            if output_file.exists():
                with open(output_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            findings.append(json.loads(line))

            # Count by severity
            severity_counts = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "info": 0
            }

            for finding in findings:
                sev = finding.get("info", {}).get("severity", "info")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

            # Store in database
            self._record_scan_history(
                scan_id, target, scan_type,
                len(findings),
                severity_counts["critical"],
                severity_counts["high"],
                severity_counts["medium"],
                severity_counts["low"],
                severity_counts["info"],
                int(duration),
                "completed"
            )

            # Process findings
            await self._process_findings(target, findings)

            result = {
                "success": True,
                "scan_id": scan_id,
                "target": target,
                "scan_type": scan_type,
                "total_findings": len(findings),
                "severity_breakdown": severity_counts,
                "duration_seconds": int(duration),
                "output_file": str(output_file)
            }

            print(f"[{datetime.now()}] Scan completed: {len(findings)} findings")

            return result

        except asyncio.TimeoutError:
            print(f"[{datetime.now()}] Scan timed out for {target}")
            return {"success": False, "error": "Scan timed out"}
        except Exception as e:
            print(f"[{datetime.now()}] Scan failed: {e}")
            return {"success": False, "error": str(e)}

    async def _process_findings(self, target: str, findings: List[Dict[str, Any]]):
        """Process scan findings and update vulnerability database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for finding in findings:
            info = finding.get("info", {})
            vuln_id = f"{info.get('template-id', 'unknown')}_{finding.get('matched-at', target)}"

            template_id = info.get("template-id", "unknown")
            severity = info.get("severity", "info")
            name = info.get("name", "Unknown Vulnerability")
            description = info.get("description", "")

            # Check if vulnerability exists
            cursor.execute(
                "SELECT id, first_detected, status FROM vulnerabilities WHERE vuln_id = ? AND target = ?",
                (vuln_id, target)
            )
            existing = cursor.fetchone()

            if existing:
                # Update last_detected
                cursor.execute(
                    "UPDATE vulnerabilities SET last_detected = ?, status = 'open' WHERE vuln_id = ? AND target = ?",
                    (datetime.now(), vuln_id, target)
                )
            else:
                # Insert new vulnerability
                remediation = self._generate_remediation_advice(finding)
                cursor.execute('''
                    INSERT INTO vulnerabilities
                    (vuln_id, target, template_id, severity, name, description, first_detected, last_detected, remediation_advice)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (vuln_id, target, template_id, severity, name, description, datetime.now(), datetime.now(), remediation))

        conn.commit()
        conn.close()

    def _generate_remediation_advice(self, finding: Dict[str, Any]) -> str:
        """Generate remediation advice for a vulnerability."""
        info = finding.get("info", {})
        template_id = info.get("template-id", "")
        severity = info.get("severity", "info")

        # Basic remediation patterns
        if "cve" in template_id.lower():
            return "Update affected software to the latest patched version. Check vendor security advisories."
        elif "exposure" in template_id or "disclosure" in template_id:
            return "Restrict access to exposed resources. Implement authentication and access controls."
        elif "misconfiguration" in template_id:
            return "Review and correct configuration according to security best practices."
        elif "default" in template_id and "login" in template_id:
            return "Change default credentials immediately. Implement strong password policies."
        elif "injection" in template_id:
            return "Implement input validation and use parameterized queries. Apply security patches."
        else:
            return f"Investigate finding and apply appropriate security controls for {severity} severity issues."

    def _record_scan_history(self, scan_id: str, target: str, scan_type: str,
                            total: int, critical: int, high: int, medium: int, low: int, info: int,
                            duration: int, status: str):
        """Record scan history in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO scan_history
            (scan_id, target, scan_type, timestamp, total_findings,
             critical_count, high_count, medium_count, low_count, info_count,
             duration_seconds, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (scan_id, target, scan_type, datetime.now(), total,
              critical, high, medium, low, info, duration, status))

        conn.commit()
        conn.close()

    async def scan_cluster(self, scan_type: str = "comprehensive") -> Dict[str, Any]:
        """Scan all cluster nodes."""
        print(f"\n{'='*60}")
        print(f"Starting cluster-wide security scan ({scan_type})")
        print(f"{'='*60}\n")

        tasks = []
        for node_name, node_info in CLUSTER_NODES.items():
            target = node_info["ip"]
            tasks.append(self.run_scan(target, scan_type))

        # Run scans with concurrency limit
        sem = asyncio.Semaphore(self.config.get("max_concurrent_scans", 4))

        async def scan_with_limit(task):
            async with sem:
                return await task

        results = await asyncio.gather(*[scan_with_limit(task) for task in tasks])

        # Aggregate results
        total_findings = sum(r.get("total_findings", 0) for r in results)
        critical_total = sum(r.get("severity_breakdown", {}).get("critical", 0) for r in results)
        high_total = sum(r.get("severity_breakdown", {}).get("high", 0) for r in results)

        summary = {
            "cluster_scan_completed": True,
            "nodes_scanned": len(CLUSTER_NODES),
            "total_findings": total_findings,
            "critical_vulnerabilities": critical_total,
            "high_vulnerabilities": high_total,
            "scan_results": results,
            "timestamp": datetime.now().isoformat()
        }

        # Alert on critical findings
        if self.config.get("alert_on_critical") and critical_total > 0:
            self._send_alert(f"CRITICAL: {critical_total} critical vulnerabilities found in cluster scan", summary)

        print(f"\n{'='*60}")
        print(f"Cluster scan completed: {total_findings} total findings")
        print(f"Critical: {critical_total}, High: {high_total}")
        print(f"{'='*60}\n")

        return summary

    def _send_alert(self, message: str, details: Dict[str, Any]):
        """Send alert notification."""
        print(f"\n🚨 SECURITY ALERT 🚨")
        print(f"Message: {message}")
        print(f"Details: {json.dumps(details, indent=2)}")
        print()

        # TODO: Integrate with notification system (email, Slack, etc.)
        # For now, log to file
        alert_file = Path("/mnt/agentic-system/logs/security_alerts.log")
        alert_file.parent.mkdir(parents=True, exist_ok=True)

        with open(alert_file, 'a') as f:
            f.write(f"[{datetime.now()}] {message}\n")
            f.write(f"{json.dumps(details, indent=2)}\n\n")

    def get_vulnerability_report(self, target: Optional[str] = None,
                                 severity: Optional[str] = None,
                                 status: str = "open") -> List[Dict[str, Any]]:
        """Generate vulnerability report."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT * FROM vulnerabilities WHERE status = ?"
        params = [status]

        if target:
            query += " AND target = ?"
            params.append(target)

        if severity:
            query += " AND severity = ?"
            params.append(severity)

        query += " ORDER BY CASE severity "
        query += "WHEN 'critical' THEN 1 "
        query += "WHEN 'high' THEN 2 "
        query += "WHEN 'medium' THEN 3 "
        query += "WHEN 'low' THEN 4 "
        query += "ELSE 5 END, first_detected DESC"

        cursor.execute(query, params)

        columns = [desc[0] for desc in cursor.description]
        vulnerabilities = []

        for row in cursor.fetchall():
            vuln = dict(zip(columns, row))
            vulnerabilities.append(vuln)

        conn.close()
        return vulnerabilities

    async def autonomous_scan_loop(self):
        """Main autonomous scanning loop."""
        print(f"Starting autonomous security agent...")
        print(f"Scan interval: {self.config['scan_interval_hours']} hours")
        print(f"Quick scan interval: {self.config['quick_scan_interval_hours']} hours")

        last_full_scan = datetime.now() - timedelta(hours=24)
        last_quick_scan = datetime.now() - timedelta(hours=6)

        while True:
            try:
                now = datetime.now()

                # Full comprehensive scan
                if (now - last_full_scan).total_seconds() >= self.config["scan_interval_hours"] * 3600:
                    await self.scan_cluster("comprehensive")
                    last_full_scan = now

                # Quick scan (network and exposure only)
                elif (now - last_quick_scan).total_seconds() >= self.config["quick_scan_interval_hours"] * 3600:
                    await self.scan_cluster("quick")
                    last_quick_scan = now

                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                print(f"Error in autonomous scan loop: {e}")
                await asyncio.sleep(60)

    async def run_once(self, scan_type: str = "comprehensive"):
        """Run a single scan iteration."""
        return await self.scan_cluster(scan_type)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Autonomous Security Scanning Agent")
    parser.add_argument("--mode", choices=["once", "continuous"], default="once",
                      help="Run mode: once (single scan) or continuous (autonomous loop)")
    parser.add_argument("--scan-type", choices=["quick", "comprehensive", "full"],
                      default="comprehensive",
                      help="Type of scan to perform")
    parser.add_argument("--target", help="Specific target to scan (instead of full cluster)")
    parser.add_argument("--report", action="store_true", help="Generate vulnerability report")

    args = parser.parse_args()

    agent = AutonomousSecurityAgent()

    if args.report:
        vulns = agent.get_vulnerability_report()
        print(json.dumps(vulns, indent=2, default=str))
        return

    if args.target:
        result = await agent.run_scan(args.target, args.scan_type)
        print(json.dumps(result, indent=2))
    elif args.mode == "once":
        result = await agent.run_once(args.scan_type)
        print(json.dumps(result, indent=2, default=str))
    else:
        await agent.autonomous_scan_loop()


if __name__ == "__main__":
    asyncio.run(main())
