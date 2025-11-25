---
description: Show AGI cluster status, node health, and active tasks
---

# AGI Cluster Status

Checking status of all nodes in the AGI cluster.

## Cluster Overview

Let me query the cluster for current status.

## Status Checks

### Node Health
```
mcp__node-chat__get_cluster_awareness
mcp__node-chat__get_agi_system_health
```

### Active Conversations
```
mcp__node-chat__watch_cluster_conversations
mcp__node-chat__get_my_active_conversations
```

### Autonomous Activities
```
mcp__node-chat__monitor_autonomous_activities
```

## Cluster Tools

### Communication
- `send_message_to_node` - Send message to specific node
- `broadcast_to_cluster` - Broadcast to all nodes
- `get_conversation_history` - View past conversations

### Awareness
- `get_my_awareness` - This node's status
- `get_cluster_awareness` - All nodes' status
- `get_node_status` - Specific node status

### AGI Coordination
- `decompose_goal` - Break goal into multi-node tasks
- `initiate_research_pipeline` - Start research workflow
- `start_improvement_cycle` - Begin self-improvement

## Quick Actions

1. **Check all nodes** - View health and availability
2. **View conversations** - See inter-node communication
3. **Check autonomous activities** - What nodes are doing

---

*Cluster management powered by node-chat-mcp*
