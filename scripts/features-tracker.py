#!/usr/bin/env python3
"""
Features Tracker - Incremental Feature Implementation Workflow
Based on Anthropic's two-agent workflow for context-efficient development.

Usage:
    features-tracker.py init <project_name> [--description DESC]
    features-tracker.py add <name> [--desc DESC] [--priority PRIO] [--deps IDS] [--tests STEPS]
    features-tracker.py status
    features-tracker.py next
    features-tracker.py implement <feature_id>
    features-tracker.py test <feature_id>
    features-tracker.py complete <feature_id> [--commit HASH]
    features-tracker.py progress
"""

import json
import os
import sys
import subprocess
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional, List


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent


FEATURES_FILE = "features.json"
PROGRESS_FILE = "progress.md"
TEMPLATE_PATH = _get_storage_base() / "templates/features-workflow/features.template.json"


def load_features() -> dict:
    """Load features.json from current directory."""
    if not Path(FEATURES_FILE).exists():
        print(f"Error: {FEATURES_FILE} not found. Run 'features-tracker.py init' first.")
        sys.exit(1)
    with open(FEATURES_FILE, "r") as f:
        return json.load(f)


def save_features(data: dict):
    """Save features.json with updated timestamp."""
    data["project"]["last_updated"] = datetime.now().isoformat()
    with open(FEATURES_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Updated {FEATURES_FILE}")


def init_project(name: str, description: str = ""):
    """Initialize a new features.json from template."""
    if Path(FEATURES_FILE).exists():
        response = input(f"{FEATURES_FILE} already exists. Overwrite? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            return

    if TEMPLATE_PATH.exists():
        with open(TEMPLATE_PATH, "r") as f:
            data = json.load(f)
    else:
        # Fallback template
        data = {
            "project": {},
            "features": [],
            "guidelines": {
                "workflow": [
                    "1. Pick next unimplemented feature",
                    "2. Implement completely",
                    "3. Run test_steps",
                    "4. Mark implemented/tested only when verified",
                    "5. Git commit with descriptive message"
                ],
                "rules": [
                    "NEVER mark tested:true without verification",
                    "ALWAYS commit in mergeable state"
                ]
            }
        }

    now = datetime.now().isoformat()
    data["project"] = {
        "name": name,
        "description": description,
        "created": now,
        "last_updated": now
    }
    data["features"] = []  # Start empty, add features via 'add' command

    save_features(data)
    update_progress()
    print(f"Initialized {FEATURES_FILE} for project: {name}")
    print("Next: Add features with 'features-tracker.py add <name>'")


def add_feature(name: str, description: str = "", priority: str = "medium",
                dependencies: List[str] = None, test_steps: List[str] = None):
    """Add a new feature to track."""
    data = load_features()

    # Generate next ID
    existing_ids = [f["id"] for f in data["features"]]
    next_num = 1
    while f"F{next_num:03d}" in existing_ids:
        next_num += 1
    feature_id = f"F{next_num:03d}"

    feature = {
        "id": feature_id,
        "name": name,
        "description": description,
        "priority": priority,
        "dependencies": dependencies or [],
        "test_steps": test_steps or ["Verify feature works as expected"],
        "implemented": False,
        "tested": False,
        "commit_hash": None,
        "notes": ""
    }

    data["features"].append(feature)
    save_features(data)
    update_progress()
    print(f"Added feature {feature_id}: {name}")


def show_status():
    """Show current progress status."""
    data = load_features()
    features = data["features"]

    total = len(features)
    implemented = sum(1 for f in features if f["implemented"])
    tested = sum(1 for f in features if f["tested"])
    complete = sum(1 for f in features if f["implemented"] and f["tested"])

    print(f"\n{'='*50}")
    print(f"Project: {data['project']['name']}")
    print(f"{'='*50}")
    print(f"Total Features: {total}")
    print(f"Implemented:    {implemented}/{total} ({100*implemented//total if total else 0}%)")
    print(f"Tested:         {tested}/{total} ({100*tested//total if total else 0}%)")
    print(f"Complete:       {complete}/{total} ({100*complete//total if total else 0}%)")
    print(f"{'='*50}\n")

    # Show feature list
    print("Features:")
    for f in features:
        impl = "✓" if f["implemented"] else "○"
        test = "✓" if f["tested"] else "○"
        status = "DONE" if f["implemented"] and f["tested"] else "TODO"
        print(f"  [{f['id']}] {impl}{test} {f['name']} [{f['priority']}] - {status}")
    print()


def show_next():
    """Show next feature to implement."""
    data = load_features()

    for f in data["features"]:
        if not f["implemented"]:
            # Check dependencies
            deps_met = True
            for dep_id in f.get("dependencies", []):
                dep = next((x for x in data["features"] if x["id"] == dep_id), None)
                if dep and not (dep["implemented"] and dep["tested"]):
                    deps_met = False
                    break

            if deps_met:
                print(f"\n{'='*50}")
                print(f"NEXT FEATURE: {f['id']} - {f['name']}")
                print(f"{'='*50}")
                print(f"Priority: {f['priority']}")
                print(f"Description: {f['description']}")
                print(f"\nTest Steps:")
                for i, step in enumerate(f.get("test_steps", []), 1):
                    print(f"  {i}. {step}")
                print(f"\nDependencies: {f.get('dependencies', []) or 'None'}")
                print(f"{'='*50}\n")
                return

    print("\nAll features implemented! Run 'status' to see completion.")


def mark_implemented(feature_id: str):
    """Mark a feature as implemented (code complete)."""
    data = load_features()

    for f in data["features"]:
        if f["id"] == feature_id:
            if f["implemented"]:
                print(f"Feature {feature_id} already marked as implemented.")
                return
            f["implemented"] = True
            save_features(data)
            update_progress()
            print(f"Marked {feature_id} as IMPLEMENTED.")
            print(f"Now run test steps and use 'test {feature_id}' when verified.")
            return

    print(f"Feature {feature_id} not found.")


def mark_tested(feature_id: str):
    """Mark a feature as tested (all test_steps verified)."""
    data = load_features()

    for f in data["features"]:
        if f["id"] == feature_id:
            if not f["implemented"]:
                print(f"Error: Feature {feature_id} not yet implemented!")
                return
            if f["tested"]:
                print(f"Feature {feature_id} already marked as tested.")
                return

            # Confirm test steps were run
            print(f"\nTest steps for {feature_id}:")
            for i, step in enumerate(f.get("test_steps", []), 1):
                print(f"  {i}. {step}")
            response = input("\nHave ALL test steps been verified? [y/N]: ")
            if response.lower() != 'y':
                print("Aborted. Run test steps first.")
                return

            f["tested"] = True
            save_features(data)
            update_progress()
            print(f"Marked {feature_id} as TESTED.")
            print(f"Now commit and use 'complete {feature_id} --commit <hash>'")
            return

    print(f"Feature {feature_id} not found.")


def mark_complete(feature_id: str, commit_hash: str = None):
    """Record git commit for completed feature."""
    data = load_features()

    for f in data["features"]:
        if f["id"] == feature_id:
            if not f["implemented"] or not f["tested"]:
                print(f"Error: Feature {feature_id} must be implemented AND tested first!")
                return

            if not commit_hash:
                # Try to get latest commit hash
                try:
                    result = subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0:
                        commit_hash = result.stdout.strip()[:8]
                except Exception:
                    pass

            f["commit_hash"] = commit_hash
            save_features(data)
            update_progress()
            print(f"Feature {feature_id} COMPLETE! Commit: {commit_hash or 'N/A'}")
            return

    print(f"Feature {feature_id} not found.")


def update_progress():
    """Generate/update progress.md from features.json."""
    data = load_features()
    features = data["features"]

    total = len(features)
    complete = sum(1 for f in features if f["implemented"] and f["tested"])

    content = f"""# Progress: {data['project']['name']}

**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Overview

- **Total Features:** {total}
- **Completed:** {complete}/{total} ({100*complete//total if total else 0}%)

## Feature Status

| ID | Feature | Priority | Implemented | Tested | Commit |
|----|---------|----------|-------------|--------|--------|
"""

    for f in features:
        impl = "✅" if f["implemented"] else "⬜"
        test = "✅" if f["tested"] else "⬜"
        commit = f.get("commit_hash", "") or "-"
        content += f"| {f['id']} | {f['name']} | {f['priority']} | {impl} | {test} | {commit} |\n"

    content += """
## Workflow

1. Pick next unimplemented feature (use `features-tracker.py next`)
2. Implement the feature completely
3. Run ALL test steps
4. Mark implemented: `features-tracker.py implement <ID>`
5. Mark tested: `features-tracker.py test <ID>`
6. Git commit with descriptive message
7. Record commit: `features-tracker.py complete <ID>`
8. Repeat

## Guidelines

"""

    for rule in data.get("guidelines", {}).get("rules", []):
        content += f"- {rule}\n"

    with open(PROGRESS_FILE, "w") as f:
        f.write(content)
    print(f"Updated {PROGRESS_FILE}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "init":
        if len(sys.argv) < 3:
            print("Usage: features-tracker.py init <project_name> [--description DESC]")
            return
        name = sys.argv[2]
        desc = ""
        if "--description" in sys.argv or "--desc" in sys.argv:
            try:
                idx = sys.argv.index("--description") if "--description" in sys.argv else sys.argv.index("--desc")
                desc = sys.argv[idx + 1]
            except (ValueError, IndexError):
                pass
        init_project(name, desc)

    elif cmd == "add":
        if len(sys.argv) < 3:
            print("Usage: features-tracker.py add <name> [--desc DESC] [--priority PRIO]")
            return
        name = sys.argv[2]
        desc = ""
        priority = "medium"
        # Parse optional args
        args = sys.argv[3:]
        i = 0
        while i < len(args):
            if args[i] in ("--desc", "--description") and i + 1 < len(args):
                desc = args[i + 1]
                i += 2
            elif args[i] == "--priority" and i + 1 < len(args):
                priority = args[i + 1]
                i += 2
            else:
                i += 1
        add_feature(name, desc, priority)

    elif cmd == "status":
        show_status()

    elif cmd == "next":
        show_next()

    elif cmd == "implement":
        if len(sys.argv) < 3:
            print("Usage: features-tracker.py implement <feature_id>")
            return
        mark_implemented(sys.argv[2].upper())

    elif cmd == "test":
        if len(sys.argv) < 3:
            print("Usage: features-tracker.py test <feature_id>")
            return
        mark_tested(sys.argv[2].upper())

    elif cmd == "complete":
        if len(sys.argv) < 3:
            print("Usage: features-tracker.py complete <feature_id> [--commit HASH]")
            return
        feature_id = sys.argv[2].upper()
        commit = None
        if "--commit" in sys.argv:
            try:
                idx = sys.argv.index("--commit")
                commit = sys.argv[idx + 1]
            except (ValueError, IndexError):
                pass
        mark_complete(feature_id, commit)

    elif cmd == "progress":
        update_progress()
        print(f"Generated {PROGRESS_FILE}")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
