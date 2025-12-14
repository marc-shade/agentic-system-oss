# Node Chat MCP Server

Real-time inter-node AI communication for distributed agentic clusters.

## Features

- **Direct Messaging**: Send messages between AI personas on different nodes
- **Conversation History**: Track and retrieve past conversations
- **Persona-Aware**: Each node has a distinct AI persona and capabilities
- **Cluster Coordination**: Coordinate tasks across multiple AI nodes
- **Memory Integration**: Conversations stored in enhanced-memory for learning

## MCP Tools

| Tool | Description |
|------|-------------|
| `send_message_to_node` | Send a chat message to another node's AI persona |
| `get_conversation_history` | View past conversations with a specific node |
| `get_my_active_conversations` | List all active conversations this node is participating in |
| `check_for_new_messages` | Check for unread messages from other nodes |
| `broadcast_to_cluster` | Send a message to all nodes in the cluster |
| `get_my_awareness` | Get self-awareness of this node's identity and state |
| `get_cluster_awareness` | Get awareness of all nodes in the cluster |
| `get_node_status` | Get detailed status of a specific node |
| `prepare_conversation_context` | Load context before starting a conversation |
| `remember_fact_about_node` | Store learned facts about other nodes |

## Requirements

- Python 3.10+
- mcp SDK
- Node configuration at `~/.claude/node-config.json`

## Installation

```bash
pip install mcp
```

## Usage

```bash
python server.py
```

## Cluster Nodes

Supports communication with configurable cluster nodes:
- orchestrator - coordination, monitoring, routing
- builder - compilation, testing, containers
- researcher - analysis, documentation, research
- inference - AI inference and GPU workloads

Node configuration is loaded from `~/.claude/cluster-nodes.json` or `CLUSTER_NODE_IDS` environment variable.

## License

MIT
