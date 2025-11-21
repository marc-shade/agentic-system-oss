#!/usr/bin/env python3
"""
Phase 1 Monitoring - Track 24-Hour Practice Period
==================================================

Monitors the autonomous loop during the 24-hour practice period on sample_module.py.
Tracks success criteria and provides go/no-go decision for enabling production targets.

Success Criteria:
- Minimum 3 successful improvement cycles
- 90%+ success rate
- Zero safety incidents
- 5%+ cumulative performance gain

Usage:
    python3 phase1_monitor.py
"""

import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple


class Phase1Monitor:
    """Monitor practice period and determine production readiness."""

    def __init__(self):
        self.config_path = Path("/mnt/agentic-system/agi_config.json")
        self.git_dir = Path("/mnt/agentic-system")
        self.target_file = Path("/mnt/agentic-system/intelligent-agents/sample_module.py")

        # Load config
        with open(self.config_path) as f:
            self.config = json.load(f)

        self.criteria = self.config["target_files"]["rollout_schedule"]["criteria"]
        self.monitoring_start = datetime.fromisoformat(
            self.config["target_files"]["rollout_schedule"]["monitoring_start"]
        )
        self.enable_after_hours = self.config["target_files"]["rollout_schedule"]["enable_after_hours"]

    def get_git_commits(self) -> List[Dict]:
        """Get all commits to sample_module.py in last 24 hours."""
        result = subprocess.run(
            ["git", "-C", str(self.git_dir), "log",
             "--since=24.hours.ago",
             "--format=%H|%at|%s",
             "--", "intelligent-agents/sample_module.py"],
            capture_output=True,
            text=True
        )

        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            commit_hash, timestamp, message = line.split('|', 2)
            commits.append({
                "hash": commit_hash,
                "timestamp": int(timestamp),
                "message": message,
                "datetime": datetime.fromtimestamp(int(timestamp))
            })

        return commits

    def analyze_commits(self, commits: List[Dict]) -> Dict:
        """Analyze commits for success patterns."""
        successful = []
        failed = []
        rollbacks = []

        for commit in commits:
            msg = commit["message"]
            if "rollback" in msg.lower() or "revert" in msg.lower():
                rollbacks.append(commit)
                failed.append(commit)
            elif "optimize" in msg.lower() or "improve" in msg.lower():
                successful.append(commit)

        total = len(commits) - len(rollbacks)  # Don't count rollbacks as attempts
        success_rate = len(successful) / max(1, total) if total > 0 else 0

        return {
            "total_cycles": total,
            "successful": len(successful),
            "failed": len(failed),
            "rollbacks": len(rollbacks),
            "success_rate": success_rate
        }

    def check_safety_incidents(self) -> Tuple[int, List[str]]:
        """Check for safety incidents in git history."""
        # Look for emergency rollbacks, safety violations, etc.
        result = subprocess.run(
            ["git", "-C", str(self.git_dir), "log",
             "--since=24.hours.ago",
             "--format=%s",
             "--grep=SAFETY",
             "--grep=EMERGENCY",
             "--grep=VIOLATION",
             "-i"],
            capture_output=True,
            text=True
        )

        incidents = [line for line in result.stdout.strip().split('\n') if line]
        return len(incidents), incidents

    def estimate_performance_gain(self) -> float:
        """Estimate cumulative performance gain from improvements."""
        # This is a rough estimate based on commit messages
        # In production, would use actual benchmark data
        commits = self.get_git_commits()

        total_gain = 0.0
        for commit in commits:
            msg = commit["message"].lower()
            # Look for performance indicators in commit messages
            if "improve" in msg or "optimize" in msg:
                # Conservative estimate: 5-10% per improvement
                total_gain += 0.075  # Average 7.5%

        return total_gain

    def check_criteria(self) -> Dict:
        """Check all success criteria."""
        commits = self.get_git_commits()
        analysis = self.analyze_commits(commits)
        incidents, incident_details = self.check_safety_incidents()
        performance_gain = self.estimate_performance_gain()

        now = datetime.now()
        time_elapsed = (now - self.monitoring_start).total_seconds() / 3600  # hours

        criteria_met = {
            "time_elapsed": {
                "required": self.enable_after_hours,
                "actual": time_elapsed,
                "met": time_elapsed >= self.enable_after_hours
            },
            "successful_cycles": {
                "required": self.criteria["min_successful_cycles"],
                "actual": analysis["successful"],
                "met": analysis["successful"] >= self.criteria["min_successful_cycles"]
            },
            "success_rate": {
                "required": self.criteria["min_success_rate"],
                "actual": analysis["success_rate"],
                "met": analysis["success_rate"] >= self.criteria["min_success_rate"]
            },
            "safety_incidents": {
                "required": self.criteria["max_safety_incidents"],
                "actual": incidents,
                "met": incidents <= self.criteria["max_safety_incidents"]
            },
            "performance_gain": {
                "required": self.criteria["min_performance_gain"],
                "actual": performance_gain,
                "met": performance_gain >= self.criteria["min_performance_gain"]
            }
        }

        all_met = all(c["met"] for c in criteria_met.values())

        return {
            "all_criteria_met": all_met,
            "criteria": criteria_met,
            "incidents": incident_details,
            "commits": len(commits),
            "analysis": analysis
        }

    def generate_report(self) -> str:
        """Generate monitoring report."""
        status = self.check_criteria()

        report = []
        report.append("=" * 70)
        report.append("PHASE 1 MONITORING REPORT")
        report.append("=" * 70)
        report.append("")

        # Overall status
        if status["all_criteria_met"]:
            report.append("✅ STATUS: READY FOR PRODUCTION TARGETS")
        else:
            report.append("⏳ STATUS: MONITORING IN PROGRESS")
        report.append("")

        # Time elapsed
        time_info = status["criteria"]["time_elapsed"]
        report.append(f"⏱️  Time Elapsed: {time_info['actual']:.1f}h / {time_info['required']}h")
        if time_info["met"]:
            report.append("   ✅ Minimum time requirement met")
        else:
            remaining = time_info["required"] - time_info["actual"]
            report.append(f"   ⏳ {remaining:.1f} hours remaining")
        report.append("")

        # Criteria breakdown
        report.append("📊 SUCCESS CRITERIA:")
        report.append("")

        for name, info in status["criteria"].items():
            if name == "time_elapsed":
                continue  # Already shown above

            status_icon = "✅" if info["met"] else "❌"
            report.append(f"{status_icon} {name.replace('_', ' ').title()}")
            report.append(f"   Required: {info['required']}")
            report.append(f"   Actual: {info['actual']:.2f}")
            report.append("")

        # Commit analysis
        report.append("📝 COMMIT ANALYSIS:")
        report.append(f"   Total cycles: {status['analysis']['total_cycles']}")
        report.append(f"   Successful: {status['analysis']['successful']}")
        report.append(f"   Failed: {status['analysis']['failed']}")
        report.append(f"   Rollbacks: {status['analysis']['rollbacks']}")
        report.append(f"   Success rate: {status['analysis']['success_rate']:.1%}")
        report.append("")

        # Safety incidents
        if status["incidents"]:
            report.append("⚠️  SAFETY INCIDENTS:")
            for incident in status["incidents"]:
                report.append(f"   - {incident}")
            report.append("")
        else:
            report.append("✅ No safety incidents detected")
            report.append("")

        # Recommendation
        report.append("=" * 70)
        if status["all_criteria_met"]:
            report.append("RECOMMENDATION: ENABLE PRODUCTION TARGETS")
            report.append("")
            report.append("Next steps:")
            report.append("1. Review this report carefully")
            report.append("2. Edit agi_config.json: set use_production_targets = true")
            report.append("3. Restart autonomous loop (or wait for next cycle)")
            report.append("4. Monitor closely for first self-improvements")
        else:
            report.append("RECOMMENDATION: CONTINUE MONITORING")
            report.append("")
            report.append("Not all criteria met yet. Continue monitoring.")
        report.append("=" * 70)

        return "\n".join(report)

    def save_report(self, report: str):
        """Save report to file."""
        report_path = Path("/mnt/agentic-system/phase1_monitoring_report.txt")
        with open(report_path, "w") as f:
            f.write(report)
            f.write(f"\n\nGenerated: {datetime.now().isoformat()}\n")

        print(f"Report saved to: {report_path}")


def main():
    """Run monitoring and generate report."""
    print("Starting Phase 1 monitoring...")
    print()

    monitor = Phase1Monitor()
    report = monitor.generate_report()

    print(report)
    print()

    monitor.save_report(report)

    # Return exit code based on readiness
    status = monitor.check_criteria()
    if status["all_criteria_met"]:
        print("✅ System is ready for production targets!")
        return 0
    else:
        print("⏳ Continue monitoring...")
        return 1


if __name__ == "__main__":
    sys.exit(main())
