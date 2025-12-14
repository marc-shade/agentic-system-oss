#!/usr/bin/env python3
"""
Phase 1 Success Tracking System
================================

Tracks progress toward Phase 1 milestones and ASI score of 21/50.
Stores historical data, generates trend reports, and provides progress visualization.

Usage:
    python3 phase1_tracker.py --record    # Record current progress
    python3 phase1_tracker.py --report    # Generate progress report
    python3 phase1_tracker.py --export    # Export data for analysis
    python3 phase1_tracker.py --asi       # Update ASI score estimate
"""
import os
import platform

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()



class Phase1Tracker:
    """Track Phase 1 progress and milestones."""

    def __init__(self):
        self.root_dir = Path(str(_STORAGE_BASE))
        self.db_path = self.root_dir / "databases" / "phase1_tracking.db"
        self.config_path = self.root_dir / "agi_config.json"

        # Ensure database directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

        # Load config
        with open(self.config_path) as f:
            self.config = json.load(f)

    def _init_database(self):
        """Initialize tracking database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Progress snapshots table
        c.execute("""
            CREATE TABLE IF NOT EXISTS progress_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                phase TEXT NOT NULL,
                target_file TEXT,
                total_commits INTEGER,
                successful_improvements INTEGER,
                failed_improvements INTEGER,
                rollback_count INTEGER,
                success_rate REAL,
                performance_gain REAL,
                safety_incidents INTEGER,
                asi_score REAL,
                notes TEXT
            )
        """)

        # Milestones table
        c.execute("""
            CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                milestone_name TEXT NOT NULL,
                target_files TEXT,
                achieved BOOLEAN,
                asi_gain REAL,
                description TEXT
            )
        """)

        # Target status table
        c.execute("""
            CREATE TABLE IF NOT EXISTS target_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                target_file TEXT NOT NULL,
                status TEXT NOT NULL,
                improvements INTEGER,
                success_rate REAL,
                days_stable INTEGER,
                ready_for_next BOOLEAN
            )
        """)

        # ASI score history
        c.execute("""
            CREATE TABLE IF NOT EXISTS asi_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                total_score REAL NOT NULL,
                cognitive REAL,
                autonomy REAL,
                creativity REAL,
                social REAL,
                self_awareness REAL,
                ethical REAL,
                notes TEXT
            )
        """)

        conn.commit()
        conn.close()

    def record_progress(self, phase: str = "1A", target_file: Optional[str] = None,
                       notes: str = "") -> int:
        """Record current progress snapshot."""
        # Get git metrics
        commits = self._get_git_commits(target_file)
        analysis = self._analyze_commits(commits)
        incidents = self._count_safety_incidents()
        performance_gain = self._estimate_performance_gain(commits)

        # Calculate success rate
        total = analysis["total_cycles"]
        successful = analysis["successful"]
        success_rate = successful / max(1, total) if total > 0 else 0.0

        # Get current ASI estimate
        asi_score = self._get_latest_asi_score()

        # Store snapshot
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            INSERT INTO progress_snapshots
            (timestamp, phase, target_file, total_commits, successful_improvements,
             failed_improvements, rollback_count, success_rate, performance_gain,
             safety_incidents, asi_score, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            phase,
            target_file or "sample_module.py",
            len(commits),
            successful,
            analysis["failed"],
            analysis["rollbacks"],
            success_rate,
            performance_gain,
            incidents,
            asi_score,
            notes
        ))

        snapshot_id = c.lastrowid
        conn.commit()
        conn.close()

        return snapshot_id

    def record_milestone(self, name: str, target_files: List[str],
                        achieved: bool, asi_gain: float, description: str) -> int:
        """Record milestone achievement."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            INSERT INTO milestones
            (timestamp, milestone_name, target_files, achieved, asi_gain, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            name,
            json.dumps(target_files),
            achieved,
            asi_gain,
            description
        ))

        milestone_id = c.lastrowid
        conn.commit()
        conn.close()

        return milestone_id

    def update_target_status(self, target_file: str, status: str,
                            improvements: int, success_rate: float,
                            days_stable: int, ready: bool):
        """Update status of a specific target file."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            INSERT INTO target_status
            (timestamp, target_file, status, improvements, success_rate,
             days_stable, ready_for_next)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            target_file,
            status,
            improvements,
            success_rate,
            days_stable,
            ready
        ))

        conn.commit()
        conn.close()

    def record_asi_score(self, total: float, cognitive: float = 4.0,
                        autonomy: float = 7.0, creativity: float = 2.0,
                        social: float = 0.0, self_awareness: float = 3.0,
                        ethical: float = 2.0, notes: str = ""):
        """Record ASI score update."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            INSERT INTO asi_history
            (timestamp, total_score, cognitive, autonomy, creativity,
             social, self_awareness, ethical, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(),
            total,
            cognitive,
            autonomy,
            creativity,
            social,
            self_awareness,
            ethical,
            notes
        ))

        conn.commit()
        conn.close()

    def generate_report(self) -> str:
        """Generate comprehensive progress report."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        report = []
        report.append("=" * 70)
        report.append("PHASE 1 PROGRESS REPORT")
        report.append("=" * 70)
        report.append("")

        # Current status
        c.execute("""
            SELECT * FROM progress_snapshots
            ORDER BY timestamp DESC LIMIT 1
        """)
        latest = c.fetchone()

        if latest:
            report.append("📊 CURRENT STATUS:")
            report.append(f"   Phase: {latest[2]}")
            report.append(f"   Target: {latest[3]}")
            report.append(f"   Success Rate: {latest[7]:.1%}")
            report.append(f"   Performance Gain: {latest[8]:.1%}")
            report.append(f"   Safety Incidents: {latest[9]}")
            report.append(f"   ASI Score: {latest[10]:.1f}/50")
            report.append("")

        # Trend analysis
        c.execute("""
            SELECT timestamp, success_rate, performance_gain, asi_score
            FROM progress_snapshots
            ORDER BY timestamp DESC LIMIT 10
        """)
        history = c.fetchall()

        if len(history) > 1:
            report.append("📈 TREND ANALYSIS (Last 10 Snapshots):")

            # Success rate trend
            rates = [h[1] for h in history if h[1] is not None]
            if rates:
                avg_rate = sum(rates) / len(rates)
                trend = "↗️" if rates[0] > rates[-1] else "↘️" if rates[0] < rates[-1] else "→"
                report.append(f"   Success Rate: {trend} Average {avg_rate:.1%}")

            # Performance gain trend
            gains = [h[2] for h in history if h[2] is not None]
            if gains:
                total_gain = sum(gains)
                report.append(f"   Cumulative Gain: +{total_gain:.1%}")

            # ASI score trend
            scores = [h[3] for h in history if h[3] is not None]
            if scores:
                score_change = scores[0] - scores[-1]
                trend = "↗️" if score_change > 0 else "↘️" if score_change < 0 else "→"
                report.append(f"   ASI Score: {trend} {score_change:+.1f} points")

            report.append("")

        # Milestones
        c.execute("""
            SELECT milestone_name, achieved, asi_gain, description
            FROM milestones
            ORDER BY timestamp DESC
        """)
        milestones = c.fetchall()

        if milestones:
            report.append("🎯 MILESTONES:")
            for m in milestones:
                status = "✅" if m[1] else "⏳"
                report.append(f"   {status} {m[0]}")
                report.append(f"      ASI Gain: +{m[2]:.1f} points")
                report.append(f"      {m[3]}")
            report.append("")

        # Target status
        c.execute("""
            SELECT DISTINCT target_file, status, improvements, success_rate,
                   days_stable, ready_for_next
            FROM target_status
            WHERE timestamp IN (
                SELECT MAX(timestamp) FROM target_status GROUP BY target_file
            )
            ORDER BY timestamp DESC
        """)
        targets = c.fetchall()

        if targets:
            report.append("📁 TARGET FILES STATUS:")
            for t in targets:
                ready = "✅" if t[5] else "⏳"
                report.append(f"   {ready} {t[0]}")
                report.append(f"      Status: {t[1]}")
                report.append(f"      Improvements: {t[2]}")
                report.append(f"      Success Rate: {t[3]:.1%}")
                report.append(f"      Days Stable: {t[4]}")
            report.append("")

        # Phase 1 completion criteria
        report.append("✅ PHASE 1 COMPLETION CRITERIA:")
        report.append("")

        if latest:
            criteria = self.config["target_files"]["rollout_schedule"]["criteria"]

            # Successful cycles
            required_cycles = criteria["min_successful_cycles"]
            actual_cycles = latest[4]
            cycles_met = actual_cycles >= required_cycles
            status = "✅" if cycles_met else "❌"
            report.append(f"{status} Successful Cycles: {actual_cycles}/{required_cycles}")

            # Success rate
            required_rate = criteria["min_success_rate"]
            actual_rate = latest[7]
            rate_met = actual_rate >= required_rate if actual_rate else False
            status = "✅" if rate_met else "❌"
            report.append(f"{status} Success Rate: {actual_rate:.1%} (need {required_rate:.1%})")

            # Safety incidents
            max_incidents = criteria["max_safety_incidents"]
            actual_incidents = latest[9]
            incidents_met = actual_incidents <= max_incidents
            status = "✅" if incidents_met else "❌"
            report.append(f"{status} Safety Incidents: {actual_incidents}/{max_incidents}")

            # Performance gain
            required_gain = criteria["min_performance_gain"]
            actual_gain = latest[8] if latest[8] else 0.0
            gain_met = actual_gain >= required_gain
            status = "✅" if gain_met else "❌"
            report.append(f"{status} Performance Gain: {actual_gain:.1%} (need {required_gain:.1%})")

            report.append("")

            all_met = cycles_met and rate_met and incidents_met and gain_met
            if all_met:
                report.append("🎉 ALL CRITERIA MET - READY TO PROCEED!")
            else:
                report.append("⏳ Continue monitoring - not all criteria met yet")

        report.append("")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("=" * 70)

        conn.close()
        return "\n".join(report)

    def export_data(self, output_path: Optional[Path] = None) -> Path:
        """Export all tracking data to JSON."""
        if output_path is None:
            output_path = self.root_dir / f"phase1_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        data = {
            "export_time": datetime.now().isoformat(),
            "progress_snapshots": [],
            "milestones": [],
            "target_status": [],
            "asi_history": []
        }

        # Progress snapshots
        c.execute("SELECT * FROM progress_snapshots ORDER BY timestamp")
        for row in c.fetchall():
            data["progress_snapshots"].append({
                "id": row[0],
                "timestamp": row[1],
                "phase": row[2],
                "target_file": row[3],
                "total_commits": row[4],
                "successful_improvements": row[5],
                "failed_improvements": row[6],
                "rollback_count": row[7],
                "success_rate": row[8],
                "performance_gain": row[9],
                "safety_incidents": row[10],
                "asi_score": row[11],
                "notes": row[12]
            })

        # Milestones
        c.execute("SELECT * FROM milestones ORDER BY timestamp")
        for row in c.fetchall():
            data["milestones"].append({
                "id": row[0],
                "timestamp": row[1],
                "milestone_name": row[2],
                "target_files": json.loads(row[3]),
                "achieved": row[4],
                "asi_gain": row[5],
                "description": row[6]
            })

        # Target status
        c.execute("SELECT * FROM target_status ORDER BY timestamp")
        for row in c.fetchall():
            data["target_status"].append({
                "id": row[0],
                "timestamp": row[1],
                "target_file": row[2],
                "status": row[3],
                "improvements": row[4],
                "success_rate": row[5],
                "days_stable": row[6],
                "ready_for_next": row[7]
            })

        # ASI history
        c.execute("SELECT * FROM asi_history ORDER BY timestamp")
        for row in c.fetchall():
            data["asi_history"].append({
                "id": row[0],
                "timestamp": row[1],
                "total_score": row[2],
                "cognitive": row[3],
                "autonomy": row[4],
                "creativity": row[5],
                "social": row[6],
                "self_awareness": row[7],
                "ethical": row[8],
                "notes": row[9]
            })

        conn.close()

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        return output_path

    def _get_git_commits(self, target_file: Optional[str] = None) -> List[Dict]:
        """Get git commits for target file."""
        file_path = target_file or "intelligent-agents/sample_module.py"

        result = subprocess.run(
            ["git", "-C", str(self.root_dir), "log",
             "--since=30.days.ago",
             "--format=%H|%at|%s",
             "--", file_path],
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

    def _analyze_commits(self, commits: List[Dict]) -> Dict:
        """Analyze commits for success patterns."""
        successful = []
        failed = []
        rollbacks = []

        for commit in commits:
            msg = commit["message"].lower()
            if "rollback" in msg or "revert" in msg:
                rollbacks.append(commit)
                failed.append(commit)
            elif "optimize" in msg or "improve" in msg:
                successful.append(commit)

        total = len(commits) - len(rollbacks)

        return {
            "total_cycles": total,
            "successful": len(successful),
            "failed": len(failed),
            "rollbacks": len(rollbacks)
        }

    def _count_safety_incidents(self) -> int:
        """Count safety incidents in git history."""
        result = subprocess.run(
            ["git", "-C", str(self.root_dir), "log",
             "--since=30.days.ago",
             "--format=%s",
             "--grep=SAFETY",
             "--grep=EMERGENCY",
             "--grep=VIOLATION",
             "-i"],
            capture_output=True,
            text=True
        )

        incidents = [line for line in result.stdout.strip().split('\n') if line]
        return len(incidents)

    def _estimate_performance_gain(self, commits: List[Dict]) -> float:
        """Estimate cumulative performance gain."""
        total_gain = 0.0
        for commit in commits:
            msg = commit["message"].lower()
            if "improve" in msg or "optimize" in msg:
                total_gain += 0.075  # Conservative 7.5% per improvement

        return total_gain

    def _get_latest_asi_score(self) -> float:
        """Get latest ASI score from database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        c.execute("""
            SELECT total_score FROM asi_history
            ORDER BY timestamp DESC LIMIT 1
        """)

        result = c.fetchone()
        conn.close()

        return result[0] if result else 18.0  # Default to initial score


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Phase 1 Success Tracking")
    parser.add_argument("--record", action="store_true", help="Record current progress")
    parser.add_argument("--phase", default="1A", help="Current phase (default: 1A)")
    parser.add_argument("--target", help="Target file being tracked")
    parser.add_argument("--notes", default="", help="Notes about this snapshot")
    parser.add_argument("--report", action="store_true", help="Generate progress report")
    parser.add_argument("--export", action="store_true", help="Export data to JSON")
    parser.add_argument("--asi", action="store_true", help="Update ASI score")
    parser.add_argument("--milestone", help="Record milestone (JSON format)")

    args = parser.parse_args()

    tracker = Phase1Tracker()

    if args.record:
        print("Recording progress snapshot...")
        snapshot_id = tracker.record_progress(
            phase=args.phase,
            target_file=args.target,
            notes=args.notes
        )
        print(f"✅ Snapshot recorded (ID: {snapshot_id})")

    if args.report:
        report = tracker.generate_report()
        print(report)

        # Save to file
        report_path = Path(str(_STORAGE_BASE / "phase1_progress_report.txt"))
        with open(report_path, "w") as f:
            f.write(report)
        print(f"\n📄 Report saved to: {report_path}")

    if args.export:
        print("Exporting tracking data...")
        export_path = tracker.export_data()
        print(f"✅ Data exported to: {export_path}")

    if args.asi:
        print("Recording initial ASI score (18/50)...")
        tracker.record_asi_score(
            total=18.0,
            cognitive=4.0,
            autonomy=7.0,
            creativity=2.0,
            social=0.0,
            self_awareness=3.0,
            ethical=2.0,
            notes="Baseline ASI assessment - recursive self-improvement in narrow domain"
        )
        print("✅ ASI score recorded")

    if args.milestone:
        milestone_data = json.loads(args.milestone)
        print(f"Recording milestone: {milestone_data['name']}...")
        tracker.record_milestone(
            name=milestone_data["name"],
            target_files=milestone_data["target_files"],
            achieved=milestone_data["achieved"],
            asi_gain=milestone_data["asi_gain"],
            description=milestone_data["description"]
        )
        print("✅ Milestone recorded")

    if not any([args.record, args.report, args.export, args.asi, args.milestone]):
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
