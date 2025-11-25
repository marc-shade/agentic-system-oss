# Migration Guide: Current System to Plugin Architecture

This guide helps existing users of the agentic system migrate to the new plugin-based architecture.

## Overview

The current system has been refactored into 4 distributable plugins:

| Current Component | New Plugin |
|-------------------|------------|
| ~/.claude/commands/* | agi-core |
| ~/.claude/agents/* | agi-core |
| ~/.claude/CLAUDE.md | agi-core |
| agent-runtime-mcp | agi-memory |
| agi-mcp | agi-memory |
| ember-mcp | agi-memory |
| enhanced-memory-mcp | agi-extended |
| research-paper-mcp | agi-extended |
| video-transcript-mcp | agi-extended |
| voice-mode | agi-extended |
| node-chat-mcp | agi-cluster |
| cluster-execution-mcp | agi-cluster |
| claude-flow-mcp | agi-cluster |

## Migration Steps

### Step 1: Backup Current State

```bash
# Create backup directory
mkdir -p ~/.claude/backup-$(date +%Y%m%d)

# Backup current configuration
cp -r ~/.claude/commands ~/.claude/backup-$(date +%Y%m%d)/
cp -r ~/.claude/agents ~/.claude/backup-$(date +%Y%m%d)/
cp ~/.claude/CLAUDE.md ~/.claude/backup-$(date +%Y%m%d)/
cp ~/.claude.json ~/.claude/backup-$(date +%Y%m%d)/

# Backup databases (if using agi-memory or higher)
cp -r /mnt/agentic-system/databases ~/.claude/backup-$(date +%Y%m%d)/
```

### Step 2: Export Persistent Data

If you have persistent data (goals, tasks, memories), export them:

```bash
# Run export script (creates JSON export files)
python3 /mnt/agentic-system/scripts/export-agi-state.py \
  --output ~/.claude/agi/migration/
```

This exports:
- Goals and tasks from agent-runtime-mcp
- Memory entities from enhanced-memory-mcp
- Action outcomes from agi-mcp
- Ember learning data

### Step 3: Set Up Marketplace

#### Option A: Local Installation

```bash
# Copy marketplace to local location
cp -r /mnt/agentic-system/plugins/marketplace ~/.claude/marketplaces/agentic-marketplace

# Add to Claude Code settings
# Edit ~/.claude/settings.json (create if doesn't exist):
```

```json
{
  "plugins": {
    "marketplaces": [
      {
        "name": "agentic-marketplace",
        "path": "~/.claude/marketplaces/agentic-marketplace"
      }
    ]
  }
}
```

#### Option B: Shared Team Installation

```bash
# Admin: Copy to shared location
cp -r /mnt/agentic-system/plugins/marketplace /path/to/shared/agentic-marketplace

# Admin: Add to repository's .claude/settings.json
# Members will auto-install when they trust the repo
```

### Step 4: Install Plugins

Restart Claude Code, then install plugins matching your current setup:

```bash
# For basic AGI patterns (was using commands/agents/CLAUDE.md)
/plugin install agi-core@agentic-marketplace

# For persistent memory (was using agent-runtime-mcp, agi-mcp, ember-mcp)
/plugin install agi-memory@agentic-marketplace

# For full AGI (was using enhanced-memory-mcp, research tools, voice)
/plugin install agi-extended@agentic-marketplace

# For cluster (was using node-chat-mcp, cluster tools)
/plugin install agi-cluster@agentic-marketplace
```

### Step 5: Import Data

After installing plugins, import your backed-up data:

```bash
# Run import script
python3 ~/.claude/plugins/agi-extended/scripts/import-state.py \
  --input ~/.claude/agi/migration/
```

### Step 6: Verify Migration

```bash
# Run status check
/agi-status

# Verify agents work
@deep-thinker Hello, verify you're working

# Verify memory (if applicable)
# Check goals and tasks are restored
```

### Step 7: Clean Up Old Configuration

Once verified, you can remove old configuration:

```bash
# Remove old commands (now in plugin)
rm -rf ~/.claude/commands/agi-*.md

# Remove old agents (now in plugin)
rm -rf ~/.claude/agents/*.agent.md

# Update CLAUDE.md to remove duplicated AGI instructions
# (plugin provides its own CLAUDE.md)
```

## Configuration Migration

### Old: ~/.claude.json MCP Servers

Your current MCP server configs in `~/.claude.json` can be migrated to plugin `.mcp.json` files.

**Before (in ~/.claude.json):**
```json
{
  "mcpServers": {
    "agent-runtime": {
      "command": "python3",
      "args": ["/path/to/agent-runtime-mcp/server.py"]
    }
  }
}
```

**After (handled by plugin):**
The agi-memory plugin's `.mcp.json` handles this automatically.

### Old: CLAUDE.md Behavioral Instructions

Your behavioral instructions in `~/.claude/CLAUDE.md` are now provided by the agi-core plugin.

**What to keep**: Any custom, project-specific instructions not related to AGI patterns.

**What to remove**: AGI behavioral instructions (action recording, gap identification, etc.) - these are now in the plugin.

## Rollback Procedure

If migration fails, restore from backup:

```bash
# Restore old configuration
cp -r ~/.claude/backup-*/commands ~/.claude/
cp -r ~/.claude/backup-*/agents ~/.claude/
cp ~/.claude/backup-*/CLAUDE.md ~/.claude/
cp ~/.claude/backup-*/.claude.json ~/

# Restart Claude Code
```

## Troubleshooting

### Plugin Not Found
```
Error: Plugin 'agi-core' not found in marketplace
```
**Solution**: Verify marketplace path in `~/.claude/settings.json` is correct.

### MCP Server Conflict
```
Error: MCP server 'agent-runtime' already configured
```
**Solution**: Remove old MCP config from `~/.claude.json` before installing agi-memory plugin.

### Data Import Failed
```
Error: Cannot import - database schema mismatch
```
**Solution**: Check plugin version matches export version. May need migration script.

### Agent Not Responding
```
Error: Agent @deep-thinker not found
```
**Solution**: Verify agi-core plugin is installed and enabled:
```
/plugin list
/plugin enable agi-core@agentic-marketplace
```

## Support

- **Issues**: https://github.com/your-org/agi-plugins/issues
- **Migration Help**: Tag issue with `migration`
- **Discussions**: https://github.com/your-org/agi-plugins/discussions
