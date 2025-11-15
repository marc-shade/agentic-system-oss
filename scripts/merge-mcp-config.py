#!/usr/bin/env python3
"""
Intelligent MCP Configuration Merger
Combines new MCP servers with existing ones without conflicts
"""

import json
from pathlib import Path
from datetime import datetime

def load_json(filepath):
    """Load JSON file or return empty dict"""
    path = Path(filepath).expanduser()
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def merge_mcp_servers(existing, new):
    """
    Merge MCP server configurations intelligently

    Rules:
    - Keep all existing servers
    - Add new servers that don't conflict
    - For conflicts, use existing and warn
    - Preserve all existing configuration
    """
    merged = existing.copy()

    # Get existing server names
    existing_servers = set(existing.get("mcpServers", {}).keys())

    # Initialize mcpServers if needed
    if "mcpServers" not in merged:
        merged["mcpServers"] = {}

    # Process each new server
    conflicts = []
    added = []

    for server_name, server_config in new.get("mcpServers", {}).items():
        if server_name in existing_servers:
            # Conflict - keep existing
            conflicts.append(server_name)
        else:
            # No conflict - add it
            merged["mcpServers"][server_name] = server_config
            added.append(server_name)

    # Preserve other top-level keys from existing
    for key in existing:
        if key != "mcpServers":
            if key not in merged:
                merged[key] = existing[key]

    return merged, added, conflicts

def main():
    # Load environmental awareness
    awareness_file = Path.home() / ".claude" / "environmental-awareness.json"
    if not awareness_file.exists():
        print("❌ Environmental awareness not found. Run environmental-awareness.py first!")
        return 1

    with open(awareness_file) as f:
        awareness = json.load(f)

    print("🔄 Intelligent MCP Configuration Merge")
    print("=" * 60)
    print()

    # Determine repository directory from awareness
    repo_dir = Path.cwd()

    # Load existing and new configurations
    existing_user = load_json("~/.claude.json")

    # Try to find the new config template
    new_config_paths = [
        repo_dir / "config-templates" / "claude-code-config.json",
        repo_dir / ".claude.json.template",
    ]

    new_user = {}
    for config_path in new_config_paths:
        if config_path.exists():
            with open(config_path) as f:
                new_user = json.load(f)
            break

    # If no template found, create minimal cluster MCP servers
    if not new_user.get("mcpServers"):
        new_user = {
            "mcpServers": {
                "enhanced-memory-mcp": {
                    "command": "python3",
                    "args": [str(repo_dir / "mcp-servers" / "enhanced-memory-mcp" / "server.py")],
                    "env": {},
                    "disabled": False
                },
                "agent-runtime-mcp": {
                    "command": "python3",
                    "args": [str(repo_dir / "mcp-servers" / "agent-runtime-mcp" / "server.py")],
                    "env": {},
                    "disabled": False
                },
                "ember-mcp": {
                    "command": "python3",
                    "args": [str(repo_dir / "mcp-servers" / "ember-mcp" / "server.py")],
                    "env": {},
                    "disabled": False
                }
            }
        }

    existing_project = load_json("~/.mcp.json")
    new_project = load_json(str(repo_dir / ".mcp.json"))

    # Merge user-level config
    print("📋 User-level configuration (~/.claude.json)")
    merged_user, added_user, conflicts_user = merge_mcp_servers(existing_user, new_user)

    if added_user:
        print(f"  ✅ Adding {len(added_user)} new MCP servers:")
        for server in added_user:
            print(f"     - {server}")

    if conflicts_user:
        print(f"  ⚠️  Skipping {len(conflicts_user)} existing servers (no changes):")
        for server in conflicts_user:
            print(f"     - {server}")

    # Merge project-level config
    print()
    print("📋 Project-level configuration (~/.mcp.json)")
    merged_project, added_project, conflicts_project = merge_mcp_servers(existing_project, new_project)

    if added_project:
        print(f"  ✅ Adding {len(added_project)} new MCP servers:")
        for server in added_project:
            print(f"     - {server}")

    if conflicts_project:
        print(f"  ⚠️  Skipping {len(conflicts_project)} existing servers (no changes):")
        for server in conflicts_project:
            print(f"     - {server}")

    # Write merged configurations
    print()
    print("💾 Saving merged configurations...")

    user_config_path = Path.home() / ".claude.json"
    with open(user_config_path, 'w') as f:
        json.dump(merged_user, f, indent=2)
    print(f"  ✅ Saved: {user_config_path}")

    if merged_project.get("mcpServers"):
        project_config_path = Path.home() / ".mcp.json"
        with open(project_config_path, 'w') as f:
            json.dump(merged_project, f, indent=2)
        print(f"  ✅ Saved: {project_config_path}")

    print()
    print("✅ MCP configuration merge complete!")
    print()
    print("Total servers configured:")
    print(f"  User-level: {len(merged_user.get('mcpServers', {}))}")
    print(f"  Project-level: {len(merged_project.get('mcpServers', {}))}")

    return 0

if __name__ == "__main__":
    exit(main())
