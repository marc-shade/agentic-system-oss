# AGI-Cluster Plugin

Distributed multi-node AGI with inter-node communication and swarm intelligence.

## Overview

This plugin enables distributed AGI across multiple machines:
- **Node Communication**: AI personas can chat between nodes
- **Task Distribution**: Intelligent routing based on capabilities
- **Swarm Intelligence**: Coordinated multi-agent operations
- **Collective Learning**: Shared knowledge across cluster

## Requirements

- All lower-tier plugins installed (agi-core, agi-memory, agi-extended)
- Multiple machines with SSH access
- Shared storage (recommended)

## Cluster Nodes

| Node | Role | Capabilities |
|------|------|--------------|
| mac-studio | Orchestrator | Coordination, planning, synthesis |
| macpro51 | Builder | Code, testing, security |
| macbook-air-m3 | Researcher | Research, analysis, docs |

## Installation

```bash
# Install plugin
/plugin install agi-cluster@agentic-marketplace

# Run setup
~/.claude/plugins/agi-cluster/scripts/setup.sh
```

## Configuration

### Cluster Topology
Edit `~/.claude/agi/cluster-topology.yaml`:
- Define nodes and their roles
- Configure SSH connections
- Set task routing rules
- Configure shared storage

### Node Profiles
Edit `~/.claude/agi/node-profiles.yaml`:
- Define persona for each role
- List capabilities
- Set communication style

## MCP Servers

### node-chat
Inter-node AI persona communication.

**Tools:**
- `send_message_to_node` - Direct message to node
- `broadcast_to_cluster` - Message all nodes
- `get_conversation_history` - View past chats
- `get_cluster_awareness` - All nodes status
- `decompose_goal` - Break goal into node tasks
- `initiate_research_pipeline` - Start research flow
- `start_improvement_cycle` - Distributed improvement

### cluster-execution
Distributed task execution.

**Tools:**
- Task routing based on node capabilities
- Load balancing across nodes
- Progress tracking

### claude-flow
Swarm orchestration.

**Tools:**
- `swarm_init` - Initialize agent swarm
- `agent_spawn` - Create specialized agents
- `task_orchestrate` - Coordinate complex tasks
- `neural_train` - Train coordination patterns

## Commands

### /cluster-status
View cluster health and node status.

### /cluster-chat
Communicate with other nodes.

### /cluster-task
Distribute tasks across cluster.

### /cluster-deploy
Deploy components to nodes.

## Communication Patterns

### Direct Message
```
mcp__node-chat__send_message_to_node
  --to_node mac-studio
  --message "Please coordinate the refactoring task"
```

### Broadcast
```
mcp__node-chat__broadcast_to_cluster
  --message "Starting new research cycle"
  --priority high
```

### Goal Decomposition
```
mcp__node-chat__decompose_goal
  --goal "Optimize memory consolidation performance"
```

## Distributed Workflows

### Research-to-Implementation
1. **Researcher**: Find relevant papers
2. **Orchestrator**: Evaluate applicability
3. **Builder**: Implement if approved
4. **All**: Store learnings

### Distributed Code Review
1. **Builder**: Security analysis
2. **Researcher**: Best practices check
3. **Orchestrator**: Synthesize findings

### Self-Improvement Cycle
1. **All**: Report current metrics
2. **Orchestrator**: Identify bottlenecks
3. **Researcher**: Find solutions
4. **Builder**: Implement optimizations

## SSH Setup

```bash
# Generate SSH key (if needed)
ssh-keygen -t ed25519

# Copy to other nodes
ssh-copy-id marc@mac-studio.local
ssh-copy-id marc@macpro51.local
ssh-copy-id marc@macbook-air-m3.local
```

## Shared Storage

Recommended: NFS or SMB mount at `/mnt/agentic-system` on all nodes.

Alternative: Use `cluster-inbox` directory for file-based messaging.

## Troubleshooting

### Node unreachable
```bash
# Test SSH
ssh marc@<node>.local

# Check if hostname resolves
ping <node>.local

# Use IP instead
ssh marc@192.168.1.x
```

### Messages not delivering
```bash
# Check cluster inbox
ls -la /mnt/agentic-system/cluster-inbox/

# Verify node-chat server
python3 ~/.claude/plugins/agi-cluster/mcp/node-chat/server.py
```

### Task routing issues
```bash
# Check cluster topology
cat ~/.claude/agi/cluster-topology.yaml

# Verify node capabilities match
cat ~/.claude/agi/node-profiles.yaml
```

## Architecture

```
                    ┌─────────────────┐
                    │   Orchestrator  │
                    │   (mac-studio)  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼────────┐     │     ┌────────▼────────┐
     │     Builder     │     │     │    Researcher   │
     │   (macpro51)    │     │     │(macbook-air-m3) │
     └─────────────────┘     │     └─────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Shared Storage │
                    │(/mnt/agentic)   │
                    └─────────────────┘
```

## Future Capabilities

- Auto-scaling based on load
- Node failure recovery
- Consensus mechanisms
- Federated learning
