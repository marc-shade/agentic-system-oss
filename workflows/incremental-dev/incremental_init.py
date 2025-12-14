#!/usr/bin/env python3
"""
Incremental Development Workflow Initializer

Creates the necessary files and structure for the incremental development workflow
based on Anthropic's agent workflow research.

Usage:
    python incremental_init.py <project_path> --name "Project Name" --description "Description"
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_timestamp() -> str:
    """Get ISO format timestamp."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def detect_tech_stack(project_path: Path) -> dict:
    """Detect the technology stack from project files."""
    stack = {
        "type": "unknown",
        "test_runner": "custom",
        "browser_testing": False,
        "framework": None
    }

    # Check for package.json (Node.js)
    if (project_path / "package.json").exists():
        try:
            with open(project_path / "package.json") as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

                # Detect framework
                if "next" in deps:
                    stack["framework"] = "next"
                    stack["type"] = "nextjs"
                elif "react" in deps:
                    stack["framework"] = "react"
                    stack["type"] = "react"
                elif "vue" in deps:
                    stack["framework"] = "vue"
                    stack["type"] = "vue"
                else:
                    stack["type"] = "node"

                # Detect test runner
                if "vitest" in deps:
                    stack["test_runner"] = "vitest"
                elif "jest" in deps:
                    stack["test_runner"] = "jest"
                elif "mocha" in deps:
                    stack["test_runner"] = "mocha"

                # Detect browser testing
                if "puppeteer" in deps or "playwright" in deps:
                    stack["browser_testing"] = True

        except json.JSONDecodeError:
            pass

    # Check for Python
    elif (project_path / "requirements.txt").exists() or (project_path / "pyproject.toml").exists():
        stack["type"] = "python"
        stack["test_runner"] = "pytest"

        # Check for FastAPI/Flask
        for req_file in ["requirements.txt", "pyproject.toml"]:
            if (project_path / req_file).exists():
                with open(project_path / req_file) as f:
                    content = f.read().lower()
                    if "fastapi" in content:
                        stack["framework"] = "fastapi"
                    elif "flask" in content:
                        stack["framework"] = "flask"
                    elif "django" in content:
                        stack["framework"] = "django"

    return stack


def create_features_json(
    project_path: Path,
    project_name: str,
    description: str,
    features: list[dict],
    config: dict
) -> None:
    """Create the features.json file."""
    timestamp = get_timestamp()

    features_data = {
        "project": project_name,
        "description": description,
        "created": timestamp,
        "version": "1.0.0",
        "config": {
            "test_runner": config.get("test_runner", "custom"),
            "browser_testing": config.get("browser_testing", False),
            "auto_commit": True,
            "require_tests": True
        },
        "features": features,
        "metadata": {
            "total_features": len(features),
            "completed_features": 0,
            "completion_percentage": 0,
            "last_updated": timestamp,
            "last_feature_completed": None
        }
    }

    with open(project_path / "features.json", "w") as f:
        json.dump(features_data, f, indent=2)

    print(f"Created features.json with {len(features)} features")


def create_progress_md(project_path: Path, project_name: str, features: list[dict]) -> None:
    """Create the progress.md tracking file."""
    timestamp = get_timestamp()

    pending_list = "\n".join([
        f"- [ ] **{f['name']}** (Priority: {f.get('priority', 5)})"
        for f in features
    ])

    progress_content = f"""# {project_name} - Development Progress

> Auto-updated after each implementation run. Do not edit manually.

## Quick Status

| Metric | Value |
|--------|-------|
| Total Features | {len(features)} |
| Completed | 0 |
| In Progress | 0 |
| Remaining | {len(features)} |
| Progress | [░░░░░░░░░░░░░░░░] 0% |

## Current Session

**Started**: {timestamp}
**Last Update**: {timestamp}
**Current Feature**: None - Ready to start

## Feature Status

### Completed

*No features completed yet*

### In Progress

*No features in progress*

### Pending

{pending_list}

## Recent Activity

- `{timestamp}` - Initialized incremental development workflow

## Git Commits

```
(No commits yet for this workflow)
```

## Next Steps

1. Run `/incremental-next` to start first feature
2. Test each feature before marking complete
3. Commit after each verified feature

---

*Generated by Incremental Development Workflow*
*Reference: features.json for full test details*
"""

    with open(project_path / "progress.md", "w") as f:
        f.write(progress_content)

    print("Created progress.md")


def create_incremental_config(project_path: Path, config: dict) -> None:
    """Create the .incremental config directory."""
    incremental_dir = project_path / ".incremental"
    incremental_dir.mkdir(exist_ok=True)

    config_data = {
        "version": "1.0.0",
        "initialized": get_timestamp(),
        "config": config,
        "sessions": []
    }

    with open(incremental_dir / "config.json", "w") as f:
        json.dump(config_data, f, indent=2)

    print("Created .incremental/config.json")


def update_claude_md(project_path: Path) -> None:
    """Add incremental workflow guidelines to CLAUDE.md."""
    claude_md_path = project_path / "CLAUDE.md"

    incremental_section = """

## Incremental Development Workflow

This project uses the incremental development workflow for context-efficient implementation.

### Key Files

- `features.json` - Feature list with tests and completion status
- `progress.md` - Human-readable progress tracking

### Rules

1. **Implement one feature at a time** from features.json
2. **Test each feature** before marking `implemented: true`
3. **Commit after each verified feature** with descriptive message
4. **Update progress.md** after each implementation run
5. **Never modify feature list** beyond marking completion status

### Commands

- `/incremental-next` - Implement next pending feature
- `/incremental-status` - View current progress

### Workflow Cycle

```
1. Read features.json -> Find next unimplemented feature
2. Implement feature
3. Run all tests for feature
4. Update features.json (implemented: true, tests passed)
5. Update progress.md
6. Git commit with feature name
7. Repeat
```

### Recovery

If session ends mid-feature:
- Check `git status` for uncommitted changes
- Check features.json for incomplete state
- Resume from last committed feature

"""

    if claude_md_path.exists():
        with open(claude_md_path, "a") as f:
            f.write(incremental_section)
        print("Updated CLAUDE.md with workflow guidelines")
    else:
        with open(claude_md_path, "w") as f:
            f.write(f"# Project Documentation\n\n{incremental_section}")
        print("Created CLAUDE.md with workflow guidelines")


def create_sample_feature(feature_id: str, name: str, description: str, priority: int, tests: list[dict]) -> dict:
    """Create a feature object."""
    return {
        "id": feature_id,
        "name": name,
        "description": description,
        "priority": priority,
        "dependencies": [],
        "tests": [
            {
                "id": f"{feature_id}-test-{i+1}",
                "description": test["description"],
                "type": test.get("type", "integration"),
                "command": test.get("command"),
                "passed": False
            }
            for i, test in enumerate(tests)
        ],
        "implemented": False,
        "verified": False,
        "committed": False,
        "commit_hash": None,
        "notes": ""
    }


def initialize_workflow(
    project_path: str,
    project_name: str,
    description: str,
    features: Optional[list[dict]] = None
) -> None:
    """Initialize the incremental development workflow."""
    path = Path(project_path).resolve()

    if not path.exists():
        print(f"Error: Project path {path} does not exist")
        sys.exit(1)

    print(f"\nInitializing incremental workflow for: {project_name}")
    print(f"Path: {path}\n")

    # Detect tech stack
    stack = detect_tech_stack(path)
    print(f"Detected stack: {stack['type']}")
    if stack['framework']:
        print(f"Framework: {stack['framework']}")
    print(f"Test runner: {stack['test_runner']}")
    print(f"Browser testing: {stack['browser_testing']}\n")

    # Create default features if none provided
    if not features:
        features = [
            create_sample_feature(
                "core-setup",
                "Project Setup",
                "Initialize project structure and verify dependencies",
                1,
                [
                    {"description": "Dependencies install without errors", "type": "integration"},
                    {"description": "Project runs without errors", "type": "integration"}
                ]
            )
        ]

    # Create all files
    create_features_json(path, project_name, description, features, stack)
    create_progress_md(path, project_name, features)
    create_incremental_config(path, stack)
    update_claude_md(path)

    # Add to gitignore if needed
    gitignore_path = path / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            gitignore = f.read()
        if ".incremental/" not in gitignore:
            with open(gitignore_path, "a") as f:
                f.write("\n# Incremental workflow\n.incremental/\n")

    print("\n" + "="*50)
    print("Incremental workflow initialized!")
    print("="*50)
    print(f"\nFeatures to implement: {len(features)}")
    print(f"First feature: {features[0]['name']}")
    print("\nNext steps:")
    print("1. Review features.json and add more features if needed")
    print("2. Run `/incremental-next` to start implementation")
    print("3. Each feature will be tested and committed separately")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize incremental development workflow")
    parser.add_argument("project_path", help="Path to the project directory")
    parser.add_argument("--name", "-n", required=True, help="Project name")
    parser.add_argument("--description", "-d", default="", help="Project description")

    args = parser.parse_args()

    initialize_workflow(args.project_path, args.name, args.description)
