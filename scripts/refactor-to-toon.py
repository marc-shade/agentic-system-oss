#!/usr/bin/env python3
"""
Batch Refactor JSON to TOON

Automatically refactors Python files to use TOON configuration format
"""

import os
import platform
import re
import sys
from pathlib import Path
from typing import List, Tuple


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

# Files that reference node-config.json (relative to storage base)
_FILES_TO_UPDATE_RELATIVE = [
    "cluster-deployment/add_node.py",
    "cluster-deployment/coordinate-deployment.py",
    "cluster-deployment/test_cluster_memory.py",
    "scripts/cluster-memory-sync.py",
    "scripts/node-registry-service.py",
    "cluster-node-api.py",
]

# Build full paths dynamically
FILES_TO_UPDATE = [str(STORAGE_BASE / f) for f in _FILES_TO_UPDATE_RELATIVE]

def add_toon_import(content: str) -> str:
    """Add TOON config import if not present"""
    if 'from toon_config import' in content:
        return content  # Already has import

    # Find import section
    lines = content.split('\n')
    last_import_idx = 0

    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            last_import_idx = i

    # Add toon_config import with platform-aware path
    insert_lines = [
        'import os',
        'import platform',
        'import sys',
        'from pathlib import Path',
        '',
        '# Auto-detect storage base for toon_config',
        'def _get_storage_base():',
        '    env = os.environ.get("AGENTIC_SYSTEM_PATH")',
        '    if env and Path(env).exists(): return Path(env)',
        '    if platform.system() == "Darwin":',
        '        for p in ["/Volumes/SSDRAID0/agentic-system", "/Volumes/FILES/agentic-system"]:',
        '            if Path(p).exists(): return Path(p)',
        '    else:',
        '        for p in ["/home/marc/agentic-system", "/mnt/agentic-system"]:',
        '            if Path(p).exists(): return Path(p)',
        '    return Path(__file__).parent.parent',
        '',
        'sys.path.insert(0, str(_get_storage_base() / "cluster-deployment"))',
        'from toon_config import load_config',
        ''
    ]

    # Insert after last import
    lines[last_import_idx + 1:last_import_idx + 1] = insert_lines
    return '\n'.join(lines)


def replace_json_load(content: str) -> str:
    """Replace json.load() calls with load_config()"""

    patterns = [
        # Pattern 1: with open(...) as f: config = json.load(f)
        (
            r'with open\(([^)]+node-config\.json[^)]*)\) as f:\s*(\w+) = json\.load\(f\)',
            r'\2 = load_config(\1.replace(".json", ""))'
        ),
        # Pattern 2: f = open(...); config = json.load(f)
        (
            r'(\w+) = open\(([^)]+node-config\.json[^)]*)\)[\s\n]+(\w+) = json\.load\(\1\)',
            r'\3 = load_config(\2.replace(".json", ""))'
        ),
        # Pattern 3: json.load(open(...))
        (
            r'json\.load\(open\(([^)]+node-config\.json[^)]*)\)\)',
            r'load_config(\1.replace(".json", ""))'
        ),
    ]

    result = content
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.MULTILINE)

    return result


def refactor_file(filepath: str) -> Tuple[bool, str]:
    """Refactor a single file"""
    path = Path(filepath)

    if not path.exists():
        return False, f"File not found: {filepath}"

    try:
        # Read original content
        with open(path, 'r') as f:
            original = f.read()

        # Apply refactorings
        content = original
        content = add_toon_import(content)
        content = replace_json_load(content)

        if content == original:
            return True, f"No changes needed: {filepath}"

        # Backup original
        backup_path = path.with_suffix(path.suffix + '.json-backup')
        with open(backup_path, 'w') as f:
            f.write(original)

        # Write refactored version
        with open(path, 'w') as f:
            f.write(content)

        return True, f"✓ Refactored: {filepath} (backup: {backup_path})"

    except Exception as e:
        return False, f"✗ Error refactoring {filepath}: {e}"


def main():
    print("=" * 60)
    print(" JSON to TOON Refactoring")
    print("=" * 60)
    print()

    success_count = 0
    fail_count = 0

    for filepath in FILES_TO_UPDATE:
        success, message = refactor_file(filepath)
        print(message)

        if success:
            success_count += 1
        else:
            fail_count += 1

    print()
    print("=" * 60)
    print(f"✓ Success: {success_count}")
    print(f"✗ Failed: {fail_count}")
    print("=" * 60)

    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
