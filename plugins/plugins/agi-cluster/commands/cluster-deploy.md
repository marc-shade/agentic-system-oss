---
description: Deploy components across the AGI cluster
---

# Cluster Deployment

Deploy and synchronize components across cluster nodes.

## Deployment Targets

| Node | Path | Services |
|------|------|----------|
| mac-studio | /Volumes/SSDRAID0 | enhanced-memory, agent-runtime |
| macpro51 | /mnt/agentic-system | security-scanner, agi-mcp |
| macbook-air-m3 | ~/agentic-system | research-paper, voice-mode |

## Deployment Commands

### Deploy to Specific Node
```bash
~/.claude/plugins/agi-cluster/scripts/deploy-to-node.sh <node> <component>
```

### Sync All Nodes
```bash
~/.claude/plugins/agi-cluster/scripts/sync-nodes.sh
```

## Components Available

### MCP Servers
- enhanced-memory-mcp
- agent-runtime-mcp
- agi-mcp
- research-paper-mcp
- security-scanner-mcp

### Configurations
- cluster-topology.yaml
- node-profiles.yaml
- claude-flow.yaml

### Scripts
- setup.sh
- init-databases.py
- health-check.py

## Deployment Process

1. **Verify SSH Access**: Check connectivity to target node
2. **Backup Current**: Snapshot current state
3. **Transfer Files**: rsync components
4. **Install Dependencies**: pip/npm install
5. **Restart Services**: Reload MCP servers
6. **Verify**: Health check

## Quick Actions

1. **Deploy MCP server** - Push server to node
2. **Sync configs** - Update all node configurations
3. **Full sync** - Complete cluster synchronization

## Example Usage

```bash
# Deploy enhanced-memory to mac-studio
~/.claude/plugins/agi-cluster/scripts/deploy-to-node.sh mac-studio enhanced-memory-mcp

# Sync all configurations
~/.claude/plugins/agi-cluster/scripts/sync-nodes.sh --configs-only

# Full cluster update
~/.claude/plugins/agi-cluster/scripts/sync-nodes.sh --all
```

What would you like to deploy?

---

*Cluster deployment powered by agi-cluster scripts*
