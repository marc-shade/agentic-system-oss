# Intelligent Integration Guide

**For Claude Code Agents Performing Non-Destructive Integration**

This guide explains how to merge the agentic system configuration into an existing environment without breaking anything.

## Prerequisites

✅ You must have completed environmental awareness (Phase 1-2 from `00-START-HERE.md`)
✅ You must have `~/.claude/environmental-awareness.json` file
✅ You must understand what's currently running on this node

## Integration Principles

1. **Backup Everything** - Before any change, create timestamped backups
2. **Merge, Don't Replace** - Combine configurations intelligently
3. **Test After Each Step** - Verify nothing broke before proceeding
4. **Preserve Data** - Never delete existing databases or data files
5. **Respect Running Services** - Don't stop or restart existing services
6. **Unique Naming** - Use different names/ports if conflicts exist

## Step-by-Step Integration

### Step 1: Create Backup Infrastructure

```bash
# Create backup directory with timestamp
BACKUP_DIR="$HOME/.claude/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup existing Claude configuration
if [ -f "$HOME/.claude.json" ]; then
    cp "$HOME/.claude.json" "$BACKUP_DIR/claude.json.backup"
fi

if [ -f "$HOME/.mcp.json" ]; then
    cp "$HOME/.mcp.json" "$BACKUP_DIR/mcp.json.backup"
fi

if [ -f "$HOME/.claude/CLAUDE.md" ]; then
    cp "$HOME/.claude/CLAUDE.md" "$BACKUP_DIR/CLAUDE.md.backup"
fi

# Backup hooks, skills, agents, commands
for dir in hooks skills agents commands; do
    if [ -d "$HOME/.claude/$dir" ]; then
        cp -r "$HOME/.claude/$dir" "$BACKUP_DIR/${dir}.backup"
    fi
done

echo "✅ Backups created in $BACKUP_DIR"
```

### Step 2: Intelligent MCP Server Merge

```python
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
        return

    with open(awareness_file) as f:
        awareness = json.load(f)

    print("🔄 Intelligent MCP Configuration Merge")
    print("=" * 60)
    print()

    # Load existing and new configurations
    existing_user = load_json("~/.claude.json")
    new_user = load_json("./config-templates/claude-code-config.json")

    existing_project = load_json("~/.mcp.json")
    new_project = load_json("./.mcp.json")

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

if __name__ == "__main__":
    main()
```

Save this as `scripts/merge-mcp-config.py` and run it:

```bash
python3 scripts/merge-mcp-config.py
```

### Step 3: Intelligent Service Integration

Based on `environmental-awareness.json`, only install missing services:

```python
#!/usr/bin/env python3
"""
Intelligent service integration - only install what's missing
"""

import json
from pathlib import Path

def get_services_to_install():
    """Determine which services need installation"""

    awareness_file = Path.home() / ".claude" / "environmental-awareness.json"
    with open(awareness_file) as f:
        awareness = json.load(f)

    services = awareness.get("services", {})

    install_plan = {
        "Qdrant": not services.get("Qdrant", {}).get("running", False),
        "Temporal": not services.get("Temporal gRPC", {}).get("running", False),
        "AutoKitteh": not services.get("AutoKitteh", {}).get("running", False),
        "Ollama": not services.get("Ollama", {}).get("running", False),
        "Prometheus": not services.get("Prometheus", {}).get("running", False),
        "Loki": not services.get("Loki", {}).get("running", False),
        "Grafana": not services.get("Grafana", {}).get("running", False)
    }

    return install_plan

def main():
    plan = get_services_to_install()

    print("📦 Service Installation Plan")
    print("=" * 60)
    print()

    to_install = [name for name, needed in plan.items() if needed]
    already_running = [name for name, needed in plan.items() if not needed]

    if already_running:
        print("✅ Already Running (will reuse):")
        for service in already_running:
            print(f"   - {service}")
        print()

    if to_install:
        print("📥 Will Install:")
        for service in to_install:
            print(f"   - {service}")
        print()
    else:
        print("✅ All required services are already running!")
        print()

    # Save installation plan
    plan_file = Path.home() / ".claude" / "installation-plan.json"
    with open(plan_file, 'w') as f:
        json.dump(plan, f, indent=2)

    print(f"💾 Installation plan saved to: {plan_file}")

if __name__ == "__main__":
    main()
```

Save as `scripts/plan-installation.py` and run:

```bash
python3 scripts/plan-installation.py
```

### Step 4: Database Integration

For databases, NEVER replace existing data:

```bash
# Check if databases exist
if [ -f ~/.claude/environmental-awareness.json ]; then
    EXISTING_DBS=$(cat ~/.claude/environmental-awareness.json | jq -r '.databases | keys[]')

    for db_path in $EXISTING_DBS; do
        echo "✅ Found existing database: $db_path"
        echo "   Will NOT modify or replace"
        echo "   New services will use this database"
    done
fi

# For new databases, create in non-conflicting locations
# Example: If /Volumes/SSDRAID0/agentic-system/databases exists, use it
# Otherwise, create ~/agentic-system/databases
```

### Step 5: Hooks and Skills Integration

Merge hooks without replacing existing ones:

```bash
# Copy new hooks with conflict detection
for hook_file in ./hooks/*; do
    HOOK_NAME=$(basename "$hook_file")
    TARGET="$HOME/.claude/hooks/$HOOK_NAME"

    if [ -f "$TARGET" ]; then
        # File exists - compare and offer merge
        if diff -q "$hook_file" "$TARGET" > /dev/null; then
            echo "✅ Hook already exists and is identical: $HOOK_NAME"
        else
            # Different - keep both
            TIMESTAMP=$(date +%Y%m%d_%H%M%S)
            cp "$TARGET" "$TARGET.existing.$TIMESTAMP"
            cp "$hook_file" "$TARGET.new.$TIMESTAMP"
            echo "⚠️  Hook conflict: $HOOK_NAME"
            echo "   Saved existing as: $HOOK_NAME.existing.$TIMESTAMP"
            echo "   Saved new as: $HOOK_NAME.new.$TIMESTAMP"
            echo "   Manual merge required"
        fi
    else
        # Doesn't exist - safe to copy
        cp "$hook_file" "$TARGET"
        chmod +x "$TARGET"
        echo "✅ Added new hook: $HOOK_NAME"
    fi
done
```

### Step 6: Port Conflict Resolution

If port conflicts exist, use alternative ports:

```python
def find_alternative_port(preferred_port):
    """Find an available port near the preferred one"""
    import socket

    for offset in range(100):
        test_port = preferred_port + offset
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.1)
        result = sock.connect_ex(('localhost', test_port))
        sock.close()

        if result != 0:  # Port is available
            return test_port

    return None

# Example usage
if qdrant_running_on_6333:
    # Use existing Qdrant
    mcp_config["qdrant_port"] = 6333
else:
    # Install new Qdrant on default port
    mcp_config["qdrant_port"] = 6333
```

### Step 7: Configuration File Merge

For CLAUDE.md and other instruction files:

```python
def merge_instruction_files(existing_path, new_path):
    """
    Merge instruction files intelligently

    Strategy:
    - Keep existing content
    - Add new sections that don't exist
    - Mark conflicts for manual review
    """

    from pathlib import Path

    existing = Path(existing_path).read_text() if Path(existing_path).exists() else ""
    new = Path(new_path).read_text()

    if not existing:
        # No existing file - use new one
        return new

    # Extract sections from both
    existing_sections = extract_markdown_sections(existing)
    new_sections = extract_markdown_sections(new)

    # Merge sections
    merged_sections = existing_sections.copy()

    for section_name, section_content in new_sections.items():
        if section_name not in existing_sections:
            # New section - add it
            merged_sections[section_name] = section_content
        else:
            # Existing section - keep existing, note new version
            merged_sections[section_name + " (New Version - Review)"] = section_content

    return rebuild_markdown_from_sections(merged_sections)

def extract_markdown_sections(text):
    """Extract markdown sections by heading"""
    sections = {}
    current_section = None
    current_content = []

    for line in text.split('\n'):
        if line.startswith('#'):
            # New section
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = line.strip()
            current_content = [line]
        else:
            current_content.append(line)

    if current_section:
        sections[current_section] = '\n'.join(current_content)

    return sections

def rebuild_markdown_from_sections(sections):
    """Rebuild markdown from sections"""
    return '\n\n'.join(sections.values())
```

### Step 8: Verification After Integration

After each integration step:

```bash
# Verify services still running
python3 ~/.claude/hooks/environmental-awareness.py

# Compare before and after
diff ~/.claude/backups/latest/environmental-awareness.json \
     ~/.claude/environmental-awareness.json

# Check for port conflicts
netstat -an | grep LISTEN | sort

# Verify MCP servers load
# (Restart Claude Code and check for errors)
```

## Integration Checklist

Use this checklist to ensure complete integration:

```markdown
### Pre-Integration
- [ ] Environmental awareness complete
- [ ] Current state cataloged
- [ ] Backups created
- [ ] Integration plan reviewed

### MCP Configuration
- [ ] Existing MCP servers identified
- [ ] New MCP servers merged (not replaced)
- [ ] Port conflicts resolved
- [ ] Configuration validated
- [ ] Claude Code restarted successfully

### Services
- [ ] Existing services identified
- [ ] Missing services installed
- [ ] No services stopped or broken
- [ ] All services accessible

### Databases
- [ ] Existing databases located
- [ ] Existing databases preserved
- [ ] New databases created in different locations
- [ ] All data intact

### Hooks, Skills, Agents
- [ ] Existing hooks backed up
- [ ] New hooks added without conflicts
- [ ] Skills merged
- [ ] Agents merged
- [ ] Slash commands merged

### Verification
- [ ] All original services still running
- [ ] All original data still accessible
- [ ] New components working
- [ ] No port conflicts
- [ ] No configuration errors
- [ ] verify-onboarding.sh passes

### Documentation
- [ ] Integration log created
- [ ] Conflicts documented
- [ ] Manual merge tasks identified
- [ ] Rollback procedure tested
```

## Rollback Procedure

If anything goes wrong:

```bash
# Find your backup
BACKUP_DIR=$(ls -td ~/.claude/backups/* | head -1)
echo "Rolling back from: $BACKUP_DIR"

# Restore configurations
cp "$BACKUP_DIR/claude.json.backup" ~/.claude.json
cp "$BACKUP_DIR/mcp.json.backup" ~/.mcp.json
cp "$BACKUP_DIR/CLAUDE.md.backup" ~/.claude/CLAUDE.md

# Restore hooks, skills, agents
for dir in hooks skills agents commands; do
    if [ -d "$BACKUP_DIR/${dir}.backup" ]; then
        rm -rf ~/.claude/$dir
        cp -r "$BACKUP_DIR/${dir}.backup" ~/.claude/$dir
    fi
done

# Restart Claude Code
pkill -f claude-code
# Restart manually

echo "✅ Rollback complete"
```

## Common Integration Scenarios

### Scenario 1: Qdrant Already Running

```bash
# Detection
if curl -s http://localhost:6333 > /dev/null; then
    echo "✅ Qdrant already running"

    # Check if enhanced-memory collection exists
    if curl -s http://localhost:6333/collections/enhanced_memory_v2 | grep -q "result"; then
        echo "✅ Collection exists - will reuse"
    else
        echo "📝 Collection missing - will create"
        # Create collection in existing Qdrant
    fi

    # Skip Qdrant installation
    INSTALL_QDRANT=false
else
    # Install Qdrant
    INSTALL_QDRANT=true
fi
```

### Scenario 2: Different Database Location

```bash
# User has databases in ~/databases instead of /Volumes/SSDRAID0
DETECTED_DB_PATH=$(cat ~/.claude/environmental-awareness.json | jq -r '.databases | keys[0]')

if [ -n "$DETECTED_DB_PATH" ]; then
    echo "✅ Using existing database path: $DETECTED_DB_PATH"
    # Update all configuration to use this path
    DB_PATH="$DETECTED_DB_PATH"
else
    # Use default
    DB_PATH="/Volumes/SSDRAID0/agentic-system/databases"
fi
```

### Scenario 3: MCP Server Name Conflict

```python
# If user already has "enhanced-memory-mcp" but different implementation
existing_servers = load_json("~/.claude.json").get("mcpServers", {})

if "enhanced-memory-mcp" in existing_servers:
    # Check if it's our implementation
    existing_cmd = existing_servers["enhanced-memory-mcp"].get("command")

    if "agentic-system/mcp-servers/enhanced-memory-mcp" in existing_cmd:
        # Same implementation - skip
        print("✅ enhanced-memory-mcp already configured correctly")
    else:
        # Different implementation - use alternate name
        print("⚠️  Conflict: enhanced-memory-mcp exists with different implementation")
        print("   Installing as: enhanced-memory-mcp-cluster")

        merged["mcpServers"]["enhanced-memory-mcp-cluster"] = new_server_config
```

## Summary

The key to intelligent integration is:

1. **Know what you have** (environmental awareness)
2. **Plan before acting** (installation plan)
3. **Merge, don't replace** (preserve existing)
4. **Backup everything** (enable rollback)
5. **Verify each step** (catch issues early)
6. **Test thoroughly** (ensure nothing broke)

This ensures new nodes can join the cluster without losing any of their existing functionality, data, or configuration.
