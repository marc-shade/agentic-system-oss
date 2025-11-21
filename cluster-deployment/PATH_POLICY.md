# Cluster Path Policy - Remote Node Autonomy

**Critical Rule**: When executing tasks or copying files to/from remote nodes, **NEVER** hardcode paths like `/Users/marc/agentic-system` or `~/agentic-system`.

## Problem

Code that hardcodes paths forces remote nodes into a specific directory structure:

```python
# ❌ WRONG - Forces ~/agentic-system on remote node
command = f"scp marc@{node_ip}:~/agentic-system/file.txt ."

# ❌ WRONG - Assumes specific path structure
command = f"ssh marc@{node_ip} 'mkdir ~/agentic-system'"
```

## Solution

Each node determines its own paths via `cluster-nodes.json` or local configuration:

```python
# ✅ CORRECT - Query node's actual storage_base
from simple_cluster_config import get_node_config

node_config = get_node_config(node_id)
storage_base = node_config['storage_base']
command = f"scp marc@{node_ip}:{storage_base}/file.txt ."
```

## Files to Fix

These files currently have hardcoded `~/agentic-system` paths:

1. `autonomous_self_improvement_agent.py` (lines 158, 198, 221)
2. `node_discovery.py` (line 491)

They should use `cluster-nodes.json` to get each node's actual `storage_base`.

## Orchestrator Config Only

The orchestrator (Mac Studio) can document where **its** files live:

- `/Users/marc/.claude/node-config.json` - Says where Mac Studio's files are
- `/Users/marc/.claude/CLAUDE.md` - Documents Mac Studio's environment
- `/Volumes/SSDRAID0/agentic-system/CLUSTER_PATHS.md` - Mac Studio's paths

But these are **informational only** for the orchestrator. Remote nodes are not required to follow this structure.

## Key Principles

1. **Orchestrator documents its own paths** - For clarity about where Mac Studio stores things
2. **Remote nodes determine their own paths** - Via their own configurations
3. **Tasks query paths dynamically** - Use `cluster-nodes.json` to get actual paths
4. **No hardcoded assumptions** - Code must work regardless of each node's path choices

## Migration Complete

As of 2025-11-20:
- ✅ Mac Studio config updated to use `/Volumes/SSDRAID0/agentic-system`
- ✅ No `/Users/marc/agentic-system` references in Mac Studio code
- ⚠️  Need to fix: SCP commands that assume `~/agentic-system` on remote nodes

## See Also

- `/Volumes/SSDRAID0/agentic-system/cluster-deployment/cluster-nodes.json` - Node registry with actual paths
- `/Volumes/SSDRAID0/agentic-system/cluster-deployment/simple_cluster_config.py` - Path lookup utilities
