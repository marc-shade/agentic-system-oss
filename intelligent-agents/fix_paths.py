#!/usr/bin/env python3
"""
Script to fix hardcoded paths in Python files.
Uses the standard _get_storage_base() pattern.
"""
import os
import platform
import re
import sys
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
    return Path(__file__).parent


_STORAGE_BASE = _get_storage_base()

files_to_fix = [
    "darwin_godel_machine.py",
    "goal_decomposition_ai.py",
    "multi_agent_coordinator.py",
    "skill_evolution_system.py",
    "context_synthesis_engine.py"
]

# Platform check code to inject into files
platform_check = '''# Platform-aware path detection
import os
import platform
from pathlib import Path

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)
    system = platform.system()
    if system == "Darwin":
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent

STORAGE_BASE = str(_get_storage_base())
'''

for filename in files_to_fix:
    with open(filename, 'r') as f:
        content = f.read()
    
    # Add platform check after imports if not present
    if 'STORAGE_BASE' not in content:
        # Find the last import statement
        import_match = list(re.finditer(r'^(import |from .* import)', content, re.MULTILINE))
        if import_match:
            insert_pos = import_match[-1].end()
            # Find the end of that line
            newline_pos = content.find('\n', insert_pos)
            content = content[:newline_pos+1] + '\n' + platform_check + '\n' + content[newline_pos+1:]
    
    # Replace hardcoded /mnt paths
    content = re.sub(
        r'Path\("/mnt/agentic-system([^"]*?)"\)',
        r'Path(STORAGE_BASE + "\1")',
        content
    )
    content = re.sub(
        r'"/mnt/agentic-system([^"]*?)"',
        r'STORAGE_BASE + "\1"',
        content
    )
    
    with open(filename, 'w') as f:
        f.write(content)
    
    print(f"✓ Fixed {filename}")

print("\nDone!")
