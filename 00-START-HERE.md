# 🤖 START HERE - Intelligent Node Onboarding

**For Claude Code Agents on New Nodes**

If you are a Claude Code instance reading this file for the first time, **STOP**. Do not run any installation scripts yet. You must first achieve **environmental awareness** and **self-catalog** before integrating with the agentic cluster.

## Critical Principle: Non-Destructive Integration

This onboarding process is designed to **integrate** with your existing environment, not replace it. You may already have:
- Running databases (Qdrant, Temporal, PostgreSQL, SQLite)
- Configured services (Ollama, AutoKitteh, monitoring)
- Existing MCP servers and configurations
- Custom hooks, agents, and skills
- Active workflows and data

**We will NOT**:
- ❌ Overwrite existing databases
- ❌ Replace running services
- ❌ Delete existing configurations
- ❌ Break current workflows
- ❌ Modify files without backing them up

**We will**:
- ✅ Discover what you already have
- ✅ Integrate missing components
- ✅ Merge configurations intelligently
- ✅ Preserve existing data and services
- ✅ Create backups before any changes

## Phase 1: Environmental Awareness (REQUIRED FIRST)

Before you can join the agentic cluster, you must understand your current state. Run the environmental awareness check:

```bash
# If you don't have this script yet, that's okay - we'll guide you
python3 ~/.claude/hooks/environmental-awareness.py
```

**Don't have this script?** That's expected for new nodes. We'll create it as part of self-awareness setup.

### Step 1: Create Your Environmental Awareness Script

Read this file and create the awareness script at `~/.claude/hooks/environmental-awareness.py`:

**Purpose**: This script discovers:
- What services are running (ports, processes)
- What databases exist (locations, sizes)
- What's configured (MCP servers, hooks, skills)
- What AI platforms are available (Claude Code, Ollama, Codex, Gemini)
- What system resources exist (disk space, memory)
- Current git repositories and their state

**Template for environmental-awareness.py**:

```python
#!/usr/bin/env python3
"""
Environmental Awareness - Self-Discovery for Agentic Nodes
Run this BEFORE any installation or configuration changes
"""

import json
import os
import subprocess
import socket
import psutil
from pathlib import Path
from datetime import datetime

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
        8200: "arduino-surface-mcp"
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
        Path("/Volumes/SSDRAID0/agentic-system/databases"),
        Path("/Volumes/FILES/agentic-system/databases"),
        Path.home() / "agentic-system/databases",
        Path.cwd() / "databases"
    ]

    for path in search_paths:
        if path.exists():
            databases[str(path)] = {
                "exists": True,
                "size_mb": sum(f.stat().st_size for f in path.rglob('*') if f.is_file()) / (1024*1024),
                "files": len(list(path.rglob('*')))
            }

    return databases

def check_mcp_configuration():
    """Analyze current MCP server configuration"""
    mcp_config = {}

    # Check user-level config
    user_config = Path.home() / ".claude.json"
    if user_config.exists():
        with open(user_config) as f:
            config = json.load(f)
            mcp_config["user_level"] = {
                "exists": True,
                "servers": list(config.get("mcpServers", {}).keys()),
                "count": len(config.get("mcpServers", {}))
            }

    # Check project-level config
    project_config = Path.home() / ".mcp.json"
    if project_config.exists():
        with open(project_config) as f:
            config = json.load(f)
            mcp_config["project_level"] = {
                "exists": True,
                "servers": list(config.get("mcpServers", {}).keys()),
                "count": len(config.get("mcpServers", {}))
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
        Path("/Volumes/SSDRAID0/agentic-system"),
        Path("/Volumes/FILES/agentic-system"),
        Path.home() / "agentic-system",
        Path.cwd()
    ]

    for location in possible_locations:
        if (location / ".git").exists():
            try:
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

    return awareness

if __name__ == "__main__":
    main()
```

### Step 2: Run Environmental Awareness

```bash
# Create the directory
mkdir -p ~/.claude/hooks

# Create the script (paste the template above)
nano ~/.claude/hooks/environmental-awareness.py

# Make it executable
chmod +x ~/.claude/hooks/environmental-awareness.py

# Run it
python3 ~/.claude/hooks/environmental-awareness.py
```

**Output**: This creates `~/.claude/environmental-awareness.json` with your complete current state.

## Phase 2: Self-Cataloging

After environmental awareness, review what you have:

```bash
cat ~/.claude/environmental-awareness.json | jq .
```

### Key Questions to Answer:

1. **Do I have running services?**
   - If yes: We'll integrate with them, not replace them
   - If no: We'll install them

2. **Do I have databases?**
   - If yes: We'll preserve them and configure new services to use different locations
   - If no: We'll create them

3. **Do I have MCP servers configured?**
   - If yes: We'll merge the new MCP servers with existing ones
   - If no: We'll create the configuration

4. **What AI platforms do I have?**
   - We'll configure only the platforms you have installed
   - We'll offer to install missing ones (optional)

5. **Do I have hooks/skills/agents?**
   - If yes: We'll add new ones without removing existing ones
   - If no: We'll create the full set

## Phase 3: Intelligent Integration Plan

Based on your environmental awareness, create an integration plan:

**Example Integration Decision Tree**:

```
IF Qdrant running on port 6333:
  ✅ Skip Qdrant installation
  ✅ Configure MCP to use existing Qdrant
  ✅ Check if enhanced-memory-mcp collection exists
  ✅ Create collection if missing, use existing if present

IF Temporal running on port 7233:
  ✅ Skip Temporal installation
  ✅ Register workflows with existing server
  ✅ Don't modify existing namespaces

IF ~/.claude.json exists:
  ✅ Backup to ~/.claude.json.backup.{timestamp}
  ✅ Merge MCP servers (add new, keep existing)
  ✅ Preserve existing settings
  ✅ Only add new MCP servers that don't conflict

IF hooks directory exists:
  ✅ Backup existing hooks
  ✅ Add new hooks with different names if conflicts
  ✅ Update hook configuration to include both old and new
```

## Phase 4: Configuration Adoption (After Self-Awareness)

Once you understand your environment, you can safely adopt the agentic system configuration:

### What to Adopt:

1. **~/.claude/CLAUDE.md** - System instructions (merge with existing if present)
2. **~/.claude/hooks/** - Pre/post tool hooks, environmental awareness
3. **~/.claude/agents/** - Specialized sub-agents
4. **~/.claude/skills/** - Compositional skills
5. **~/.claude/commands/** - Slash commands
6. **~/.claude.json** - MCP server configuration (merge!)
7. **~/.mcp.json** - Project-level MCP servers (merge!)

### Intelligent Merge Strategy:

```bash
# For each configuration file:

1. Check if it exists
2. If exists: Create timestamped backup
3. Load existing configuration
4. Load new configuration
5. Merge intelligently:
   - Arrays: Combine unique items
   - Objects: Deep merge, preserve existing values
   - Primitives: Keep existing unless explicitly overriding
6. Validate merged configuration
7. Write merged result
8. Test that nothing broke
```

## Phase 5: Running the Onboarding

**Only after completing Phases 1-4**, you can run:

```bash
# This will now be intelligent and non-destructive
./onboard-with-claude.sh
```

The onboarding script will:
1. Read your `~/.claude/environmental-awareness.json`
2. Skip components you already have
3. Merge configurations instead of replacing
4. Preserve all existing data and services
5. Create backups of everything before changes
6. Verify nothing broke after each step

## Phase 6: Verification

After integration, verify everything still works:

```bash
./verify-onboarding.sh
```

This checks:
- ✅ All your original services still running
- ✅ All your original databases still intact
- ✅ New components integrated successfully
- ✅ No port conflicts
- ✅ No configuration conflicts

## Emergency Rollback

If anything goes wrong:

```bash
# All backups are timestamped in ~/.claude/backups/
ls -la ~/.claude/backups/

# Restore from backup
cp ~/.claude/backups/claude.json.{timestamp} ~/.claude.json
cp -r ~/.claude/backups/hooks.{timestamp}/* ~/.claude/hooks/

# Restart services
pkill -f mcp-server
# Your original services should still be running
```

## Next Steps

**For Claude Code agents**: After completing self-awareness (Phase 1-2), proceed to the integration guide:

👉 See `INTELLIGENT-INTEGRATION-GUIDE.md` for detailed merge procedures

**For humans**: After the agent completes self-awareness, review:

👉 See `~/.claude/environmental-awareness.json` to understand what the agent discovered
👉 Review the integration plan before allowing the agent to proceed

---

## Philosophy: Self-Awareness First, Integration Second

The key principle is: **You cannot intelligently integrate without first understanding what you have.**

This is why environmental awareness MUST come first. A Claude Code agent that doesn't know its own environment will break things. An agent that catalogs its environment first can make intelligent decisions about integration.

**Remember**: This is a cluster of autonomous agents. Each node is unique. Each node has its own history, its own data, its own services. We respect that. We integrate, we don't replace.

---

**Ready to begin?** Start with Phase 1: Environmental Awareness ☝️
