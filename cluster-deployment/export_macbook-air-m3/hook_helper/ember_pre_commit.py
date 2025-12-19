#!/usr/bin/env python3
"""
Ember Pre-Commit Gate
The ONE blocking checkpoint: Before code leaves your machine

Philosophy: Trust during development, verify before commit
"""

import json
import sys
import subprocess
from pathlib import Path
from typing import List, Dict

VIOLATIONS_LOG = Path.home() / ".claude" / "ember_violations.jsonl"

class PreCommitGate:
    """Final checkpoint before code leaves the machine"""

    def __init__(self):
        self.recent_violations = self._load_recent_violations(hours=1)

    def _load_recent_violations(self, hours: int) -> List[Dict]:
        """Load violations from last N hours"""
        import time
        violations = []

        if VIOLATIONS_LOG.exists():
            cutoff = time.time() - (hours * 3600)
            with open(VIOLATIONS_LOG) as f:
                for line in f:
                    try:
                        v = json.loads(line)
                        if v.get("timestamp", 0) > cutoff:
                            violations.append(v)
                    except:
                        pass

        return violations

    def get_staged_files(self) -> List[str]:
        """Get files staged for commit"""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True,
                text=True,
                check=True
            )
            return [f.strip() for f in result.stdout.split("\n") if f.strip()]
        except:
            return []

    def get_violations_for_staged_files(self) -> List[Dict]:
        """Get violations in staged files"""
        staged_files = self.get_staged_files()

        violations = []
        for v in self.recent_violations:
            file_path = v.get("file_path", "")

            # Check if violation file is staged
            for staged in staged_files:
                if staged in file_path or file_path.endswith(staged):
                    violations.append(v)
                    break

        return violations

    def filter_critical(self, violations: List[Dict]) -> List[Dict]:
        """Filter to only critical/escalate tier violations"""
        return [
            v for v in violations
            if v.get("tier") in ["escalate", "intervene"]
        ]

    def run(self) -> bool:
        """
        Run pre-commit check

        Returns:
            True: Allow commit
            False: Block commit
        """
        violations = self.get_violations_for_staged_files()
        critical = self.filter_critical(violations)

        if not critical:
            # No critical violations - allow commit
            return True

        # Show violations
        print("\n🔥 Ember Pre-Commit Check:")
        print("=" * 60)

        for i, v in enumerate(critical, 1):
            tier = v.get("tier", "unknown").upper()
            file_path = v.get("file_path", "unknown")
            risk = v.get("risk_score", 0)
            patterns = v.get("patterns", [])

            print(f"\n{i}. [{tier}] {file_path}")
            print(f"   Risk: {risk:.2f}")

            if patterns:
                pattern_types = [p.get("type", "unknown") for p in patterns]
                print(f"   Concerns: {', '.join(set(pattern_types))}")

        print("\n" + "=" * 60)

        # Check for secrets (auto-block)
        has_secrets = any(
            any(p.get("type") == "secrets" for p in v.get("patterns", []))
            for v in critical
        )

        if has_secrets:
            print("\n🚨 BLOCKED: Credentials/secrets detected in staged files.")
            print("   Remove secrets before committing.")
            print("   Use environment variables or secret management instead.")
            return False

        # Ask user for other violations
        print("\n⚠️  Critical issues found in staged files.")
        print("   You can:")
        print("   - [n] Fix issues before committing (recommended)")
        print("   - [y] Commit anyway (override)")
        print("   - [s] Show details")

        while True:
            response = input("\nProceed with commit? (y/n/s): ").lower().strip()

            if response == 's':
                # Show details
                for v in critical:
                    print(f"\n{v.get('file_path')}:")
                    snippet = v.get("code_snippet", "")
                    if snippet:
                        print(f"  {snippet[:100]}...")
                continue

            elif response in ['y', 'yes']:
                # User overrides - log but allow
                self._log_override(critical)
                print("\n✓ Commit allowed (override logged)")
                return True

            elif response in ['n', 'no']:
                # User will fix - block commit
                print("\n✗ Commit blocked. Please address issues above.")
                return False

            else:
                print("Invalid input. Please enter y, n, or s.")

    def _log_override(self, violations: List[Dict]) -> None:
        """Log commit override for learning"""
        import time

        override_log = Path.home() / ".claude" / "ember_overrides.jsonl"
        entry = {
            "timestamp": time.time(),
            "violations_count": len(violations),
            "violations": violations
        }

        with open(override_log, "a") as f:
            f.write(json.dumps(entry) + "\n")

def main() -> int:
    """
    Main entry point for git pre-commit hook

    Returns:
        0: Allow commit
        1: Block commit
    """
    try:
        gate = PreCommitGate()
        allowed = gate.run()
        return 0 if allowed else 1

    except Exception as e:
        # On error, fail open (allow commit)
        print(f"\n⚠️  Ember pre-commit check error: {e}")
        print("Allowing commit (fail-open)")
        return 0

if __name__ == "__main__":
    sys.exit(main())
