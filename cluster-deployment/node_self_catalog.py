#!/usr/bin/env python3
"""
Node Self-Cataloging System
============================

Each node catalogs its own Claude Code configuration and shares it with the cluster.

Configuration includes:
- Hooks (SessionStart, SessionEnd, PreToolUse, PostToolUse)
- Agents (custom agent definitions)
- Skills (custom skill definitions)
- Commands (custom slash commands)
- MCP servers (active and configured servers)
- Permissions (allowed/denied tools)
- Status line configuration
- Node-specific customizations
"""

import json
import os
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import platform

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()


# Platform-aware paths
if platform.system() == "Darwin":
    STORAGE_BASE = str(_STORAGE_BASE)
    CLAUDE_HOME = Path.home() / ".claude"
else:
    STORAGE_BASE = str(_STORAGE_BASE)
    CLAUDE_HOME = Path.home() / ".claude"

DB_PATH = Path(STORAGE_BASE) / "databases" / "cluster" / "node_registry.db"


class NodeSelfCatalog:
    """Catalog this node's Claude Code configuration"""

    def __init__(self):
        self.node_id = self._get_node_id()
        self.catalog = {
            "node_id": self.node_id,
            "timestamp": datetime.now().isoformat(),
            "platform": platform.system(),
            "hostname": platform.node(),
            "configuration": {}
        }

    def _get_node_id(self) -> str:
        """Get current node ID from registry"""
        try:
            config_file = CLAUDE_HOME / "node-config.json"
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)
                    return config.get("node_id", platform.node())
        except Exception as e:
            print(f"Warning: Could not read node-config.json: {e}")

        # Fallback to hostname
        return platform.node()

    def catalog_hooks(self) -> Dict[str, Any]:
        """Catalog all hooks"""
        hooks = {
            "session_start": [],
            "session_end": [],
            "pre_tool_use": [],
            "post_tool_use": [],
            "helper_modules": []
        }

        # Read settings.json for hook configuration
        settings_file = CLAUDE_HOME / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    settings = json.load(f)
                    hook_config = settings.get("hooks", {})

                    # Extract hook paths
                    for hook_name, hook_list in hook_config.items():
                        if hook_name == "SessionStart":
                            for hook_group in hook_list:
                                for hook in hook_group.get("hooks", []):
                                    hooks["session_start"].append(hook.get("command", ""))
                        elif hook_name == "SessionEnd":
                            for hook_group in hook_list:
                                for hook in hook_group.get("hooks", []):
                                    hooks["session_end"].append(hook.get("command", ""))
                        elif hook_name == "PreToolUse":
                            for hook_group in hook_list:
                                for hook in hook_group.get("hooks", []):
                                    hooks["pre_tool_use"].append(hook.get("command", ""))
                        elif hook_name == "PostToolUse":
                            for hook_group in hook_list:
                                for hook in hook_group.get("hooks", []):
                                    hooks["post_tool_use"].append(hook.get("command", ""))
            except Exception as e:
                print(f"Error reading hooks: {e}")

        # List helper modules
        hooks_dir = CLAUDE_HOME / "hooks"
        if hooks_dir.exists():
            helper_files = list(hooks_dir.glob("*.py"))
            hooks["helper_modules"] = [f.name for f in helper_files if f.name not in
                                       ["pre-tool-use.py", "post-tool-use.py", "session-start.py", "session-end.py"]]
            hooks["total_helper_modules"] = len(hooks["helper_modules"])

        return hooks

    def catalog_agents(self) -> Dict[str, Any]:
        """Catalog all custom agents"""
        agents_dir = CLAUDE_HOME / "agents"
        agents = {
            "count": 0,
            "agents": []
        }

        if agents_dir.exists():
            agent_files = list(agents_dir.glob("*.md"))
            agents["count"] = len(agent_files)
            agents["agents"] = [f.stem for f in agent_files]

        return agents

    def catalog_skills(self) -> Dict[str, Any]:
        """Catalog all custom skills"""
        skills_dir = CLAUDE_HOME / "skills"
        skills = {
            "count": 0,
            "skills": []
        }

        if skills_dir.exists():
            skill_files = list(skills_dir.glob("*.md"))
            skills["count"] = len(skill_files)
            skills["skills"] = [f.stem for f in skill_files]

        return skills

    def catalog_commands(self) -> Dict[str, Any]:
        """Catalog all custom slash commands"""
        commands_dir = CLAUDE_HOME / "commands"
        commands = {
            "count": 0,
            "commands": []
        }

        if commands_dir.exists():
            command_files = list(commands_dir.glob("*.md"))
            commands["count"] = len(command_files)
            commands["commands"] = [f.stem for f in command_files]

        return commands

    def catalog_mcp_servers(self) -> Dict[str, Any]:
        """Catalog MCP server configuration"""
        mcp_config = {
            "user_level": [],
            "project_level": [],
            "total": 0
        }

        # User-level MCP servers
        user_mcp = CLAUDE_HOME / ".claude.json"
        if user_mcp.exists():
            try:
                with open(user_mcp) as f:
                    config = json.load(f)
                    servers = config.get("mcpServers", {})
                    mcp_config["user_level"] = list(servers.keys())
            except Exception as e:
                print(f"Error reading user MCP config: {e}")

        # Project-level MCP servers
        project_mcp = Path.home() / ".mcp.json"
        if project_mcp.exists():
            try:
                with open(project_mcp) as f:
                    config = json.load(f)
                    servers = config.get("mcpServers", {})
                    mcp_config["project_level"] = list(servers.keys())
            except Exception as e:
                print(f"Error reading project MCP config: {e}")

        mcp_config["total"] = len(mcp_config["user_level"]) + len(mcp_config["project_level"])
        return mcp_config

    def catalog_permissions(self) -> Dict[str, Any]:
        """Catalog tool permissions"""
        permissions = {
            "allow": [],
            "deny": []
        }

        settings_file = CLAUDE_HOME / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    settings = json.load(f)
                    perms = settings.get("permissions", {})
                    permissions["allow"] = perms.get("allow", [])
                    permissions["deny"] = perms.get("deny", [])
            except Exception as e:
                print(f"Error reading permissions: {e}")

        return permissions

    def catalog_status_line(self) -> Dict[str, Any]:
        """Catalog status line configuration"""
        status_line = {
            "enabled": False,
            "command": None,
            "padding": 0
        }

        settings_file = CLAUDE_HOME / "settings.json"
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    settings = json.load(f)
                    sl = settings.get("statusLine", {})
                    status_line["enabled"] = sl.get("type") == "command"
                    status_line["command"] = sl.get("command")
                    status_line["padding"] = sl.get("padding", 0)
            except Exception as e:
                print(f"Error reading status line: {e}")

        return status_line

    def generate_full_catalog(self) -> Dict[str, Any]:
        """Generate complete configuration catalog"""
        print(f"Cataloging node: {self.node_id}")

        self.catalog["configuration"] = {
            "hooks": self.catalog_hooks(),
            "agents": self.catalog_agents(),
            "skills": self.catalog_skills(),
            "commands": self.catalog_commands(),
            "mcp_servers": self.catalog_mcp_servers(),
            "permissions": self.catalog_permissions(),
            "status_line": self.catalog_status_line()
        }

        return self.catalog

    def save_to_database(self, catalog: Dict[str, Any]):
        """Save catalog to cluster database"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create configuration catalog table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_configurations (
                node_id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                platform TEXT,
                hostname TEXT,
                hooks_json TEXT,
                agents_json TEXT,
                skills_json TEXT,
                commands_json TEXT,
                mcp_servers_json TEXT,
                permissions_json TEXT,
                status_line_json TEXT,
                full_catalog_json TEXT,
                updated_at TEXT NOT NULL
            )
        """)

        config = catalog["configuration"]

        # Upsert configuration
        cursor.execute("""
            INSERT OR REPLACE INTO node_configurations
            (node_id, timestamp, platform, hostname, hooks_json, agents_json,
             skills_json, commands_json, mcp_servers_json, permissions_json,
             status_line_json, full_catalog_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            catalog["node_id"],
            catalog["timestamp"],
            catalog["platform"],
            catalog["hostname"],
            json.dumps(config["hooks"]),
            json.dumps(config["agents"]),
            json.dumps(config["skills"]),
            json.dumps(config["commands"]),
            json.dumps(config["mcp_servers"]),
            json.dumps(config["permissions"]),
            json.dumps(config["status_line"]),
            json.dumps(catalog),
            datetime.now().isoformat()
        ))

        conn.commit()
        conn.close()

        print(f"✓ Configuration saved to database for {catalog['node_id']}")

    def run(self) -> Dict[str, Any]:
        """Run complete cataloging process"""
        catalog = self.generate_full_catalog()
        self.save_to_database(catalog)
        return catalog


def main():
    """Main entry point"""
    cataloger = NodeSelfCatalog()
    catalog = cataloger.run()

    print("\n" + "="*80)
    print("NODE CONFIGURATION CATALOG")
    print("="*80)
    print(f"Node: {catalog['node_id']}")
    print(f"Platform: {catalog['platform']}")
    print(f"Timestamp: {catalog['timestamp']}")
    print("\nConfiguration Summary:")
    print(f"  Hooks: {len(catalog['configuration']['hooks']['session_start']) + len(catalog['configuration']['hooks']['session_end']) + len(catalog['configuration']['hooks']['pre_tool_use']) + len(catalog['configuration']['hooks']['post_tool_use'])} main hooks, {catalog['configuration']['hooks'].get('total_helper_modules', 0)} helper modules")
    print(f"  Agents: {catalog['configuration']['agents']['count']}")
    print(f"  Skills: {catalog['configuration']['skills']['count']}")
    print(f"  Commands: {catalog['configuration']['commands']['count']}")
    print(f"  MCP Servers: {catalog['configuration']['mcp_servers']['total']}")
    print(f"  Permissions: {len(catalog['configuration']['permissions']['allow'])} allowed, {len(catalog['configuration']['permissions']['deny'])} denied")
    print(f"  Status Line: {'Enabled' if catalog['configuration']['status_line']['enabled'] else 'Disabled'}")
    print("="*80)

    # Save to JSON file for easy sharing
    output_file = Path(STORAGE_BASE) / "cluster-deployment" / f"config_{catalog['node_id']}.json"
    with open(output_file, 'w') as f:
        json.dump(catalog, f, indent=2)
    print(f"\n✓ Configuration also saved to: {output_file}")


if __name__ == "__main__":
    main()
