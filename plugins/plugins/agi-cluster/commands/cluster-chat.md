---
description: Chat with other nodes in the AGI cluster
---

# Cluster Chat

Communicate with AI personas on other nodes in the cluster.

## Available Nodes

| Node | Role | Capabilities |
|------|------|--------------|
| mac-studio | Orchestrator | Coordination, planning, decisions |
| macpro51 | Builder | Code, testing, security |
| macbook-air-m3 | Researcher | Research, analysis, docs |

## Chat Commands

### Send Message
```
mcp__node-chat__send_message_to_node --to_node <node> --message "<message>"
```

### Broadcast
```
mcp__node-chat__broadcast_to_cluster --message "<message>" --priority normal
```

### Check Messages
```
mcp__node-chat__check_for_new_messages
```

### View History
```
mcp__node-chat__get_conversation_history --with_node <node>
```

## Communication Patterns

### Request Help
"@mac-studio I need help coordinating a complex refactoring task"

### Delegate Task
"@macpro51 Please run security scan on the auth module"

### Share Research
"@macbook-air-m3 Found relevant paper on RAG optimization, please analyze"

### Status Check
"@all What are you currently working on?"

## Conversation View

```
mcp__node-chat__view_conversations_threaded --mode recent
```

## Example Usage

Who would you like to chat with?

---

*Inter-node communication powered by node-chat-mcp*
