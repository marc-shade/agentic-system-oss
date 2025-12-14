#!/usr/bin/env python3
"""
Convert MCP Server Configurations to TOON Format

Converts JSON config files in MCP servers to TOON format for token efficiency.
Focuses on production configs and ignores test data, benchmarks, and artifacts.
"""

import json
import sys
from pathlib import Path
from toon_py import encode

# MCP servers base path
MCP_BASE = Path("/mnt/agentic-system/mcp-servers")

# Config files to convert (relative to mcp-servers directory)
TARGET_CONFIGS = [
    # SAFLA configs
    "SAFLA/config/safla_config_production.json",
    "SAFLA/config/optimized_safla_config.json",
    "SAFLA/config/fly_gpu_config.json",
    "SAFLA/config/mcp_client_config.json",

    # Enhanced Memory MCP configs (documentation/templates only)
    "enhanced-memory-mcp/future_proof_mcp_architecture.json",
    "enhanced-memory-mcp/knowledge_aware_agent_templates.json",
    "enhanced-memory-mcp/knowledge_aware_coordination_workflows.json",
]

# Files to skip (test data, benchmarks, temporary files)
SKIP_PATTERNS = [
    "/data/",
    "/testing/",
    "/tests/",
    "/models/",
    "/deploy_temp/",
    "/node_modules/",
    "/.venv/",
    "benchmark",
    "test_results",
    "validation",
]

def should_skip(filepath: str) -> bool:
    """Check if file should be skipped"""
    filepath_str = str(filepath).lower()
    return any(pattern in filepath_str for pattern in SKIP_PATTERNS)

def convert_to_toon(json_path: Path) -> tuple[bool, str]:
    """Convert a JSON file to TOON format"""
    if not json_path.exists():
        return False, f"File not found: {json_path}"

    if should_skip(json_path):
        return False, f"Skipped (excluded pattern): {json_path.name}"

    try:
        # Load JSON
        with open(json_path, 'r') as f:
            data = json.load(f)

        # Convert to TOON
        toon_output = encode(data)

        # Save TOON file
        toon_path = json_path.with_suffix('.toon')
        with open(toon_path, 'w') as f:
            f.write(toon_output)

        # Calculate savings
        json_size = len(json.dumps(data))
        toon_size = len(toon_output)
        savings = ((json_size - toon_size) / json_size) * 100 if json_size > 0 else 0

        return True, f"✓ {json_path.name} → {toon_path.name} ({savings:.1f}% savings)"

    except Exception as e:
        return False, f"✗ Error converting {json_path.name}: {e}"

def main():
    print("=" * 60)
    print(" MCP Server Config → TOON Conversion")
    print("=" * 60)
    print()

    converted = []
    skipped = []
    errors = []

    for config_rel_path in TARGET_CONFIGS:
        config_path = MCP_BASE / config_rel_path
        success, message = convert_to_toon(config_path)

        print(message)

        if success:
            if "Skipped" in message:
                skipped.append(config_rel_path)
            else:
                converted.append(config_rel_path)
        else:
            errors.append(config_rel_path)

    print()
    print("=" * 60)
    print(f"✓ Converted: {len(converted)} files")
    print(f"⊘ Skipped: {len(skipped)} files")
    print(f"✗ Errors: {len(errors)} files")
    print("=" * 60)

    if converted:
        print()
        print("Converted files:")
        for path in converted:
            print(f"  • {path}")

    return 0 if len(errors) == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
