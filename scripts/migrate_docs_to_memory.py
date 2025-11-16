#!/usr/bin/env python3
"""
Migrate .md documentation files to enhanced-memory system.

This script identifies documentation files, classifies them by type,
stores them in appropriate memory tiers, and removes the .md files
after successful migration.
"""

import sys
import os
from pathlib import Path
import re
from datetime import datetime

# Add enhanced-memory to path
sys.path.insert(0, str(Path.home() / ".claude" / "enhanced_memories"))

# File classification patterns
DOCUMENTATION_PATTERNS = [
    r".*_GUIDE\.md$",
    r".*_ARCHITECTURE\.md$",
    r".*README\.md$",
    r".*SYSTEM\.md$",
]

COMPLETION_PATTERNS = [
    r".*_COMPLETE\.md$",
    r".*_COMPLETE_SUMMARY\.md$",
    r".*_STATUS\.md$",
    r".*_DEPLOYMENT\.md$",
    r".*_SUCCESS\.md$",
]

SESSION_PATTERNS = [
    r".*SESSION_SUMMARY\.md$",
    r".*_SUMMARY\.md$",
    r"session.*\.md$",
]

GUIDE_PATTERNS = [
    r".*QUICKSTART.*\.md$",
    r".*_CHECKLIST\.md$",
    r".*_EXAMPLES\.md$",
    r".*_REFERENCE\.md$",
]

# Paths to exclude
EXCLUDE_PATHS = [
    "voice-cache/whisper.cpp",
    "node_modules",
    ".git",
    "venv",
    "examples",
    "tests",
]


def should_exclude(file_path):
    """Check if file should be excluded from migration."""
    path_str = str(file_path)

    # Exclude third-party paths
    for exclude in EXCLUDE_PATHS:
        if exclude in path_str:
            return True

    # Keep MCP server README files (for GitHub)
    if "mcp-servers" in path_str and file_path.name == "README.md":
        return True

    # Exclude if not in main agentic-system directory
    if not path_str.startswith("/mnt/agentic-system"):
        return True

    return False


def classify_file(file_path):
    """Classify .md file by content and name pattern."""
    name = file_path.name

    # Check patterns
    for pattern in COMPLETION_PATTERNS:
        if re.match(pattern, name):
            return "completion_report"

    for pattern in DOCUMENTATION_PATTERNS:
        if re.match(pattern, name):
            return "documentation"

    for pattern in GUIDE_PATTERNS:
        if re.match(pattern, name):
            return "guide"

    for pattern in SESSION_PATTERNS:
        if re.match(pattern, name):
            return "session_summary"

    return "unknown"


def extract_metadata(content, file_path):
    """Extract metadata from .md file content."""
    metadata = {
        "file_path": str(file_path),
        "file_name": file_path.name,
        "file_size": file_path.stat().st_size,
        "modified_date": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
    }

    # Extract date from content
    date_patterns = [
        r"Date[:\s]+(\d{4}-\d{2}-\d{2})",
        r"Updated[:\s]+(\d{4}-\d{2}-\d{2})",
        r"(\d{4}-\d{2}-\d{2})",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, content)
        if match:
            metadata["content_date"] = match.group(1)
            break

    # Extract status
    if "Status:" in content:
        match = re.search(r"Status[:\s]+([^\n]+)", content)
        if match:
            metadata["status"] = match.group(1).strip()

    # Extract key technologies
    tech_keywords = ["COMPASS", "EMBER", "AGI", "Temporal", "AutoKitteh", "n8n",
                     "Qdrant", "MCP", "Arduino", "GraphRAG"]
    mentioned_tech = [tech for tech in tech_keywords if tech in content]
    if mentioned_tech:
        metadata["technologies"] = mentioned_tech

    return metadata


def get_migration_candidates():
    """Get list of .md files to migrate."""
    base_path = Path("/mnt/agentic-system")
    candidates = []

    for md_file in base_path.rglob("*.md"):
        if should_exclude(md_file):
            continue

        file_type = classify_file(md_file)
        if file_type == "unknown":
            continue  # Skip unclassified files

        candidates.append({
            "path": md_file,
            "type": file_type,
            "priority": get_priority(file_type, md_file)
        })

    # Sort by priority (high to low)
    candidates.sort(key=lambda x: x["priority"], reverse=True)

    return candidates


def get_priority(file_type, file_path):
    """Determine migration priority."""
    name = file_path.name

    # High priority: System documentation and completion reports
    if file_type == "completion_report":
        if any(keyword in name for keyword in ["COMPASS", "EMBER", "AGI", "COMPLETE"]):
            return 10
        return 8

    if file_type == "documentation":
        if any(keyword in name for keyword in ["ARCHITECTURE", "SYSTEM", "GUIDE"]):
            return 9
        return 7

    # Medium priority: Guides and examples
    if file_type == "guide":
        return 6

    # Lower priority: Session summaries
    if file_type == "session_summary":
        return 5

    return 1


def main():
    """Main migration execution."""
    print("=" * 70)
    print("DOCUMENTATION MIGRATION TO ENHANCED-MEMORY")
    print("=" * 70)
    print()

    # Get migration candidates
    candidates = get_migration_candidates()

    print(f"Found {len(candidates)} files to migrate:")
    print()

    # Group by type
    by_type = {}
    for candidate in candidates:
        file_type = candidate["type"]
        if file_type not in by_type:
            by_type[file_type] = []
        by_type[file_type].append(candidate)

    for file_type, files in by_type.items():
        print(f"\n{file_type.upper()}: {len(files)} files")
        for file_info in files[:5]:  # Show first 5
            print(f"  - {file_info['path'].name} (priority: {file_info['priority']})")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")

    print("\n" + "=" * 70)
    print("\nMigration will be executed by memory-ingestion-agent")
    print("Files will be stored in enhanced-memory and deleted after verification")
    print("\nCandidate file list saved to: /tmp/migration_candidates.txt")

    # Save candidate list for agent
    with open("/tmp/migration_candidates.txt", "w") as f:
        for candidate in candidates:
            f.write(f"{candidate['path']}\t{candidate['type']}\t{candidate['priority']}\n")

    print("\nReady to proceed with migration.")


if __name__ == "__main__":
    main()
