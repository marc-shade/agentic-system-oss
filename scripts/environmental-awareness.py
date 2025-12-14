#!/usr/bin/env python3
"""
Environmental Awareness - Self-Discovery for Agentic Nodes
Run this BEFORE any installation or configuration changes
"""
import platform

import json
import os
import subprocess
import socket
import psutil
from pathlib import Path
from datetime import datetime

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


def check_running_services():
    """Discover what services are already running"""
    services = {}

    # Check common ports
    ports_to_check = {
        6333: "Qdrant",
        7233: "Temporal gRPC",
        8233: "Temporal UI",
        9980: "AutoKitteh",
        5678: "n8n",
        9700: "Prometheus",
        9900: "Loki",
        9500: "Grafana",
        11434: "Ollama",
        8101: "enhanced-memory-mcp",
        8102: "agent-runtime-mcp",
        8200: "arduino-surface-mcp",
        8300: "ember-mcp"
    }

    for port, service_name in ports_to_check.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        result = sock.connect_ex(('localhost', port))
        services[service_name] = {
            "running": result == 0,
            "port": port
        }
        sock.close()

    return services

def find_databases():
    """Locate existing databases"""
    databases = {}

    # Common database locations
    search_paths = [
        Path.home() / ".qdrant",
        Path.home() / ".temporal",
        Path(str(_STORAGE_BASE / "databases")),
        Path(str(_STORAGE_BASE / "databases")),
        Path.home() / "agentic-system/databases",
        Path.cwd() / "databases"
    ]

    for path in search_paths:
        if path.exists():
            try:
                size_mb = sum(f.stat().st_size for f in path.rglob('*') if f.is_file()) / (1024*1024)
                databases[str(path)] = {
                    "exists": True,
                    "size_mb": round(size_mb, 2),
                    "files": len(list(path.rglob('*')))
                }
            except (PermissionError, OSError):
                databases[str(path)] = {
                    "exists": True,
                    "size_mb": 0,
                    "files": 0,
                    "error": "Permission denied"
                }

    return databases

def check_mcp_configuration():
    """Analyze current MCP server configuration"""
    mcp_config = {}

    # Check user-level config
    user_config = Path.home() / ".claude.json"
    if user_config.exists():
        try:
            with open(user_config) as f:
                config = json.load(f)
                mcp_config["user_level"] = {
                    "exists": True,
                    "servers": list(config.get("mcpServers", {}).keys()),
                    "count": len(config.get("mcpServers", {}))
                }
        except json.JSONDecodeError:
            mcp_config["user_level"] = {
                "exists": True,
                "error": "Invalid JSON"
            }

    # Check project-level config
    project_config = Path.home() / ".mcp.json"
    if project_config.exists():
        try:
            with open(project_config) as f:
                config = json.load(f)
                mcp_config["project_level"] = {
                    "exists": True,
                    "servers": list(config.get("mcpServers", {}).keys()),
                    "count": len(config.get("mcpServers", {}))
                }
        except json.JSONDecodeError:
            mcp_config["project_level"] = {
                "exists": True,
                "error": "Invalid JSON"
            }

    return mcp_config

def check_hooks_and_skills():
    """Check for existing hooks, skills, and agents"""
    claude_dir = Path.home() / ".claude"

    hooks = {}
    if (claude_dir / "hooks").exists():
        hooks = {
            "directory": str(claude_dir / "hooks"),
            "scripts": [f.name for f in (claude_dir / "hooks").iterdir() if f.suffix in ['.py', '.sh']]
        }

    skills = {}
    if (claude_dir / "skills").exists():
        skills = {
            "directory": str(claude_dir / "skills"),
            "files": [f.name for f in (claude_dir / "skills").iterdir() if f.suffix == '.md']
        }

    agents = {}
    if (claude_dir / "agents").exists():
        agents = {
            "directory": str(claude_dir / "agents"),
            "files": [f.name for f in (claude_dir / "agents").iterdir() if f.suffix == '.md']
        }

    commands = {}
    if (claude_dir / "commands").exists():
        commands = {
            "directory": str(claude_dir / "commands"),
            "files": [f.name for f in (claude_dir / "commands").iterdir() if f.suffix == '.md']
        }

    return {"hooks": hooks, "skills": skills, "agents": agents, "commands": commands}

def check_ai_platforms():
    """Check which AI platforms are available"""
    platforms = {}

    # Claude Code
    platforms["claude-code"] = subprocess.run(
        ["which", "claude-code"],
        capture_output=True,
        text=True
    ).returncode == 0

    # Ollama
    platforms["ollama"] = subprocess.run(
        ["which", "ollama"],
        capture_output=True,
        text=True
    ).returncode == 0

    # OpenAI Codex
    platforms["codex"] = subprocess.run(
        ["which", "codex"],
        capture_output=True,
        text=True
    ).returncode == 0

    # Gemini CLI
    platforms["gemini"] = subprocess.run(
        ["which", "gemini"],
        capture_output=True,
        text=True
    ).returncode == 0

    return platforms

def get_system_resources():
    """Get available system resources"""
    return {
        "cpu_count": psutil.cpu_count(),
        "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2),
        "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
        "hostname": socket.gethostname(),
        "platform": os.uname().sysname
    }

def check_git_repos():
    """Check for git repositories"""
    repos = {}

    possible_locations = [
        Path(str(_STORAGE_BASE)),
        Path(str(_STORAGE_BASE)),
        Path.home() / "agentic-system",
        Path.cwd()
    ]

    for location in possible_locations:
        if (location / ".git").exists():
            try:
                original_dir = os.getcwd()
                os.chdir(location)

                branch = subprocess.run(
                    ["git", "branch", "--show-current"],
                    capture_output=True,
                    text=True
                ).stdout.strip()

                status = subprocess.run(
                    ["git", "status", "--porcelain"],
                    capture_output=True,
                    text=True
                ).stdout

                repos[str(location)] = {
                    "branch": branch,
                    "clean": len(status) == 0,
                    "changes": len(status.splitlines()) if status else 0
                }

                os.chdir(original_dir)
            except:
                pass

    return repos

def main():
    print("🔍 Environmental Awareness Check")
    print("=" * 60)
    print()

    awareness = {
        "timestamp": datetime.now().isoformat(),
        "hostname": socket.gethostname(),
        "services": check_running_services(),
        "databases": find_databases(),
        "mcp_config": check_mcp_configuration(),
        "hooks_skills_agents": check_hooks_and_skills(),
        "ai_platforms": check_ai_platforms(),
        "system_resources": get_system_resources(),
        "git_repos": check_git_repos()
    }

    # Save to file
    output_file = Path.home() / ".claude" / "environmental-awareness.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(awareness, f, indent=2)

    print(f"✅ Environmental awareness saved to: {output_file}")
    print()
    print("📊 Summary:")
    print(f"  Running Services: {sum(1 for s in awareness['services'].values() if s['running'])}/{len(awareness['services'])}")
    print(f"  Databases Found: {len(awareness['databases'])}")
    print(f"  MCP Servers: User={awareness['mcp_config'].get('user_level', {}).get('count', 0)}, Project={awareness['mcp_config'].get('project_level', {}).get('count', 0)}")
    print(f"  AI Platforms: {sum(awareness['ai_platforms'].values())}/4")
    print(f"  Git Repos: {len(awareness['git_repos'])}")
    print()
    print("Next step: Review this file, then run onboard-with-claude.sh")

    return awareness

if __name__ == "__main__":
    main()
