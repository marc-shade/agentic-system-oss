#!/usr/bin/env python3
"""
Phase 1 Restart Verification Script
====================================

Verifies system integrity after restart (graceful or crash).
Checks all persistence layers and reports readiness to continue.

Usage:
    python3 verify_phase1_restart.py

Exit Codes:
    0 - All checks passed, ready to continue
    1 - Some checks failed, needs attention
    2 - Critical failures, manual intervention required
"""
import platform

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

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



class Phase1RestartVerifier:
    """Verify system state after restart."""

    def __init__(self):
        self.root_dir = Path(str(_STORAGE_BASE))
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = []
        self.errors = []

    def verify_all(self) -> Tuple[bool, Dict]:
        """Run all verification checks."""
        print("=" * 70)
        print("PHASE 1 RESTART VERIFICATION")
        print("=" * 70)
        print()

        results = {
            "timestamp": datetime.now().isoformat(),
            "checks": {}
        }

        # Run all checks
        checks = [
            ("Critical Files", self._check_critical_files),
            ("Configuration", self._check_configuration),
            ("State File", self._check_state_file),
            ("Databases", self._check_databases),
            ("Git Repository", self._check_git_repository),
            ("Target Files", self._check_target_files),
            ("Autonomous Loop", self._check_autonomous_loop),
            ("Progress Tracking", self._check_progress_tracking)
        ]

        for name, check_func in checks:
            print(f"🔍 Checking {name}...", end=" ")
            passed, details = check_func()
            results["checks"][name] = {
                "passed": passed,
                "details": details
            }

            if passed:
                print("✅")
                self.checks_passed += 1
            else:
                print("❌")
                self.checks_failed += 1
                self.errors.append(f"{name}: {details}")

        print()
        print("=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        print()
        print(f"✅ Checks Passed: {self.checks_passed}/{self.checks_passed + self.checks_failed}")
        print(f"❌ Checks Failed: {self.checks_failed}/{self.checks_passed + self.checks_failed}")
        print()

        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   - {warning}")
            print()

        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"   - {error}")
            print()

        # Overall status
        if self.checks_failed == 0:
            print("✅ ALL CHECKS PASSED - System ready to continue")
            print()
            self._print_current_state()
            return True, results
        elif self.checks_failed <= 2:
            print("⚠️  SOME CHECKS FAILED - Review errors above")
            print("   System may still be operational")
            return False, results
        else:
            print("❌ CRITICAL FAILURES - Manual intervention required")
            print("   Review RECOVERY_PROCEDURES.md")
            return False, results

    def _check_critical_files(self) -> Tuple[bool, str]:
        """Check all critical files exist."""
        critical_files = [
            "agi_config.json",
            ".phase1_state.json",
            "STRATEGIC_ROADMAP_TO_40.md",
            "ASI_SELF_ASSESSMENT.md",
            "PHASE1_MONITORING_CHECKLIST.md",
            "PRODUCTION_TARGETS_ROLLOUT.md",
            "PHASE1_PREPARATION_COMPLETE.md",
            "RECOVERY_PROCEDURES.md",
            "phase1_monitor.py",
            "phase1_tracker.py",
            "verify_phase1_restart.py",
            "autonomous_recursive_agi_loop.py"
        ]

        missing = []
        for file in critical_files:
            path = self.root_dir / file
            if not path.exists():
                missing.append(file)

        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        return True, f"All {len(critical_files)} critical files present"

    def _check_configuration(self) -> Tuple[bool, str]:
        """Check configuration file is valid."""
        config_path = self.root_dir / "agi_config.json"

        try:
            with open(config_path) as f:
                config = json.load(f)

            # Verify key sections
            required_keys = ["mode", "knowledge_acquisition", "target_files", "safety"]
            missing_keys = [k for k in required_keys if k not in config]
            if missing_keys:
                return False, f"Missing config keys: {', '.join(missing_keys)}"

            # Verify production targets
            targets = config.get("target_files", {}).get("production_targets", [])
            if len(targets) != 10:
                self.warnings.append(f"Expected 10 production targets, found {len(targets)}")

            return True, f"Configuration valid - {len(targets)} production targets"

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except Exception as e:
            return False, f"Error reading config: {e}"

    def _check_state_file(self) -> Tuple[bool, str]:
        """Check state file is valid and current."""
        state_path = self.root_dir / ".phase1_state.json"

        try:
            with open(state_path) as f:
                state = json.load(f)

            current_phase = state.get("current_phase", "Unknown")
            status = state.get("status", "Unknown")
            target = state.get("target_file", "Unknown")

            return True, f"Phase {current_phase} ({status}) - Target: {target}"

        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"
        except FileNotFoundError:
            return False, "State file not found"
        except Exception as e:
            return False, f"Error reading state: {e}"

    def _check_databases(self) -> Tuple[bool, str]:
        """Check databases are accessible."""
        databases = {
            "phase1_tracking.db": "databases/phase1_tracking.db",
            "memory.db": "agent-memory/enhanced_memories/memory.db"
        }

        accessible = []
        inaccessible = []

        for name, path in databases.items():
            full_path = self.root_dir / path
            if full_path.exists():
                try:
                    conn = sqlite3.connect(full_path)
                    conn.execute("SELECT 1")
                    conn.close()
                    accessible.append(name)
                except Exception as e:
                    inaccessible.append(f"{name}: {e}")
            else:
                inaccessible.append(f"{name}: not found")

        if inaccessible:
            return False, f"Inaccessible: {', '.join(inaccessible)}"
        return True, f"All {len(accessible)} databases accessible"

    def _check_git_repository(self) -> Tuple[bool, str]:
        """Check git repository is healthy."""
        try:
            # Check if it's a git repo
            result = subprocess.run(
                ["git", "-C", str(self.root_dir), "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return False, "Not a git repository"

            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "-C", str(self.root_dir), "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=5
            )

            uncommitted = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            if uncommitted > 5:
                self.warnings.append(f"{uncommitted} uncommitted changes")

            # Get recent commits count
            result = subprocess.run(
                ["git", "-C", str(self.root_dir), "log", "--oneline", "--since=7.days.ago"],
                capture_output=True,
                text=True,
                timeout=5
            )

            recent_commits = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0

            return True, f"Git healthy - {recent_commits} commits in last 7 days"

        except subprocess.TimeoutExpired:
            return False, "Git command timeout"
        except Exception as e:
            return False, f"Git error: {e}"

    def _check_target_files(self) -> Tuple[bool, str]:
        """Check all target files exist."""
        # Read targets from config
        config_path = self.root_dir / "agi_config.json"
        try:
            with open(config_path) as f:
                config = json.load(f)

            practice_targets = config.get("target_files", {}).get("practice_targets", [])
            production_targets = config.get("target_files", {}).get("production_targets", [])
            targets = practice_targets + production_targets

        except Exception as e:
            # Fallback to hardcoded list if config read fails
            targets = ["intelligent-agents/sample_module.py"]
            self.warnings.append(f"Could not read targets from config: {e}")

        missing = []
        for target in targets:
            path = self.root_dir / target
            if not path.exists():
                missing.append(target)

        if missing:
            return False, f"Missing targets: {', '.join(missing)}"
        return True, f"All {len(targets)} target files present"

    def _check_autonomous_loop(self) -> Tuple[bool, str]:
        """Check autonomous loop status."""
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5
            )

            loop_running = "autonomous_recursive_agi_loop.py" in result.stdout

            if loop_running:
                # Extract PID
                for line in result.stdout.split('\n'):
                    if "autonomous_recursive_agi_loop.py" in line:
                        parts = line.split()
                        pid = parts[1] if len(parts) > 1 else "unknown"
                        return True, f"Running (PID: {pid})"

            return False, "Not running - restart with: python3 autonomous_recursive_agi_loop.py &"

        except Exception as e:
            return False, f"Error checking loop: {e}"

    def _check_progress_tracking(self) -> Tuple[bool, str]:
        """Check progress tracking operational."""
        db_path = self.root_dir / "databases" / "phase1_tracking.db"

        try:
            conn = sqlite3.connect(db_path)
            c = conn.cursor()

            # Check snapshots
            c.execute("SELECT COUNT(*) FROM progress_snapshots")
            snapshots = c.fetchone()[0]

            # Check ASI history
            c.execute("SELECT COUNT(*) FROM asi_history")
            asi_records = c.fetchone()[0]

            # Get latest snapshot
            c.execute("""
                SELECT timestamp, phase, success_rate, asi_score
                FROM progress_snapshots
                ORDER BY timestamp DESC LIMIT 1
            """)
            latest = c.fetchone()

            conn.close()

            if latest:
                return True, f"{snapshots} snapshots, {asi_records} ASI records - Latest: Phase {latest[1]}"
            elif snapshots == 0:
                self.warnings.append("No progress snapshots yet")
                return True, "Database initialized but empty"
            else:
                return True, f"{snapshots} snapshots, {asi_records} ASI records"

        except sqlite3.OperationalError as e:
            return False, f"Database error: {e}"
        except Exception as e:
            return False, f"Error checking tracking: {e}"

    def _print_current_state(self):
        """Print current phase state."""
        try:
            state_path = self.root_dir / ".phase1_state.json"
            with open(state_path) as f:
                state = json.load(f)

            print("📊 CURRENT STATE:")
            print(f"   Mission: {state.get('mission', 'Unknown')}")
            print(f"   Phase: {state.get('current_phase', 'Unknown')} - {state.get('phase_name', 'Unknown')}")
            print(f"   Target: {state.get('target_file', 'Unknown')}")
            print(f"   Status: {state.get('status', 'Unknown')}")
            print(f"   ASI Score: {state.get('asi_score_start', 0)}/50 → {state.get('asi_score_target', 0)}/50")
            print()

            # Print next steps
            print("📋 NEXT STEPS:")
            print("   1. Run: python3 phase1_monitor.py")
            print("   2. Check: python3 phase1_tracker.py --report")
            if not self._is_autonomous_loop_running():
                print("   3. Start loop: python3 autonomous_recursive_agi_loop.py &")
            print()

        except Exception:
            pass

    def _is_autonomous_loop_running(self) -> bool:
        """Check if autonomous loop is running."""
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return "autonomous_recursive_agi_loop.py" in result.stdout
        except Exception:
            return False


def main():
    """Main entry point."""
    verifier = Phase1RestartVerifier()

    try:
        all_passed, results = verifier.verify_all()

        if all_passed:
            return 0
        elif verifier.checks_failed <= 2:
            return 1
        else:
            return 2

    except KeyboardInterrupt:
        print("\n⚠️  Verification interrupted")
        return 1
    except Exception as e:
        print(f"\n❌ Verification error: {e}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
