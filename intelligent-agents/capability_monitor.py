#!/usr/bin/env python3
"""
Capability Monitor - AGI System Capability Registry Integration

Purpose: Provides functions to query, update, and monitor AGI capabilities
         from the capability_registry.db database.

Phase 5 Implementation: Persistent capability tracking with automated recovery

Key Functions:
- get_capability_status(capability_id) - Query current capability status
- update_capability_status(capability_id, status, notes) - Update status
- record_capability_check(capability_id, status, health_score, notes) - Record check
- get_recovery_procedures(capability_id) - Retrieve recovery steps
- execute_recovery(capability_id) - Automated recovery execution
- get_all_capabilities() - List all registered capabilities
- get_dormant_capabilities() - Find capabilities needing attention
- get_capability_history(capability_id, days) - Historical status tracking

Integration Points:
- Self-care agent health checks
- Pre-tool-use hook capability discovery
- Autonomous improvement daemon monitoring
- Enhanced-memory storage for trends

Author: AGI System
Created: 2025-11-19 (Phase 5)
"""

import sqlite3
from storage_path_utils import get_database_path, get_logs_path, STORAGE_BASE
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Database path
DB_PATH = get_database_path("capability_registry.db")


@dataclass
class Capability:
    """Capability data structure"""
    capability_id: str
    capability_name: str
    capability_type: str
    location: str
    status: str
    last_checked: Optional[str]
    last_active: Optional[str]
    integration_method: Optional[str]
    criticality: str
    recovery_command: Optional[str]
    health_check_command: Optional[str]
    description: Optional[str]


@dataclass
class CapabilityCheck:
    """Capability check record"""
    check_id: Optional[int]
    capability_id: str
    timestamp: str
    status: str
    notes: Optional[str]
    health_score: Optional[int]


@dataclass
class RecoveryProcedure:
    """Recovery procedure step"""
    procedure_id: int
    capability_id: str
    step_number: int
    step_description: str
    step_command: Optional[str]
    expected_outcome: Optional[str]
    verification_command: Optional[str]


class CapabilityMonitor:
    """
    Capability Registry Monitor

    Provides interface to capability_registry.db for health monitoring
    and automated recovery.
    """

    def __init__(self, db_path: Path = DB_PATH):
        """Initialize capability monitor"""
        self.db_path = db_path
        self._ensure_database_exists()

    def _ensure_database_exists(self):
        """Verify database exists"""
        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Capability registry database not found: {self.db_path}\n"
                "Run create_capability_registry.sql first"
            )

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # ============================================================
    # CAPABILITY QUERIES
    # ============================================================

    def get_capability(self, capability_id: str) -> Optional[Capability]:
        """Get capability by ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM capabilities WHERE capability_id = ?",
                (capability_id,)
            )
            row = cursor.fetchone()
            if row:
                return Capability(**dict(row))
            return None

    def get_all_capabilities(self) -> List[Capability]:
        """Get all registered capabilities"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM capabilities ORDER BY criticality DESC, capability_name")
            return [Capability(**dict(row)) for row in cursor.fetchall()]

    def get_capabilities_by_status(self, status: str) -> List[Capability]:
        """Get capabilities by status (active, dormant, missing, error)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM capabilities WHERE status = ? ORDER BY criticality DESC",
                (status,)
            )
            return [Capability(**dict(row)) for row in cursor.fetchall()]

    def get_capabilities_by_criticality(self, criticality: str) -> List[Capability]:
        """Get capabilities by criticality (critical, important, optional)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM capabilities WHERE criticality = ? ORDER BY capability_name",
                (criticality,)
            )
            return [Capability(**dict(row)) for row in cursor.fetchall()]

    def get_dormant_capabilities(self) -> List[Capability]:
        """Get all capabilities not in 'active' status"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM capabilities WHERE status != 'active' ORDER BY criticality DESC"
            )
            return [Capability(**dict(row)) for row in cursor.fetchall()]

    # ============================================================
    # CAPABILITY STATUS UPDATES
    # ============================================================

    def update_capability_status(
        self,
        capability_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Update capability status

        Args:
            capability_id: Capability identifier
            status: New status (active, dormant, missing, error)
            notes: Optional notes about status change

        Returns:
            True if updated successfully
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Update status and last_checked
            cursor.execute(
                """
                UPDATE capabilities
                SET status = ?, last_checked = datetime('now')
                WHERE capability_id = ?
                """,
                (status, capability_id)
            )

            # If status is 'active', update last_active
            if status == 'active':
                cursor.execute(
                    """
                    UPDATE capabilities
                    SET last_active = datetime('now')
                    WHERE capability_id = ?
                    """,
                    (capability_id,)
                )

            conn.commit()
            return cursor.rowcount > 0

    # ============================================================
    # CAPABILITY HEALTH CHECKS
    # ============================================================

    def check_capability_health(self, capability_id: str) -> Tuple[str, int, Optional[str]]:
        """
        Execute health check for capability

        Args:
            capability_id: Capability identifier

        Returns:
            Tuple of (status, health_score, notes)
        """
        capability = self.get_capability(capability_id)
        if not capability:
            return ("missing", 0, f"Capability '{capability_id}' not found in registry")

        if not capability.health_check_command:
            return ("unknown", 50, "No health check command defined")

        try:
            # Execute health check command
            result = subprocess.run(
                capability.health_check_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Health check passed
                status = "active"
                health_score = 100
                notes = "Health check passed"
            else:
                # Health check failed
                status = "dormant"
                health_score = 0
                notes = f"Health check failed: {result.stderr[:200]}"

        except subprocess.TimeoutExpired:
            status = "error"
            health_score = 0
            notes = "Health check command timed out"
        except Exception as e:
            status = "error"
            health_score = 0
            notes = f"Health check error: {str(e)[:200]}"

        return (status, health_score, notes)

    def record_capability_check(
        self,
        capability_id: str,
        status: str,
        health_score: int,
        notes: Optional[str] = None
    ) -> int:
        """
        Record a capability check in the database

        Args:
            capability_id: Capability identifier
            status: Detected status
            health_score: Health score (0-100)
            notes: Optional notes

        Returns:
            check_id of the recorded check
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO capability_checks (capability_id, status, health_score, notes)
                VALUES (?, ?, ?, ?)
                """,
                (capability_id, status, health_score, notes)
            )
            conn.commit()
            return cursor.lastrowid

    def perform_and_record_check(self, capability_id: str) -> Dict:
        """
        Perform health check and record results

        Args:
            capability_id: Capability identifier

        Returns:
            Dictionary with check results
        """
        # Execute health check
        status, health_score, notes = self.check_capability_health(capability_id)

        # Update capability status
        self.update_capability_status(capability_id, status, notes)

        # Record check
        check_id = self.record_capability_check(capability_id, status, health_score, notes)

        return {
            "capability_id": capability_id,
            "check_id": check_id,
            "status": status,
            "health_score": health_score,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        }

    def check_all_capabilities(self) -> List[Dict]:
        """
        Check all registered capabilities

        Returns:
            List of check results for all capabilities
        """
        capabilities = self.get_all_capabilities()
        results = []

        for capability in capabilities:
            result = self.perform_and_record_check(capability.capability_id)
            results.append(result)

        return results

    # ============================================================
    # CAPABILITY HISTORY
    # ============================================================

    def get_capability_history(
        self,
        capability_id: str,
        days: int = 7
    ) -> List[CapabilityCheck]:
        """
        Get capability check history

        Args:
            capability_id: Capability identifier
            days: Number of days of history (default 7)

        Returns:
            List of capability checks
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            since = (datetime.now() - timedelta(days=days)).isoformat()
            cursor.execute(
                """
                SELECT * FROM capability_checks
                WHERE capability_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                """,
                (capability_id, since)
            )
            return [CapabilityCheck(**dict(row)) for row in cursor.fetchall()]

    def get_recent_status_changes(self, hours: int = 24) -> List[Dict]:
        """
        Get capabilities with status changes in recent hours

        Args:
            hours: Number of hours to look back (default 24)

        Returns:
            List of capabilities with recent status changes
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            cursor.execute(
                """
                SELECT c.capability_id, c.capability_name, c.criticality,
                       cc.status, cc.timestamp, cc.health_score, cc.notes
                FROM capabilities c
                JOIN capability_checks cc ON c.capability_id = cc.capability_id
                WHERE cc.timestamp >= ?
                ORDER BY cc.timestamp DESC
                """,
                (since,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ============================================================
    # RECOVERY PROCEDURES
    # ============================================================

    def get_recovery_procedures(self, capability_id: str) -> List[RecoveryProcedure]:
        """
        Get recovery procedures for capability

        Args:
            capability_id: Capability identifier

        Returns:
            List of recovery procedure steps
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM recovery_procedures
                WHERE capability_id = ?
                ORDER BY step_number
                """,
                (capability_id,)
            )
            return [RecoveryProcedure(**dict(row)) for row in cursor.fetchall()]

    def execute_recovery_step(
        self,
        procedure: RecoveryProcedure,
        dry_run: bool = False
    ) -> Dict:
        """
        Execute a single recovery procedure step

        Args:
            procedure: RecoveryProcedure to execute
            dry_run: If True, don't actually execute (default False)

        Returns:
            Dictionary with execution results
        """
        if not procedure.step_command:
            return {
                "step": procedure.step_number,
                "success": True,
                "notes": "No command to execute (manual step)",
                "dry_run": dry_run
            }

        if dry_run:
            return {
                "step": procedure.step_number,
                "command": procedure.step_command,
                "success": True,
                "notes": "Dry run - command not executed",
                "dry_run": True
            }

        try:
            # Execute recovery command
            result = subprocess.run(
                procedure.step_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            success = result.returncode == 0

            # Verify if verification command provided
            if success and procedure.verification_command:
                verify_result = subprocess.run(
                    procedure.verification_command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                success = verify_result.returncode == 0

            return {
                "step": procedure.step_number,
                "command": procedure.step_command,
                "success": success,
                "stdout": result.stdout[:500],
                "stderr": result.stderr[:500],
                "notes": procedure.expected_outcome if success else "Step failed",
                "dry_run": False
            }

        except subprocess.TimeoutExpired:
            return {
                "step": procedure.step_number,
                "command": procedure.step_command,
                "success": False,
                "notes": "Command timed out",
                "dry_run": False
            }
        except Exception as e:
            return {
                "step": procedure.step_number,
                "command": procedure.step_command,
                "success": False,
                "notes": f"Error: {str(e)}",
                "dry_run": False
            }

    def execute_recovery(
        self,
        capability_id: str,
        dry_run: bool = False
    ) -> Dict:
        """
        Execute full recovery procedure for capability

        Args:
            capability_id: Capability identifier
            dry_run: If True, don't actually execute commands (default False)

        Returns:
            Dictionary with recovery results
        """
        capability = self.get_capability(capability_id)
        if not capability:
            return {
                "success": False,
                "notes": f"Capability '{capability_id}' not found"
            }

        # Get recovery procedures
        procedures = self.get_recovery_procedures(capability_id)

        if not procedures:
            # No recovery procedures defined, try recovery_command
            if capability.recovery_command:
                try:
                    if dry_run:
                        return {
                            "success": True,
                            "capability_id": capability_id,
                            "command": capability.recovery_command,
                            "notes": "Dry run - recovery command not executed",
                            "dry_run": True
                        }

                    result = subprocess.run(
                        capability.recovery_command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    success = result.returncode == 0

                    if success:
                        # Re-check health after recovery
                        status, health_score, notes = self.check_capability_health(capability_id)
                        self.update_capability_status(capability_id, status, notes)

                    return {
                        "success": success,
                        "capability_id": capability_id,
                        "command": capability.recovery_command,
                        "stdout": result.stdout[:500],
                        "stderr": result.stderr[:500],
                        "dry_run": False
                    }

                except Exception as e:
                    return {
                        "success": False,
                        "capability_id": capability_id,
                        "notes": f"Recovery failed: {str(e)}",
                        "dry_run": False
                    }
            else:
                return {
                    "success": False,
                    "capability_id": capability_id,
                    "notes": "No recovery procedures or recovery command defined"
                }

        # Execute recovery procedure steps
        step_results = []
        all_successful = True

        for procedure in procedures:
            step_result = self.execute_recovery_step(procedure, dry_run)
            step_results.append(step_result)

            if not step_result["success"]:
                all_successful = False
                break  # Stop on first failure

        # Re-check health if recovery successful (and not dry run)
        if all_successful and not dry_run:
            status, health_score, notes = self.check_capability_health(capability_id)
            self.update_capability_status(capability_id, status, notes)

        return {
            "success": all_successful,
            "capability_id": capability_id,
            "steps_executed": len(step_results),
            "steps": step_results,
            "dry_run": dry_run
        }

    # ============================================================
    # SYSTEM-WIDE HEALTH REPORT
    # ============================================================

    def generate_system_health_report(self) -> Dict:
        """
        Generate comprehensive system health report

        Returns:
            Dictionary with complete system health assessment
        """
        capabilities = self.get_all_capabilities()

        # Check all capabilities
        check_results = []
        for capability in capabilities:
            result = self.perform_and_record_check(capability.capability_id)
            check_results.append(result)

        # Categorize by status
        active = [r for r in check_results if r["status"] == "active"]
        dormant = [r for r in check_results if r["status"] == "dormant"]
        missing = [r for r in check_results if r["status"] == "missing"]
        error = [r for r in check_results if r["status"] == "error"]

        # Categorize by criticality
        critical_capabilities = self.get_capabilities_by_criticality("critical")
        critical_issues = [
            r for r in check_results
            if r["capability_id"] in [c.capability_id for c in critical_capabilities]
            and r["status"] != "active"
        ]

        # Calculate overall health score
        if check_results:
            avg_health = sum(r["health_score"] for r in check_results) / len(check_results)
        else:
            avg_health = 0

        # Determine overall status
        if critical_issues:
            overall_status = "critical"
        elif dormant or error:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status,
            "overall_health_score": round(avg_health, 1),
            "total_capabilities": len(capabilities),
            "active": len(active),
            "dormant": len(dormant),
            "missing": len(missing),
            "error": len(error),
            "critical_issues": len(critical_issues),
            "critical_issue_details": critical_issues,
            "capability_details": check_results,
            "recommendations": self._generate_recommendations(check_results, critical_issues)
        }

    def _generate_recommendations(
        self,
        check_results: List[Dict],
        critical_issues: List[Dict]
    ) -> List[str]:
        """Generate actionable recommendations based on health check results"""
        recommendations = []

        if critical_issues:
            recommendations.append(
                f"⚠️ CRITICAL: {len(critical_issues)} critical capabilities are not active. "
                "Immediate attention required."
            )
            for issue in critical_issues:
                cap = self.get_capability(issue["capability_id"])
                if cap and cap.recovery_command:
                    recommendations.append(
                        f"  → Run recovery for {cap.capability_name}: "
                        f"capability_monitor.execute_recovery('{cap.capability_id}')"
                    )

        dormant = [r for r in check_results if r["status"] == "dormant"]
        if dormant:
            recommendations.append(
                f"⚠️ {len(dormant)} capabilities are dormant. Review and restart if needed."
            )

        error = [r for r in check_results if r["status"] == "error"]
        if error:
            recommendations.append(
                f"⚠️ {len(error)} capabilities have errors. Check logs and fix issues."
            )

        if not recommendations:
            recommendations.append("✅ All systems healthy. No action required.")

        return recommendations


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def get_monitor() -> CapabilityMonitor:
    """Get capability monitor instance"""
    return CapabilityMonitor()


def check_all() -> List[Dict]:
    """Quick check all capabilities"""
    monitor = get_monitor()
    return monitor.check_all_capabilities()


def get_system_health() -> Dict:
    """Quick system health report"""
    monitor = get_monitor()
    return monitor.generate_system_health_report()


def recover(capability_id: str, dry_run: bool = False) -> Dict:
    """Quick recovery execution"""
    monitor = get_monitor()
    return monitor.execute_recovery(capability_id, dry_run)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import sys

    # CLI interface for testing
    if len(sys.argv) < 2:
        print("Usage: capability_monitor.py <command> [args]")
        print()
        print("Commands:")
        print("  list                      - List all capabilities")
        print("  check <capability_id>     - Check specific capability")
        print("  check-all                 - Check all capabilities")
        print("  health                    - Generate system health report")
        print("  recover <capability_id>   - Execute recovery (dry run)")
        print("  recover! <capability_id>  - Execute recovery (actual)")
        print("  history <capability_id>   - Show capability history")
        sys.exit(1)

    command = sys.argv[1]
    monitor = get_monitor()

    if command == "list":
        capabilities = monitor.get_all_capabilities()
        for cap in capabilities:
            print(f"{cap.capability_id:40} {cap.status:10} [{cap.criticality}] {cap.capability_name}")

    elif command == "check" and len(sys.argv) > 2:
        capability_id = sys.argv[2]
        result = monitor.perform_and_record_check(capability_id)
        print(json.dumps(result, indent=2))

    elif command == "check-all":
        results = monitor.check_all_capabilities()
        print(json.dumps(results, indent=2))

    elif command == "health":
        report = monitor.generate_system_health_report()
        print(json.dumps(report, indent=2))

    elif command == "recover" and len(sys.argv) > 2:
        capability_id = sys.argv[2]
        result = monitor.execute_recovery(capability_id, dry_run=True)
        print(json.dumps(result, indent=2))

    elif command == "recover!" and len(sys.argv) > 2:
        capability_id = sys.argv[2]
        result = monitor.execute_recovery(capability_id, dry_run=False)
        print(json.dumps(result, indent=2))

    elif command == "history" and len(sys.argv) > 2:
        capability_id = sys.argv[2]
        history = monitor.get_capability_history(capability_id, days=7)
        for check in history:
            print(f"{check.timestamp} {check.status:10} score={check.health_score:3} {check.notes}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
