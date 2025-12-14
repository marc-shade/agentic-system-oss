#!/usr/bin/env python3
"""
Batch Fix Hardcoded Paths - Comprehensive Path Fixer
=====================================================

Finds and fixes all hardcoded paths in Python files across the codebase.
Adds platform-aware path detection to ensure cross-platform compatibility.

Usage:
    python3 batch_fix_hardcoded_paths.py --dry-run  # Preview changes
    python3 batch_fix_hardcoded_paths.py            # Apply changes
"""

import os
import platform
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set


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


STORAGE_BASE = _get_storage_base()


# The platform detection function to inject
PLATFORM_DETECTION_FUNCTION = '''
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


_STORAGE_BASE = _get_storage_base()
'''

# Hardcoded path patterns to find
HARDCODED_PATTERNS = [
    r'"/mnt/agentic-system"',
    r'"/home/marc/agentic-system"',
    r'"/Volumes/SSDRAID0/agentic-system"',
    r'"/Volumes/FILES/agentic-system"',
    r"'/mnt/agentic-system'",
    r"'/home/marc/agentic-system'",
    r"'/Volumes/SSDRAID0/agentic-system'",
    r"'/Volumes/FILES/agentic-system'",
]

# Files to skip (already properly fixed or special)
SKIP_FILES = {
    'batch_fix_hardcoded_paths.py',  # This script itself
    'fix_paths.py',  # Old fixer
    'refactor-to-toon.py',  # Already has detection
    'enhanced_conversation_viewer.py',  # Already has detection
    'cluster_brain_dynamic.py',  # Already has detection
    'daemon.py',  # Just fixed
    'detect-storage.sh',  # Shell detection script
}

# Directories to skip
SKIP_DIRS = {
    '.git',
    '__pycache__',
    'node_modules',
    '.venv',
    'venv',
    'coral-venv',
    'backups',
    '.claude',
}


def find_python_files_with_hardcoded_paths(base_path: Path) -> List[Path]:
    """Find all Python files containing hardcoded paths."""
    files_with_issues = []

    for py_file in base_path.rglob("*.py"):
        # Skip certain directories
        if any(skip in py_file.parts for skip in SKIP_DIRS):
            continue

        # Skip certain files
        if py_file.name in SKIP_FILES:
            continue

        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')

            # Check for hardcoded paths
            for pattern in HARDCODED_PATTERNS:
                if re.search(pattern, content):
                    files_with_issues.append(py_file)
                    break
        except Exception as e:
            print(f"  Warning: Could not read {py_file}: {e}")

    return files_with_issues


def has_platform_detection(content: str) -> bool:
    """Check if file already has platform detection."""
    return '_get_storage_base' in content or 'get_storage_base' in content


def has_required_imports(content: str) -> Tuple[bool, bool, bool]:
    """Check for required imports (os, platform, Path)."""
    has_os = bool(re.search(r'^import os\b|^from os ', content, re.MULTILINE))
    has_platform = bool(re.search(r'^import platform\b', content, re.MULTILINE))
    has_path = bool(re.search(r'^from pathlib import.*Path|^import pathlib', content, re.MULTILINE))
    return has_os, has_platform, has_path


def add_missing_imports(content: str, has_os: bool, has_platform: bool, has_path: bool) -> str:
    """Add missing imports at the top of the file."""
    imports_to_add = []

    if not has_os:
        imports_to_add.append('import os')
    if not has_platform:
        imports_to_add.append('import platform')
    if not has_path:
        imports_to_add.append('from pathlib import Path')

    if not imports_to_add:
        return content

    # Find the position after existing imports
    lines = content.split('\n')
    insert_line = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip docstrings, comments, empty lines at the start
        if stripped.startswith('"""') or stripped.startswith("'''"):
            # Skip multi-line docstrings
            if stripped.count('"""') == 1 or stripped.count("'''") == 1:
                for j in range(i + 1, len(lines)):
                    if '"""' in lines[j] or "'''" in lines[j]:
                        insert_line = j + 1
                        break
            continue
        elif stripped.startswith('#') or not stripped:
            continue
        elif stripped.startswith('import ') or stripped.startswith('from '):
            insert_line = i + 1
        elif insert_line > 0:
            break

    # Insert the imports
    for imp in reversed(imports_to_add):
        lines.insert(insert_line, imp)

    return '\n'.join(lines)


def add_platform_detection(content: str) -> str:
    """Add platform detection function after imports."""
    if has_platform_detection(content):
        return content

    # Find the end of imports section
    lines = content.split('\n')
    insert_line = 0
    in_docstring = False

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track docstrings
        if '"""' in stripped or "'''" in stripped:
            count = stripped.count('"""') + stripped.count("'''")
            if count == 1:
                in_docstring = not in_docstring
            continue

        if in_docstring:
            continue

        # Find last import line
        if stripped.startswith('import ') or stripped.startswith('from '):
            insert_line = i + 1

    # Insert the platform detection function after imports
    lines.insert(insert_line, PLATFORM_DETECTION_FUNCTION)

    return '\n'.join(lines)


def replace_hardcoded_paths(content: str) -> str:
    """Replace hardcoded paths with _STORAGE_BASE."""

    # Pattern replacements - handle various string quoting styles
    replacements = [
        # Double-quoted full paths
        (r'"/mnt/agentic-system"', 'str(_STORAGE_BASE)'),
        (r'"/home/marc/agentic-system"', 'str(_STORAGE_BASE)'),
        (r'"/Volumes/SSDRAID0/agentic-system"', 'str(_STORAGE_BASE)'),
        (r'"/Volumes/FILES/agentic-system"', 'str(_STORAGE_BASE)'),
        # Single-quoted full paths
        (r"'/mnt/agentic-system'", 'str(_STORAGE_BASE)'),
        (r"'/home/marc/agentic-system'", 'str(_STORAGE_BASE)'),
        (r"'/Volumes/SSDRAID0/agentic-system'", 'str(_STORAGE_BASE)'),
        (r"'/Volumes/FILES/agentic-system'", 'str(_STORAGE_BASE)'),
        # Path() calls with full paths
        (r'Path\("/mnt/agentic-system"\)', '_STORAGE_BASE'),
        (r'Path\("/home/marc/agentic-system"\)', '_STORAGE_BASE'),
        (r'Path\("/Volumes/SSDRAID0/agentic-system"\)', '_STORAGE_BASE'),
        (r'Path\("/Volumes/FILES/agentic-system"\)', '_STORAGE_BASE'),
        # With subpaths (most common case)
        (r'"/mnt/agentic-system/([^"]+)"', r'str(_STORAGE_BASE / "\1")'),
        (r'"/home/marc/agentic-system/([^"]+)"', r'str(_STORAGE_BASE / "\1")'),
        (r'"/Volumes/SSDRAID0/agentic-system/([^"]+)"', r'str(_STORAGE_BASE / "\1")'),
        (r'"/Volumes/FILES/agentic-system/([^"]+)"', r'str(_STORAGE_BASE / "\1")'),
        # Environment variable with fallback patterns
        (r'os\.environ\.get\("AGENTIC_SYSTEM_PATH",\s*"/mnt/agentic-system"\)', 'str(_STORAGE_BASE)'),
        (r'os\.environ\.get\("AGENTIC_SYSTEM_PATH",\s*"/home/marc/agentic-system"\)', 'str(_STORAGE_BASE)'),
        # Path() with subpaths
        (r'Path\("/mnt/agentic-system/([^"]+)"\)', r'_STORAGE_BASE / "\1"'),
        (r'Path\("/home/marc/agentic-system/([^"]+)"\)', r'_STORAGE_BASE / "\1"'),
        (r'Path\("/Volumes/SSDRAID0/agentic-system/([^"]+)"\)', r'_STORAGE_BASE / "\1"'),
        (r'Path\("/Volumes/FILES/agentic-system/([^"]+)"\)', r'_STORAGE_BASE / "\1"'),
    ]

    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)

    return content


def fix_file(file_path: Path, dry_run: bool = False) -> bool:
    """Fix a single file's hardcoded paths."""
    try:
        original = file_path.read_text(encoding='utf-8')

        # Skip if already has proper detection
        if has_platform_detection(original):
            print(f"  SKIP (already has detection): {file_path.name}")
            return False

        content = original

        # Check and add missing imports
        has_os, has_platform, has_path = has_required_imports(content)
        content = add_missing_imports(content, has_os, has_platform, has_path)

        # Add platform detection function
        content = add_platform_detection(content)

        # Replace hardcoded paths
        content = replace_hardcoded_paths(content)

        # Check if changes were made
        if content == original:
            print(f"  SKIP (no changes): {file_path.name}")
            return False

        if dry_run:
            print(f"  WOULD FIX: {file_path}")
            return True

        # Write the fixed content
        file_path.write_text(content, encoding='utf-8')
        print(f"  FIXED: {file_path}")
        return True

    except Exception as e:
        print(f"  ERROR: {file_path}: {e}")
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fix hardcoded paths in Python files")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print("=" * 60)
    print(" Batch Fix Hardcoded Paths")
    print("=" * 60)
    print(f"\nStorage base: {STORAGE_BASE}")
    print(f"Mode: {'DRY RUN (preview only)' if args.dry_run else 'APPLY CHANGES'}")
    print()

    # Find files with issues
    print("Scanning for Python files with hardcoded paths...")
    files = find_python_files_with_hardcoded_paths(STORAGE_BASE)
    print(f"Found {len(files)} files with hardcoded paths\n")

    if not files:
        print("No files need fixing!")
        return 0

    # Fix each file
    fixed_count = 0
    skipped_count = 0
    error_count = 0

    for file_path in sorted(files):
        result = fix_file(file_path, args.dry_run)
        if result:
            fixed_count += 1
        elif result is False:
            skipped_count += 1
        else:
            error_count += 1

    # Summary
    print()
    print("=" * 60)
    print(" Summary")
    print("=" * 60)
    print(f"  Total files scanned: {len(files)}")
    print(f"  Files {'would be ' if args.dry_run else ''}fixed: {fixed_count}")
    print(f"  Files skipped: {skipped_count}")
    print(f"  Errors: {error_count}")

    if args.dry_run:
        print("\n  Run without --dry-run to apply changes.")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
