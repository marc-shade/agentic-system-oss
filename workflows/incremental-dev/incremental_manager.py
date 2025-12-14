#!/usr/bin/env python3
"""
Incremental Development Workflow Manager

Provides utilities for managing the incremental development workflow state.
Used by Claude Code during implementation to track progress.
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional


class IncrementalManager:
    """Manage incremental development workflow state."""

    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.features_path = self.project_path / "features.json"
        self.progress_path = self.project_path / "progress.md"
        self.config_path = self.project_path / ".incremental" / "config.json"

    def load_features(self) -> dict:
        """Load features.json."""
        if not self.features_path.exists():
            raise FileNotFoundError(f"features.json not found at {self.features_path}")

        with open(self.features_path) as f:
            return json.load(f)

    def save_features(self, features_data: dict) -> None:
        """Save features.json with updated timestamp."""
        features_data["metadata"]["last_updated"] = self._timestamp()
        with open(self.features_path, "w") as f:
            json.dump(features_data, f, indent=2)

    def get_next_feature(self) -> Optional[dict]:
        """Get the next feature to implement based on priority and dependencies."""
        data = self.load_features()
        completed_ids = {f["id"] for f in data["features"] if f.get("committed", False)}

        for feature in sorted(data["features"], key=lambda x: x.get("priority", 5)):
            if feature.get("committed", False):
                continue

            # Check dependencies
            deps = feature.get("dependencies", [])
            if all(dep in completed_ids for dep in deps):
                return feature

        return None

    def get_status(self) -> dict:
        """Get current workflow status."""
        data = self.load_features()

        completed = [f for f in data["features"] if f.get("committed", False)]
        in_progress = [f for f in data["features"] if f.get("implemented", False) and not f.get("committed", False)]
        pending = [f for f in data["features"] if not f.get("implemented", False)]

        return {
            "project": data["project"],
            "total": len(data["features"]),
            "completed": len(completed),
            "in_progress": len(in_progress),
            "pending": len(pending),
            "percentage": round(len(completed) / len(data["features"]) * 100, 1) if data["features"] else 0,
            "completed_features": completed,
            "in_progress_features": in_progress,
            "pending_features": pending,
            "next_feature": self.get_next_feature()
        }

    def mark_test_passed(self, feature_id: str, test_id: str, passed: bool = True, error: str = None) -> None:
        """Mark a specific test as passed or failed."""
        data = self.load_features()

        for feature in data["features"]:
            if feature["id"] == feature_id:
                for test in feature["tests"]:
                    if test["id"] == test_id:
                        test["passed"] = passed
                        test["last_run"] = self._timestamp()
                        if error:
                            test["error"] = error
                        elif "error" in test:
                            del test["error"]
                        break
                break

        self.save_features(data)

    def mark_feature_implemented(self, feature_id: str, notes: str = "") -> None:
        """Mark a feature as implemented (code written, not yet verified)."""
        data = self.load_features()

        for feature in data["features"]:
            if feature["id"] == feature_id:
                feature["implemented"] = True
                feature["notes"] = notes
                break

        self.save_features(data)

    def mark_feature_verified(self, feature_id: str) -> bool:
        """Mark a feature as verified (all tests pass). Returns False if tests fail."""
        data = self.load_features()

        for feature in data["features"]:
            if feature["id"] == feature_id:
                # Check all tests pass
                all_passed = all(test.get("passed", False) for test in feature["tests"])
                if not all_passed:
                    return False

                feature["verified"] = True
                break

        self.save_features(data)
        return True

    def mark_feature_committed(self, feature_id: str, commit_hash: str) -> None:
        """Mark a feature as committed with git hash."""
        data = self.load_features()

        for feature in data["features"]:
            if feature["id"] == feature_id:
                feature["committed"] = True
                feature["commit_hash"] = commit_hash
                feature["completed_at"] = self._timestamp()
                data["metadata"]["last_feature_completed"] = feature_id
                data["metadata"]["completed_features"] = sum(
                    1 for f in data["features"] if f.get("committed", False)
                )
                data["metadata"]["completion_percentage"] = round(
                    data["metadata"]["completed_features"] / data["metadata"]["total_features"] * 100, 1
                )
                break

        self.save_features(data)

    def update_progress_md(self) -> None:
        """Regenerate progress.md from current state."""
        data = self.load_features()
        status = self.get_status()

        # Create progress bar
        filled = int(status["percentage"] / 100 * 16)
        progress_bar = "[" + "█" * filled + "░" * (16 - filled) + "]"

        # Build completed list
        completed_lines = []
        for f in status["completed_features"]:
            tests_passed = sum(1 for t in f["tests"] if t.get("passed", False))
            completed_lines.append(
                f"- [x] **{f['name']}** ({f.get('commit_hash', 'N/A')[:7]})\n"
                f"  - Tests: {tests_passed}/{len(f['tests'])} passed\n"
                f"  - Completed: {f.get('completed_at', 'Unknown')}"
            )

        # Build in progress list
        in_progress_lines = []
        for f in status["in_progress_features"]:
            tests_passed = sum(1 for t in f["tests"] if t.get("passed", False))
            in_progress_lines.append(
                f"- [ ] **{f['name']}**\n"
                f"  - Tests: {tests_passed}/{len(f['tests'])} passing\n"
                f"  - Status: Implementing"
            )

        # Build pending list
        pending_lines = []
        for f in status["pending_features"]:
            deps = ", ".join(f.get("dependencies", [])) or "None"
            pending_lines.append(
                f"- [ ] **{f['name']}** (Priority: {f.get('priority', 5)})\n"
                f"  - Dependencies: {deps}"
            )

        # Get git log
        git_log = self._get_git_log()

        # Next feature
        next_feature = status["next_feature"]
        next_name = next_feature["name"] if next_feature else "All features complete!"

        progress_content = f"""# {data['project']} - Development Progress

> Auto-updated after each implementation run. Do not edit manually.

## Quick Status

| Metric | Value |
|--------|-------|
| Total Features | {status['total']} |
| Completed | {status['completed']} |
| In Progress | {status['in_progress']} |
| Remaining | {status['pending']} |
| Progress | {progress_bar} {status['percentage']}% |

## Current Session

**Started**: {data.get('created', 'Unknown')}
**Last Update**: {self._timestamp()}
**Current Feature**: {next_name}

## Feature Status

### Completed

{chr(10).join(completed_lines) if completed_lines else '*No features completed yet*'}

### In Progress

{chr(10).join(in_progress_lines) if in_progress_lines else '*No features in progress*'}

### Pending

{chr(10).join(pending_lines) if pending_lines else '*All features complete!*'}

## Recent Git Commits

```
{git_log}
```

## Next Steps

1. {'Implement: ' + next_name if next_feature else 'Project complete!'}
2. Test all feature functionality
3. Commit after verification

---

*Generated by Incremental Development Workflow*
*Reference: features.json for full test details*
"""

        with open(self.progress_path, "w") as f:
            f.write(progress_content)

    def commit_feature(self, feature_id: str, feature_name: str) -> str:
        """Commit the current feature and return commit hash."""
        # Get test summary
        data = self.load_features()
        feature = next((f for f in data["features"] if f["id"] == feature_id), None)

        if not feature:
            raise ValueError(f"Feature {feature_id} not found")

        tests_passed = sum(1 for t in feature["tests"] if t.get("passed", False))
        tests_total = len(feature["tests"])

        # Stage all changes
        subprocess.run(["git", "add", "-A"], cwd=self.project_path, check=True)

        # Create commit message
        commit_msg = f"""feat({feature_id}): {feature_name}

- Implemented {feature.get('description', feature_name)}
- Tests: {tests_passed}/{tests_total} passing
- Verified: All tests pass

Incremental workflow commit"""

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=self.project_path,
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Git commit failed: {result.stderr}")

        # Get commit hash
        hash_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.project_path,
            capture_output=True,
            text=True,
            check=True
        )

        return hash_result.stdout.strip()

    def _timestamp(self) -> str:
        """Get ISO format timestamp."""
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    def _get_git_log(self, count: int = 10) -> str:
        """Get recent git log."""
        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--oneline"],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            return result.stdout.strip() or "(No commits yet)"
        except Exception:
            return "(Git not available)"


def print_status(project_path: str = ".") -> None:
    """Print current workflow status."""
    manager = IncrementalManager(project_path)
    status = manager.get_status()

    print(f"\n{'='*50}")
    print(f"Project: {status['project']}")
    print(f"{'='*50}")

    # Progress bar
    filled = int(status["percentage"] / 100 * 20)
    bar = "[" + "█" * filled + "░" * (20 - filled) + "]"
    print(f"\nProgress: {bar} {status['percentage']}%")
    print(f"Features: {status['completed']}/{status['total']} completed")

    if status["in_progress_features"]:
        print(f"\nIn Progress:")
        for f in status["in_progress_features"]:
            print(f"  - {f['name']}")

    if status["next_feature"]:
        print(f"\nNext Feature: {status['next_feature']['name']}")
    else:
        print("\nAll features complete!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        print_status(sys.argv[1])
    else:
        print_status()
