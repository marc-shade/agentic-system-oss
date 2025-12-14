#!/usr/bin/env python3
"""
Systematically fix hardcoded macOS paths in intelligent agent files.
Replaces Path("/Volumes/SSDRAID0/agentic-system/...") with imports from storage_path_utils.py
"""

import os
import platform
import re
from pathlib import Path


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

# Files to fix
FILES_TO_FIX = [
    "agent_auto_selector.py",
    "arduino_status_rotation.py",
    "auto_implementation_engine.py",
    "autonomous_improvement_daemon.py",
    "capability_monitor.py",
    "context_synthesis_engine.py",
    "darwin_godel_machine.py",
    "goal_decomposition_ai.py",
    "knowledge_synthesis_engine.py",
    "llm_detection_integration.py",
    "performance_regression_tracker.py",
    "proactive_memory_loader.py",
    "quality_gates.py",
    "rag_code_generator.py",
    "skill_evolution_system.py",
    "symbolic_regression_manager.py",
    "test_integrated_system.py",
    "verified_improvement_executor.py",
]

BASE_DIR = _STORAGE_BASE / "intelligent-agents"

# Pattern to match hardcoded paths
PATTERN = r'Path\(["\']\/Volumes\/SSDRAID0\/agentic-system\/([^"\']+)["\']\)'


def fix_file(filepath: Path) -> tuple[bool, str]:
    """Fix hardcoded paths in a single file"""
    try:
        content = filepath.read_text()
        original = content

        # Check if already imports storage_path_utils
        has_import = 'from storage_path_utils import' in content or 'import storage_path_utils' in content

        # Find all hardcoded paths
        matches = list(re.finditer(PATTERN, content))

        if not matches:
            return False, "No hardcoded paths found"

        # Add import if needed
        if not has_import:
            # Find first import line
            import_match = re.search(r'^(from|import) ', content, re.MULTILINE)
            if import_match:
                insert_pos = content.find('\n', import_match.start()) + 1
                content = (content[:insert_pos] +
                          "from storage_path_utils import get_database_path, get_logs_path, STORAGE_BASE\n" +
                          content[insert_pos:])

        # Replace database paths
        content = re.sub(
            r'Path\(["\']\/Volumes\/SSDRAID0\/agentic-system\/databases\/([^"\']+)["\']\)',
            r'get_database_path("\1")',
            content
        )

        # Replace log paths
        content = re.sub(
            r'Path\(["\']\/Volumes\/SSDRAID0\/agentic-system\/logs\/([^"\']+)["\']\)',
            r'get_logs_path("\1")',
            content
        )

        # Replace generic paths
        content = re.sub(
            r'Path\(["\']\/Volumes\/SSDRAID0\/agentic-system["\']\)',
            r'STORAGE_BASE',
            content
        )

        # Write back if changed
        if content != original:
            filepath.write_text(content)
            return True, f"Fixed {len(matches)} path(s)"
        else:
            return False, "No changes needed"

    except Exception as e:
        return False, f"Error: {e}"


def main():
    print("Fixing hardcoded paths in intelligent agent files...")
    print("=" * 60)

    fixed_count = 0
    for filename in FILES_TO_FIX:
        filepath = BASE_DIR / filename
        if not filepath.exists():
            print(f"✗ {filename}: File not found")
            continue

        changed, message = fix_file(filepath)
        status = "✓" if changed else "○"
        print(f"{status} {filename}: {message}")
        if changed:
            fixed_count += 1

    print("=" * 60)
    print(f"Fixed {fixed_count} file(s)")


if __name__ == "__main__":
    main()
