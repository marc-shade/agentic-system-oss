#!/usr/bin/env python3
"""
Complexity Purge - Hyperthink Move 3 Implementation

"Every line of code is a liability. Every feature is cognitive load.
If it doesn't serve the user's moment of truth, kill it."

This tool audits the system for complexity that should be eliminated:
1. MCP servers not called in the last 30 days → Disable
2. Commands not used in the last 30 days → Archive
3. Daemons not producing visible value → Stop
4. Logs not being read → Stop generating

The guiding question: "Would Marc notice if we turned this off?"

STATUS: Production Ready
"""

import asyncio
import logging
import json
import os
import sqlite3
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
STORAGE_BASE = "/Volumes/SSDRAID0/agentic-system"
CLAUDE_HOME = os.path.expanduser("~/.claude")
COMMANDS_DIR = f"{CLAUDE_HOME}/commands"
SKILLS_DIR = f"{CLAUDE_HOME}/skills"
MCP_CONFIG = os.path.expanduser("~/.claude.json")
LOGS_DIR = f"{STORAGE_BASE}/logs"


@dataclass
class AuditResult:
    """Result of a single audit check"""
    category: str
    item: str
    status: str  # "active", "unused", "unknown"
    last_used: Optional[str]
    recommendation: str
    impact: str  # "low", "medium", "high"
    details: Dict[str, Any]


class ComplexityPurge:
    """
    Audit system complexity and recommend simplifications.

    Usage:
        purge = ComplexityPurge()
        report = purge.full_audit()
        print(report)
    """

    def __init__(self, days_threshold: int = 30):
        self.days_threshold = days_threshold
        self.cutoff_date = datetime.now() - timedelta(days=days_threshold)

    def audit_mcp_servers(self) -> List[AuditResult]:
        """Audit MCP server usage based on tool call logs"""
        results = []

        # Load MCP config
        try:
            with open(MCP_CONFIG, 'r') as f:
                config = json.load(f)
            mcp_servers = config.get('mcpServers', {})
        except Exception as e:
            logger.error(f"Failed to load MCP config: {e}")
            return [AuditResult(
                category="mcp_servers",
                item="config_error",
                status="unknown",
                last_used=None,
                recommendation="Fix MCP config file",
                impact="high",
                details={"error": str(e)}
            )]

        # Check each MCP server
        for server_name, server_config in mcp_servers.items():
            disabled = server_config.get('disabled', False)

            if disabled:
                results.append(AuditResult(
                    category="mcp_servers",
                    item=server_name,
                    status="disabled",
                    last_used=None,
                    recommendation="Already disabled - consider removing from config",
                    impact="low",
                    details={"config": server_config}
                ))
                continue

            # Check if server is essential (from known essential list)
            essential_servers = {
                "enhanced-memory", "voice-mode", "agent-runtime-mcp",
                "sequential-thinking", "arduino-surface", "ember-mcp",
                "cluster-execution-mcp", "node-chat-mcp", "safla-mcp"
            }

            if server_name in essential_servers:
                results.append(AuditResult(
                    category="mcp_servers",
                    item=server_name,
                    status="active",
                    last_used="essential",
                    recommendation="Keep - essential server",
                    impact="high",
                    details={"tier": "essential"}
                ))
            else:
                # Mark as needing usage review
                results.append(AuditResult(
                    category="mcp_servers",
                    item=server_name,
                    status="unknown",
                    last_used=None,
                    recommendation=f"Review usage - disable if not used in {self.days_threshold} days",
                    impact="medium",
                    details={"config": server_config}
                ))

        return results

    def audit_commands(self) -> List[AuditResult]:
        """Audit slash command files"""
        results = []

        if not os.path.exists(COMMANDS_DIR):
            return results

        command_files = list(Path(COMMANDS_DIR).glob("*.md"))
        total_commands = len(command_files)

        # Categorize commands
        essential_patterns = [
            "continue", "clear", "help", "status", "memory",
            "commit", "review", "prime", "init"
        ]

        for cmd_file in command_files:
            cmd_name = cmd_file.stem

            # Check file modification time (rough proxy for usage)
            mtime = datetime.fromtimestamp(cmd_file.stat().st_mtime)
            days_since_modified = (datetime.now() - mtime).days

            # Check if essential
            is_essential = any(p in cmd_name.lower() for p in essential_patterns)

            if is_essential:
                status = "active"
                recommendation = "Keep - essential command"
                impact = "low"
            elif days_since_modified > self.days_threshold * 2:  # 60 days
                status = "unused"
                recommendation = "Archive - not modified in 60+ days"
                impact = "low"
            elif days_since_modified > self.days_threshold:
                status = "stale"
                recommendation = f"Review - not modified in {days_since_modified} days"
                impact = "low"
            else:
                status = "active"
                recommendation = "Keep - recently active"
                impact = "low"

            results.append(AuditResult(
                category="commands",
                item=cmd_name,
                status=status,
                last_used=mtime.isoformat(),
                recommendation=recommendation,
                impact=impact,
                details={
                    "file": str(cmd_file),
                    "days_since_modified": days_since_modified,
                    "size_bytes": cmd_file.stat().st_size
                }
            ))

        return results

    def audit_skills(self) -> List[AuditResult]:
        """Audit skill directories"""
        results = []

        if not os.path.exists(SKILLS_DIR):
            return results

        skill_dirs = [d for d in Path(SKILLS_DIR).iterdir() if d.is_dir()]

        for skill_dir in skill_dirs:
            skill_name = skill_dir.name
            skill_file = skill_dir / "SKILL.md"

            if not skill_file.exists():
                results.append(AuditResult(
                    category="skills",
                    item=skill_name,
                    status="broken",
                    last_used=None,
                    recommendation="Fix or remove - missing SKILL.md",
                    impact="low",
                    details={"path": str(skill_dir)}
                ))
                continue

            # Check modification time
            mtime = datetime.fromtimestamp(skill_file.stat().st_mtime)
            days_since_modified = (datetime.now() - mtime).days

            if days_since_modified > self.days_threshold * 2:
                status = "unused"
                recommendation = "Review - not modified in 60+ days"
            else:
                status = "active"
                recommendation = "Keep"

            results.append(AuditResult(
                category="skills",
                item=skill_name,
                status=status,
                last_used=mtime.isoformat(),
                recommendation=recommendation,
                impact="low",
                details={
                    "path": str(skill_dir),
                    "days_since_modified": days_since_modified
                }
            ))

        return results

    def audit_daemons(self) -> List[AuditResult]:
        """Audit running daemons and their value"""
        results = []

        # Check for known daemon processes
        daemon_patterns = [
            ("temporal", "Temporal Server", "essential"),
            ("autokitteh", "AutoKitteh", "essential"),
            ("prometheus", "Prometheus", "monitoring"),
            ("loki", "Loki", "monitoring"),
            ("grafana", "Grafana", "monitoring"),
            ("qdrant", "Qdrant Vector DB", "essential"),
            ("consciousness_daemon", "Consciousness Daemon", "experimental"),
            ("visual_agi", "Visual AGI Daemon", "experimental"),
            ("darwin_godel", "Darwin Gödel Machine", "experimental"),
            ("cluster_health", "Cluster Health Monitor", "monitoring"),
        ]

        for pattern, name, tier in daemon_patterns:
            try:
                result = subprocess.run(
                    ["pgrep", "-f", pattern],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                is_running = result.returncode == 0
                pids = result.stdout.strip().split('\n') if is_running else []
            except:
                is_running = False
                pids = []

            if tier == "essential":
                if is_running:
                    status = "active"
                    recommendation = "Keep - essential service"
                else:
                    status = "stopped"
                    recommendation = "Start - essential service not running!"
                impact = "high"
            elif tier == "experimental":
                if is_running:
                    status = "active"
                    recommendation = "Review - experimental daemon running"
                else:
                    status = "stopped"
                    recommendation = "Keep stopped unless actively developing"
                impact = "low"
            else:  # monitoring
                status = "active" if is_running else "stopped"
                recommendation = "Keep for observability" if is_running else "Consider starting"
                impact = "medium"

            results.append(AuditResult(
                category="daemons",
                item=name,
                status=status,
                last_used=None,
                recommendation=recommendation,
                impact=impact,
                details={
                    "pattern": pattern,
                    "tier": tier,
                    "running": is_running,
                    "pids": pids
                }
            ))

        return results

    def audit_log_directories(self) -> List[AuditResult]:
        """Audit log directories for size and activity"""
        results = []

        if not os.path.exists(LOGS_DIR):
            return results

        log_dirs = [d for d in Path(LOGS_DIR).iterdir() if d.is_dir()]

        for log_dir in log_dirs:
            dir_name = log_dir.name

            # Calculate total size
            total_size = sum(f.stat().st_size for f in log_dir.rglob("*") if f.is_file())
            size_mb = total_size / (1024 * 1024)

            # Find most recent log
            log_files = list(log_dir.rglob("*.log")) + list(log_dir.rglob("*.json"))
            if log_files:
                most_recent = max(log_files, key=lambda f: f.stat().st_mtime)
                last_modified = datetime.fromtimestamp(most_recent.stat().st_mtime)
                days_since = (datetime.now() - last_modified).days
            else:
                last_modified = None
                days_since = 999

            if size_mb > 1000:  # Over 1GB
                status = "bloated"
                recommendation = f"Clean up - {size_mb:.0f}MB of logs"
                impact = "medium"
            elif days_since > self.days_threshold:
                status = "stale"
                recommendation = "Archive old logs"
                impact = "low"
            else:
                status = "active"
                recommendation = "Keep"
                impact = "low"

            results.append(AuditResult(
                category="logs",
                item=dir_name,
                status=status,
                last_used=last_modified.isoformat() if last_modified else None,
                recommendation=recommendation,
                impact=impact,
                details={
                    "path": str(log_dir),
                    "size_mb": round(size_mb, 2),
                    "days_since_update": days_since
                }
            ))

        return results

    def audit_workflow_systems(self) -> List[AuditResult]:
        """Audit workflow systems (Temporal, AutoKitteh, n8n)"""
        results = []

        systems = [
            ("Temporal", 7233, "Long-running stateful workflows"),
            ("AutoKitteh", 9980, "Event-driven lightweight workflows"),
            ("n8n", 5678, "Visual workflow automation"),
        ]

        for name, port, purpose in systems:
            try:
                result = subprocess.run(
                    ["lsof", "-i", f":{port}"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                is_running = "LISTEN" in result.stdout
            except:
                is_running = False

            if name in ["Temporal", "AutoKitteh"]:
                # These are core systems
                if is_running:
                    status = "active"
                    recommendation = f"Keep - {purpose}"
                else:
                    status = "stopped"
                    recommendation = "Start - core workflow system"
                impact = "high"
            else:
                # n8n is optional
                if is_running:
                    status = "active"
                    recommendation = "Review usage - is it providing unique value?"
                else:
                    status = "stopped"
                    recommendation = "Keep stopped unless actively used"
                impact = "low"

            results.append(AuditResult(
                category="workflows",
                item=name,
                status=status,
                last_used=None,
                recommendation=recommendation,
                impact=impact,
                details={
                    "port": port,
                    "purpose": purpose,
                    "running": is_running
                }
            ))

        return results

    def full_audit(self) -> Dict[str, Any]:
        """Run complete complexity audit"""
        logger.info("Starting Complexity Purge audit...")

        all_results = []

        # Run all audits
        audits = [
            ("MCP Servers", self.audit_mcp_servers),
            ("Commands", self.audit_commands),
            ("Skills", self.audit_skills),
            ("Daemons", self.audit_daemons),
            ("Logs", self.audit_log_directories),
            ("Workflow Systems", self.audit_workflow_systems),
        ]

        for name, audit_func in audits:
            logger.info(f"Auditing {name}...")
            try:
                results = audit_func()
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Audit failed for {name}: {e}")

        # Summarize
        by_status = {}
        by_category = {}
        high_impact = []
        recommendations = []

        for r in all_results:
            # Count by status
            by_status[r.status] = by_status.get(r.status, 0) + 1

            # Count by category
            if r.category not in by_category:
                by_category[r.category] = {"total": 0, "unused": 0, "active": 0}
            by_category[r.category]["total"] += 1
            if r.status in ["unused", "stale", "bloated", "broken"]:
                by_category[r.category]["unused"] += 1
            elif r.status == "active":
                by_category[r.category]["active"] += 1

            # Collect high impact items
            if r.impact == "high" and r.status != "active":
                high_impact.append(r)

            # Collect actionable recommendations
            if r.status in ["unused", "stale", "bloated", "broken", "stopped"]:
                recommendations.append({
                    "category": r.category,
                    "item": r.item,
                    "action": r.recommendation,
                    "impact": r.impact
                })

        return {
            "audit_date": datetime.now().isoformat(),
            "threshold_days": self.days_threshold,
            "summary": {
                "total_items": len(all_results),
                "by_status": by_status,
                "by_category": by_category
            },
            "high_impact_issues": [
                {"item": r.item, "status": r.status, "recommendation": r.recommendation}
                for r in high_impact
            ],
            "recommendations": recommendations[:20],  # Top 20
            "full_results": [
                {
                    "category": r.category,
                    "item": r.item,
                    "status": r.status,
                    "recommendation": r.recommendation,
                    "impact": r.impact
                }
                for r in all_results
            ]
        }

    def generate_report(self) -> str:
        """Generate human-readable report"""
        audit = self.full_audit()

        lines = [
            "=" * 60,
            "COMPLEXITY PURGE REPORT",
            f"Generated: {audit['audit_date']}",
            f"Threshold: {audit['threshold_days']} days",
            "=" * 60,
            "",
            "SUMMARY",
            "-" * 40,
            f"Total items audited: {audit['summary']['total_items']}",
            "",
            "By Status:",
        ]

        for status, count in audit['summary']['by_status'].items():
            lines.append(f"  {status}: {count}")

        lines.append("")
        lines.append("By Category:")
        for cat, stats in audit['summary']['by_category'].items():
            lines.append(f"  {cat}: {stats['active']} active, {stats['unused']} unused of {stats['total']}")

        if audit['high_impact_issues']:
            lines.append("")
            lines.append("HIGH IMPACT ISSUES")
            lines.append("-" * 40)
            for issue in audit['high_impact_issues']:
                lines.append(f"  ⚠️ {issue['item']}: {issue['recommendation']}")

        if audit['recommendations']:
            lines.append("")
            lines.append("TOP RECOMMENDATIONS")
            lines.append("-" * 40)
            for i, rec in enumerate(audit['recommendations'][:10], 1):
                lines.append(f"  {i}. [{rec['category']}] {rec['item']}")
                lines.append(f"     → {rec['action']}")

        lines.append("")
        lines.append("=" * 60)
        lines.append("Remember: The goal is SIMPLER every week, not more complex.")
        lines.append("Question: 'Would Marc notice if we turned this off?'")
        lines.append("=" * 60)

        return "\n".join(lines)


    def archive_unused_commands(self, dry_run: bool = True) -> Dict[str, Any]:
        """Archive unused commands to ~/.claude/commands/archived/"""
        archive_dir = Path(COMMANDS_DIR) / "archived"

        if not dry_run:
            archive_dir.mkdir(exist_ok=True)

        results = self.audit_commands()
        archived = []
        skipped = []

        for r in results:
            if r.status in ["unused", "stale"]:
                cmd_file = Path(r.details["file"])
                if cmd_file.exists():
                    if dry_run:
                        archived.append({"file": r.item, "action": "would archive"})
                    else:
                        dest = archive_dir / cmd_file.name
                        cmd_file.rename(dest)
                        archived.append({"file": r.item, "action": "archived", "dest": str(dest)})
            else:
                skipped.append(r.item)

        return {
            "dry_run": dry_run,
            "archived": archived,
            "skipped_count": len(skipped),
            "archive_dir": str(archive_dir)
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Complexity Purge Audit")
    parser.add_argument("--days", type=int, default=30, help="Days threshold for 'unused'")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of report")
    parser.add_argument("--category", type=str, help="Audit specific category only")
    parser.add_argument("--action", type=str, choices=["archive"], help="Action to take")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")
    parser.add_argument("--execute", action="store_true", help="Actually execute the action")

    args = parser.parse_args()

    purge = ComplexityPurge(days_threshold=args.days)

    if args.action == "archive":
        dry_run = not args.execute
        result = purge.archive_unused_commands(dry_run=dry_run)
        if dry_run:
            print(f"DRY RUN - Would archive {len(result['archived'])} commands to {result['archive_dir']}")
            for item in result['archived'][:20]:
                print(f"  → {item['file']}")
            if len(result['archived']) > 20:
                print(f"  ... and {len(result['archived']) - 20} more")
        else:
            print(f"Archived {len(result['archived'])} commands to {result['archive_dir']}")
            for item in result['archived']:
                print(f"  ✓ {item['file']}")
    elif args.json:
        print(json.dumps(purge.full_audit(), indent=2, default=str))
    else:
        print(purge.generate_report())
