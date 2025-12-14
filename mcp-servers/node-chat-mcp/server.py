#!/usr/bin/env python3
"""
Node Chat MCP Server
Enables AI personas to communicate directly with other node personas in real-time.

Provides tools for:
- Sending chat messages to other nodes
- Viewing conversation history
- Managing active conversations
- Real-time inter-node AI communication
"""

import sys
import json
import logging
from pathlib import Path
from typing import Any

# Add cluster-deployment to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "cluster-deployment"))

from node_chat_client import NodeChatClient
from node_persona import get_persona
from enhanced_conversation_viewer import EnhancedConversationViewer
from agi_orchestrator import AGIOrchestrator

# Enhanced memory integration
from memory_integration import get_memory_integration, ENHANCED_MEMORY_ENABLED

# Conversation context management
from conversation_context import get_context_manager, ConversationContextManager

# MCP SDK
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp import types

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize server
server = Server("node-chat")

# Load node configuration
node_config_path = Path.home() / ".claude" / "node-config.json"
with open(node_config_path) as f:
    NODE_CONFIG = json.load(f)

# Load available cluster node IDs from config or environment
# Set CLUSTER_NODE_IDS as JSON array: ["node1", "node2", "node3"]
def _get_cluster_node_ids() -> list:
    """Get list of valid cluster node IDs."""
    env_nodes = os.environ.get("CLUSTER_NODE_IDS")
    if env_nodes:
        try:
            return json.loads(env_nodes)
        except json.JSONDecodeError:
            pass
    # Fall back to cluster config file
    cluster_config_path = Path.home() / ".claude" / "cluster-nodes.json"
    if cluster_config_path.exists():
        try:
            with open(cluster_config_path) as f:
                config = json.load(f)
                return list(config.keys()) if isinstance(config, dict) else config
        except (json.JSONDecodeError, IOError):
            pass
    # Default to generic node names
    return ["orchestrator", "builder", "researcher", "inference"]

import os
CLUSTER_NODE_IDS = _get_cluster_node_ids()

# Initialize chat client and persona
chat_client = NodeChatClient(NODE_CONFIG['node_id'], NODE_CONFIG['storage']['base'])
persona = get_persona(NODE_CONFIG['node_id'], NODE_CONFIG['storage']['base'])

# Initialize enhanced memory integration
memory_integration = get_memory_integration(NODE_CONFIG['storage']['base'], NODE_CONFIG['node_id'])
logger.info(f"Enhanced memory integration: {'ENABLED' if ENHANCED_MEMORY_ENABLED else 'DISABLED'}")

# Initialize conversation context manager
context_manager = get_context_manager(NODE_CONFIG['storage']['base'], NODE_CONFIG['node_id'])
logger.info(f"Conversation context manager initialized for {NODE_CONFIG['node_id']}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available chat tools for AI personas"""
    return [
        types.Tool(
            name="send_message_to_node",
            description="""
            Send a chat message to another node's AI persona.

            Use this to communicate directly with other nodes in the cluster.
            Messages are delivered via multiple channels (HTTP, database, file) for reliability.

            Example: Send strategic coordination to orchestrator, request analysis from researcher,
            or notify builder of compilation tasks.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "to_node": {
                        "type": "string",
                        "description": "Target node ID (e.g., orchestrator, builder, researcher, inference)",
                        "enum": CLUSTER_NODE_IDS
                    },
                    "message": {
                        "type": "string",
                        "description": "Message content to send"
                    }
                },
                "required": ["to_node", "message"]
            }
        ),
        types.Tool(
            name="get_conversation_history",
            description="""
            Get chat history with another node.

            View past conversations to maintain context and continuity.
            Returns messages in chronological order with timestamps.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "with_node": {
                        "type": "string",
                        "description": "Node ID to get history with",
                        "enum": CLUSTER_NODE_IDS
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum messages to retrieve (default: 50)",
                        "default": 50
                    }
                },
                "required": ["with_node"]
            }
        ),
        types.Tool(
            name="get_my_active_conversations",
            description="""
            Get all active conversations this node is participating in.

            Shows ongoing chats with other nodes, message counts, and last activity.
            Useful for maintaining awareness of cluster communication state.
            """,
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="check_for_new_messages",
            description="""
            Check if other nodes have sent messages to this node.

            Returns unread messages from other node personas.
            Use this periodically to stay responsive to cluster communication.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "mark_as_read": {
                        "type": "boolean",
                        "description": "Mark retrieved messages as read (default: true)",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="broadcast_to_cluster",
            description="""
            Send a message to all nodes in the cluster.

            Use for announcements, status updates, or cluster-wide coordination.
            Messages delivered to all nodes except self.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Broadcast message content"
                    },
                    "priority": {
                        "type": "string",
                        "description": "Message priority",
                        "enum": ["low", "normal", "high", "urgent"],
                        "default": "normal"
                    }
                },
                "required": ["message"]
            }
        ),
        types.Tool(
            name="get_my_awareness",
            description="""
            Get complete self-awareness of this node's identity, capabilities, and current state.

            Returns:
            - Node identity and role
            - Current environmental status (CPU, memory, storage, health)
            - Capabilities and specialties
            - Situational awareness (cluster state, active tasks, communications)

            Use this to understand your own current state and capabilities.
            """,
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_cluster_awareness",
            description="""
            Get awareness of all nodes in the cluster - their capabilities, status, and functions.

            Returns complete information about all cluster nodes including:
            - Node roles and specialties
            - Current online/offline status
            - Capabilities and functions
            - Recent activity

            Use this to understand what other nodes can do and their current availability.
            """,
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_node_status",
            description="""
            Get detailed status and awareness of a specific node.

            Query another node for its current state, capabilities, and availability.
            Useful for determining if a node can handle specific tasks.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "Target node ID",
                        "enum": CLUSTER_NODE_IDS
                    }
                },
                "required": ["node_id"]
            }
        ),
        types.Tool(
            name="watch_cluster_conversations",
            description="""
            Monitor and display all cluster conversations in real-time.

            Shows agent-to-agent communications across all nodes with:
            - Color-coded nodes for easy identification
            - Message timestamps and delivery status
            - Conversation history context
            - Live updates as messages are sent/received

            Use this to observe how nodes are coordinating and communicating.
            Returns formatted conversation stream for human readability.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Display mode",
                        "enum": ["recent", "live_snapshot", "stats"],
                        "default": "recent"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent messages to show (default: 20)",
                        "default": 20
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="view_conversations_threaded",
            description="""
            View cluster conversations in rich threaded format (like Sequential Thinking).

            Displays conversations grouped by context with:
            - Node personas and reasoning
            - Message threading and context
            - Delivery status and timestamps
            - Expandable message content

            This gives you a comprehensive view of autonomous node coordination.
            Perfect for observing collective intelligence in action!

            Modes:
            - "threaded": Group by conversation context (default)
            - "recent": Chronological stream
            - "active": Only active (last hour)
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of messages (default: 20)",
                        "default": 20
                    },
                    "mode": {
                        "type": "string",
                        "description": "Display mode",
                        "enum": ["threaded", "recent", "active"],
                        "default": "threaded"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="decompose_goal",
            description="""
            AGI: Decompose a complex goal into coordinated multi-node tasks.

            Analyzes goal requirements and optimally assigns to specialized nodes.
            This enables autonomous distributed problem-solving across the cluster.

            Example: "Optimize memory consolidation to be 10x faster"
            → Builder: Benchmark performance
            → Researcher: Find optimization techniques
            → Orchestrator: Coordinate implementation

            Returns structured plan with node assignments.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "High-level goal to decompose"
                    }
                },
                "required": ["goal"]
            }
        ),
        types.Tool(
            name="initiate_research_pipeline",
            description="""
            AGI: Start autonomous research-to-implementation pipeline.

            Fully autonomous flow:
            1. Researcher searches papers and extracts insights
            2. Orchestrator evaluates applicability
            3. Builder implements if approved
            4. Knowledge stored in cluster memory

            This is how the system learns and improves itself!

            Example: "efficient graph neural networks for pattern extraction"
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "research_topic": {
                        "type": "string",
                        "description": "What to research"
                    }
                },
                "required": ["research_topic"]
            }
        ),
        types.Tool(
            name="start_improvement_cycle",
            description="""
            AGI: Initiate recursive self-improvement cycle.

            Coordinates nodes to improve a specific system metric:
            1. Baseline: Builder measures current performance
            2. Analysis: Orchestrator identifies bottlenecks
            3. Research: Researcher finds solutions
            4. Implementation: Builder applies optimizations
            5. Validation: Builder measures improvement
            6. Consolidation: All nodes store learnings

            This is recursive self-improvement in action!

            Example metrics: "memory_consolidation_speed", "task_routing_latency"
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "target_metric": {
                        "type": "string",
                        "description": "What to improve"
                    }
                },
                "required": ["target_metric"]
            }
        ),
        types.Tool(
            name="get_agi_system_health",
            description="""
            AGI: Get overall AGI system health and status.

            Shows:
            - Node status and activity levels
            - Communication health (messages, conversations)
            - Memory system health
            - Learning system status

            Use this to monitor the collective intelligence.
            """,
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="monitor_autonomous_activities",
            description="""
            AGI: Monitor what nodes are doing autonomously right now.

            Shows:
            - Active conversations between nodes
            - Ongoing distributed tasks
            - Recent collective decisions
            - Autonomous coordination patterns

            Watch the system coordinate itself!
            """,
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="search_conversation_memory",
            description="""
            Search past node conversations using semantic similarity.

            Uses enhanced-memory vector database to find relevant past conversations.
            Useful for:
            - Finding how similar problems were solved before
            - Retrieving context from past coordination
            - Learning from previous node interactions

            Returns semantically similar messages from conversation history.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for in past conversations"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default: 10)",
                        "default": 10
                    },
                    "from_node": {
                        "type": "string",
                        "description": "Filter by sender node (optional)",
                        "enum": CLUSTER_NODE_IDS
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="get_memory_stats",
            description="""
            Get statistics about node conversation memory storage.

            Shows:
            - Whether enhanced memory is enabled
            - Number of stored conversations
            - Memory collection status
            """,
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="prepare_conversation_context",
            description="""
            Get complete context before starting a conversation with another node.

            This is THE KEY TOOL for persona-aware node conversations!

            Returns rich context including:
            - Your persona (role, style, specialties)
            - Your current system state (CPU, memory, availability)
            - Past conversation history with this specific node
            - Relationship summary (how many times we've talked, collaboration history)
            - Key facts you've learned about them
            - Important highlights from past conversations

            ALWAYS call this before engaging in substantive conversation with another node.
            It helps you remember who you are and what you know about them!

            Example: Before sending a task request to the orchestrator, call this to:
            - Remember your role and persona (pragmatic, execution-focused)
            - See if you've worked with that node before
            - Recall any past agreements or collaboration patterns
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "with_node": {
                        "type": "string",
                        "description": "Node to prepare context for",
                        "enum": CLUSTER_NODE_IDS
                    },
                    "include_history": {
                        "type": "boolean",
                        "description": "Include recent message history (default: true)",
                        "default": True
                    },
                    "max_history": {
                        "type": "integer",
                        "description": "Max history messages to include (default: 20)",
                        "default": 20
                    }
                },
                "required": ["with_node"]
            }
        ),
        types.Tool(
            name="start_conversation_with_context",
            description="""
            Start a new conversation with another node, automatically loading context.

            This combines prepare_conversation_context + send_message in one call.
            Use this when initiating a new conversation topic.

            The message will be sent with full awareness of:
            - Who you are (your persona and capabilities)
            - Your current state (busy/available)
            - Past relationship with this node
            - Previous conversations and decisions

            Returns both the context that was used AND the message delivery status.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "to_node": {
                        "type": "string",
                        "description": "Target node",
                        "enum": CLUSTER_NODE_IDS
                    },
                    "message": {
                        "type": "string",
                        "description": "Message to send"
                    },
                    "topic": {
                        "type": "string",
                        "description": "Conversation topic for tracking (optional)"
                    }
                },
                "required": ["to_node", "message"]
            }
        ),
        types.Tool(
            name="remember_fact_about_node",
            description="""
            Store a learned fact about another node for future reference.

            Use this when you learn something important about another node:
            - Their capabilities or limitations
            - Their preferences or communication style
            - Expertise areas or specializations
            - Performance characteristics

            Facts are stored persistently and will be included in future
            conversation context with that node.

            Example: After the orchestrator says they prefer detailed status updates,
            store: fact_type="preference", content="Prefers detailed status updates"
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "about_node": {
                        "type": "string",
                        "description": "Node the fact is about",
                        "enum": CLUSTER_NODE_IDS
                    },
                    "fact_type": {
                        "type": "string",
                        "description": "Category of fact",
                        "enum": ["capability", "preference", "limitation", "expertise", "communication_style", "availability_pattern"]
                    },
                    "content": {
                        "type": "string",
                        "description": "The fact to remember"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence in this fact (0.0-1.0, default: 0.8)",
                        "default": 0.8
                    }
                },
                "required": ["about_node", "fact_type", "content"]
            }
        ),
        types.Tool(
            name="get_relationship_summary",
            description="""
            Get a summary of your relationship with another node.

            Shows:
            - Total messages exchanged
            - When you first talked
            - Last interaction time
            - Collaboration areas
            - Known facts about them
            - Communication patterns

            Useful for understanding your history with a specific node.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "with_node": {
                        "type": "string",
                        "description": "Node to get relationship summary for",
                        "enum": CLUSTER_NODE_IDS
                    }
                },
                "required": ["with_node"]
            }
        ),
        types.Tool(
            name="summarize_conversation",
            description="""
            Update the summary of a conversation with key topics and decisions.

            Call this after important conversations to record:
            - Main topics discussed
            - Decisions made
            - Notes about the interaction

            This helps future conversations by providing quick context.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "with_node": {
                        "type": "string",
                        "description": "Node the conversation was with",
                        "enum": CLUSTER_NODE_IDS
                    },
                    "key_topics": {
                        "type": "array",
                        "description": "Main topics discussed",
                        "items": {"type": "string"}
                    },
                    "key_decisions": {
                        "type": "array",
                        "description": "Decisions or agreements made",
                        "items": {"type": "string"}
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of the conversation"
                    }
                },
                "required": ["with_node"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool calls for node chat"""

    if not arguments:
        arguments = {}

    try:
        if name == "send_message_to_node":
            to_node = arguments["to_node"]
            message = arguments["message"]

            # Send message via multi-channel client
            result = chat_client.send_message(to_node, message)

            if result['success']:
                channels = [k for k, v in result['delivery_channels'].items() if v.get('success')]

                # Track conversation context
                conversation_id = result.get('conversation_id', f"{NODE_CONFIG['node_id']}-{to_node}-default")
                context_manager.update_after_message(
                    with_node=to_node,
                    message_content=message,
                    direction="sent",
                    message_id=result['message_id'],
                    conversation_id=conversation_id
                )

                # Store in enhanced memory for learning
                if ENHANCED_MEMORY_ENABLED:
                    memory_integration.store_conversation_message(
                        message_id=result['message_id'],
                        from_node=NODE_CONFIG['node_id'],
                        to_node=to_node,
                        content=message,
                        conversation_id=conversation_id,
                        timestamp=result['timestamp'],
                        metadata={"direction": "outgoing", "channels": channels}
                    )

                response = {
                    "success": True,
                    "message_id": result['message_id'],
                    "delivered_via": channels,
                    "timestamp": result['timestamp'],
                    "stored_in_memory": ENHANCED_MEMORY_ENABLED,
                    "conversation_tracked": True,
                    "message": f"✓ Message delivered to {to_node} via: {', '.join(channels)}"
                }
            else:
                response = {
                    "success": False,
                    "message": f"✗ Failed to deliver message to {to_node}",
                    "delivery_attempts": result['delivery_channels']
                }

            return [types.TextContent(
                type="text",
                text=json.dumps(response, indent=2)
            )]

        elif name == "get_conversation_history":
            with_node = arguments["with_node"]
            limit = arguments.get("limit", 50)

            history = chat_client.get_conversation_history(with_node, limit)

            if not history:
                response = {
                    "conversation_with": with_node,
                    "message_count": 0,
                    "messages": [],
                    "note": "No conversation history found"
                }
            else:
                response = {
                    "conversation_with": with_node,
                    "message_count": len(history),
                    "messages": history
                }

            return [types.TextContent(
                type="text",
                text=json.dumps(response, indent=2)
            )]

        elif name == "get_my_active_conversations":
            # Get active conversations from database
            import sqlite3
            chat_db = Path(NODE_CONFIG['storage']['base']) / "databases" / "cluster" / "node_chat.db"

            if not chat_db.exists():
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"conversations": [], "count": 0, "note": "No conversations yet"}, indent=2)
                )]

            conn = sqlite3.connect(str(chat_db))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT c.conversation_id, c.participants, c.last_activity,
                       COUNT(m.message_id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.conversation_id = m.conversation_id
                WHERE c.active = 1 AND c.participants LIKE ?
                GROUP BY c.conversation_id
                ORDER BY c.last_activity DESC
            """, (f'%{NODE_CONFIG["node_id"]}%',))

            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    'conversation_id': row[0],
                    'participants': row[1].split(','),
                    'last_activity': row[2],
                    'message_count': row[3]
                })

            conn.close()

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "node_id": NODE_CONFIG['node_id'],
                    "conversations": conversations,
                    "count": len(conversations)
                }, indent=2)
            )]

        elif name == "check_for_new_messages":
            mark_as_read = arguments.get("mark_as_read", True)

            # Query for unread messages
            import sqlite3
            chat_db = Path(NODE_CONFIG['storage']['base']) / "databases" / "cluster" / "node_chat.db"

            if not chat_db.exists():
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"new_messages": [], "count": 0}, indent=2)
                )]

            conn = sqlite3.connect(str(chat_db))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT message_id, conversation_id, from_node, content, timestamp
                FROM messages
                WHERE to_node = ? AND read = 0
                ORDER BY timestamp DESC
                LIMIT 50
            """, (NODE_CONFIG['node_id'],))

            new_messages = []
            message_ids = []
            for row in cursor.fetchall():
                new_messages.append({
                    'message_id': row[0],
                    'conversation_id': row[1],
                    'from_node': row[2],
                    'content': row[3],
                    'timestamp': row[4]
                })
                message_ids.append(row[0])

            # Mark as read if requested
            if mark_as_read and message_ids:
                placeholders = ','.join('?' * len(message_ids))
                cursor.execute(f"""
                    UPDATE messages
                    SET read = 1, read_at = CURRENT_TIMESTAMP
                    WHERE message_id IN ({placeholders})
                """, message_ids)
                conn.commit()

            conn.close()

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "node_id": NODE_CONFIG['node_id'],
                    "new_messages": new_messages,
                    "count": len(new_messages),
                    "marked_as_read": mark_as_read
                }, indent=2)
            )]

        elif name == "broadcast_to_cluster":
            message = arguments["message"]
            priority = arguments.get("priority", "normal")

            # Get all nodes except self
            from node_chat_client import NodeChatClient
            client = NodeChatClient(NODE_CONFIG['node_id'], NODE_CONFIG['storage']['base'])
            all_nodes = list(client.cluster_nodes.keys())
            target_nodes = [n for n in all_nodes if n != NODE_CONFIG['node_id']]

            # Send to each node
            results = {}
            for node in target_nodes:
                result = client.send_message(node, f"[BROADCAST] {message}")
                results[node] = {
                    "delivered": result['success'],
                    "channels": [k for k, v in result['delivery_channels'].items() if v.get('success')]
                }

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "broadcast_to": target_nodes,
                    "message": message,
                    "priority": priority,
                    "results": results
                }, indent=2)
            )]

        elif name == "get_my_awareness":
            # Get complete self-awareness
            awareness = {
                "identity": {
                    "node_id": persona.node_id,
                    "role": persona.role,
                    "capabilities": persona.capabilities,
                    "specialties": persona.specialties,
                    "personality": persona.personality if hasattr(persona, 'personality') else {}
                },
                "environmental": persona.get_environmental_awareness(),
                "situational": persona.get_situational_awareness(),
                "introduction": persona.introduce()
            }

            return [types.TextContent(
                type="text",
                text=persona.format_awareness_summary()
            )]

        elif name == "get_cluster_awareness":
            # Get awareness of all cluster nodes
            cluster_info = {"nodes": {}, "cluster_health": persona._get_cluster_health()}

            for node_id, node_config in chat_client.cluster_nodes.items():
                cluster_info["nodes"][node_id] = {
                    "node_id": node_id,
                    "role": node_config['role'],
                    "specialties": node_config.get('specialties', []),
                    "capabilities": node_config.get('capabilities', []),
                    "os": node_config['os'],
                    "arch": node_config['arch'],
                    "ip": node_config['ip'],
                    "storage_base": node_config['storage_base']
                }

                # Check if online (skip self)
                if node_id != persona.node_id:
                    try:
                        result = subprocess.run(
                            ['ping', '-c', '1', '-W', '1', node_config['ip']],
                            capture_output=True, timeout=2
                        )
                        cluster_info["nodes"][node_id]["status"] = "online" if result.returncode == 0 else "offline"
                    except:
                        cluster_info["nodes"][node_id]["status"] = "unknown"
                else:
                    cluster_info["nodes"][node_id]["status"] = "local"

            return [types.TextContent(
                type="text",
                text=json.dumps(cluster_info, indent=2)
            )]

        elif name == "get_node_status":
            target_node = arguments["node_id"]

            if target_node == persona.node_id:
                # Return self-awareness
                return [types.TextContent(
                    type="text",
                    text=persona.format_awareness_summary()
                )]

            # Get status of other node
            if target_node not in chat_client.cluster_nodes:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"error": f"Unknown node: {target_node}"}, indent=2)
                )]

            node_config = chat_client.cluster_nodes[target_node]
            node_status = {
                "node_id": target_node,
                "role": node_config['role'],
                "specialties": node_config.get('specialties', []),
                "capabilities": node_config.get('capabilities', []),
                "os": node_config['os'],
                "arch": node_config['arch'],
                "storage_base": node_config['storage_base']
            }

            # Check if reachable
            try:
                import subprocess
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '1', node_config['ip']],
                    capture_output=True, timeout=2
                )
                node_status["reachable"] = result.returncode == 0
                node_status["status"] = "online" if result.returncode == 0 else "offline"
            except:
                node_status["reachable"] = False
                node_status["status"] = "unknown"

            # Try to get remote status via HTTP API if available
            if node_status["reachable"]:
                try:
                    response = requests.get(f"http://{node_config['ip']}:5200/api/chat/status", timeout=3)
                    if response.status_code == 200:
                        node_status["remote_status"] = response.json()
                except:
                    pass

            return [types.TextContent(
                type="text",
                text=json.dumps(node_status, indent=2)
            )]

        elif name == "watch_cluster_conversations":
            mode = arguments.get("mode", "recent")
            limit = arguments.get("limit", 20)

            chat_db = Path(NODE_CONFIG['storage']['base']) / "databases" / "cluster" / "node_chat.db"

            if not chat_db.exists():
                return [types.TextContent(
                    type="text",
                    text="No conversations yet. Nodes haven't started chatting."
                )]

            conn = sqlite3.connect(str(chat_db))
            cursor = conn.cursor()

            if mode == "stats":
                # Show statistics
                cursor.execute("SELECT COUNT(*) FROM messages")
                total_messages = cursor.fetchone()[0]

                cursor.execute("""
                    SELECT from_node, COUNT(*) as count
                    FROM messages
                    GROUP BY from_node
                    ORDER BY count DESC
                """)
                by_node = cursor.fetchall()

                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN delivered = 1 THEN 1 ELSE 0 END) as delivered
                    FROM messages
                """)
                total, delivered = cursor.fetchone()
                delivery_rate = (delivered / total * 100) if total > 0 else 0

                stats_text = f"""
Cluster Communication Statistics
{'='*60}

Total Messages: {total_messages}
Delivery Rate: {delivery_rate:.1f}%

Messages by Node:
"""
                for node, count in by_node:
                    stats_text += f"  • {node}: {count}\n"

                conn.close()
                return [types.TextContent(type="text", text=stats_text)]

            else:
                # Show recent messages
                cursor.execute("""
                    SELECT message_id, from_node, to_node, content, timestamp, delivered, read
                    FROM messages
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

                messages = []
                for row in cursor.fetchall():
                    messages.append({
                        'message_id': row[0],
                        'from_node': row[1],
                        'to_node': row[2],
                        'content': row[3],
                        'timestamp': row[4],
                        'delivered': bool(row[5]),
                        'read': bool(row[6])
                    })

                conn.close()

                if not messages:
                    return [types.TextContent(
                        type="text",
                        text="No messages yet. Use send_message_to_node() to start a conversation!"
                    )]

                # Format for display
                conversation_text = f"""
Cluster Conversations (Last {len(messages)} messages)
{'='*60}

"""
                for msg in reversed(messages):  # Chronological order
                    ts = msg['timestamp'][:19].replace('T', ' ')
                    direction = "→" if msg['from_node'] == NODE_CONFIG['node_id'] else "←" if msg['to_node'] == NODE_CONFIG['node_id'] else "↔"
                    status = "✓✓" if msg['read'] else "✓" if msg['delivered'] else "○"

                    conversation_text += f"[{ts}] {msg['from_node']} {direction} {msg['to_node']}: {msg['content']} {status}\n"

                conversation_text += f"""
{'='*60}
Legend: → outgoing, ← incoming, ↔ between other nodes
        ✓✓ read, ✓ delivered, ○ pending
"""

                return [types.TextContent(type="text", text=conversation_text)]

        # AGI Orchestration Tools
        elif name == "view_conversations_threaded":
            limit = arguments.get("limit", 20)
            mode = arguments.get("mode", "threaded")

            viewer = EnhancedConversationViewer(NODE_CONFIG['storage']['base'])
            result = viewer.get_conversations(limit=limit, mode=mode)

            return [types.TextContent(type="text", text=result)]

        elif name == "decompose_goal":
            goal = arguments["goal"]

            orchestrator = AGIOrchestrator(NODE_CONFIG['storage']['base'])
            result = orchestrator.decompose_goal(goal, NODE_CONFIG['node_id'])

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "initiate_research_pipeline":
            research_topic = arguments["research_topic"]

            orchestrator = AGIOrchestrator(NODE_CONFIG['storage']['base'])
            result = orchestrator.coordinate_research_implementation(research_topic)

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "start_improvement_cycle":
            target_metric = arguments["target_metric"]

            orchestrator = AGIOrchestrator(NODE_CONFIG['storage']['base'])
            result = orchestrator.initiate_self_improvement_cycle(target_metric)

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "get_agi_system_health":
            orchestrator = AGIOrchestrator(NODE_CONFIG['storage']['base'])
            result = orchestrator.get_system_health()

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "monitor_autonomous_activities":
            orchestrator = AGIOrchestrator(NODE_CONFIG['storage']['base'])
            result = orchestrator.monitor_autonomous_activities()

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        elif name == "search_conversation_memory":
            query = arguments["query"]
            limit = arguments.get("limit", 10)
            from_node = arguments.get("from_node")

            if not ENHANCED_MEMORY_ENABLED:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "Enhanced memory not enabled",
                        "hint": "Set ENHANCED_MEMORY_INTEGRATION=true in environment"
                    }, indent=2)
                )]

            results = memory_integration.search_conversations(
                query=query,
                limit=limit,
                from_node=from_node
            )

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "query": query,
                    "results_count": len(results),
                    "results": results
                }, indent=2)
            )]

        elif name == "get_memory_stats":
            stats = memory_integration.get_stats()
            stats["node_id"] = NODE_CONFIG['node_id']

            return [types.TextContent(
                type="text",
                text=json.dumps(stats, indent=2)
            )]

        # ===== NEW CONVERSATION CONTEXT TOOLS =====

        elif name == "prepare_conversation_context":
            with_node = arguments["with_node"]
            include_history = arguments.get("include_history", True)
            max_history = arguments.get("max_history", 20)

            # Get full context for conversation
            context = context_manager.get_conversation_context(
                with_node=with_node,
                include_persona=True,
                include_system_state=True,
                include_history=include_history,
                max_history_messages=max_history
            )

            # Format for easy reading
            formatted = context_manager.format_context_for_prompt(context)

            return [types.TextContent(
                type="text",
                text=formatted + "\n\n" + json.dumps(context, indent=2, default=str)
            )]

        elif name == "start_conversation_with_context":
            to_node = arguments["to_node"]
            message = arguments["message"]
            topic = arguments.get("topic", "general")

            # First, get context
            context = context_manager.get_conversation_context(
                with_node=to_node,
                include_persona=True,
                include_system_state=True,
                include_history=True
            )

            # Send the message
            result = chat_client.send_message(to_node, message)

            if result['success']:
                channels = [k for k, v in result['delivery_channels'].items() if v.get('success')]

                # Update conversation context
                context_manager.update_after_message(
                    with_node=to_node,
                    message_content=message,
                    direction="sent",
                    message_id=result['message_id'],
                    conversation_id=result.get('conversation_id', f"{NODE_CONFIG['node_id']}-{to_node}-{topic}")
                )

                # Store in enhanced memory if available
                if ENHANCED_MEMORY_ENABLED:
                    memory_integration.store_conversation_message(
                        message_id=result['message_id'],
                        from_node=NODE_CONFIG['node_id'],
                        to_node=to_node,
                        content=message,
                        conversation_id=result.get('conversation_id', 'default'),
                        timestamp=result['timestamp'],
                        metadata={"direction": "outgoing", "channels": channels, "topic": topic}
                    )

                response = {
                    "success": True,
                    "message_id": result['message_id'],
                    "delivered_via": channels,
                    "timestamp": result['timestamp'],
                    "context_used": {
                        "my_persona": context.get("my_persona", {}).get("name"),
                        "relationship_exists": context.get("relationship", {}).get("relationship_exists", False),
                        "past_messages": len(context.get("conversation_history", [])),
                        "known_facts": len(context.get("known_facts_about_them", []))
                    },
                    "message": f"Message sent to {to_node} with full context awareness"
                }
            else:
                response = {
                    "success": False,
                    "message": f"Failed to deliver message to {to_node}",
                    "delivery_attempts": result['delivery_channels']
                }

            return [types.TextContent(
                type="text",
                text=json.dumps(response, indent=2)
            )]

        elif name == "remember_fact_about_node":
            about_node = arguments["about_node"]
            fact_type = arguments["fact_type"]
            content = arguments["content"]
            confidence = arguments.get("confidence", 0.8)

            context_manager.add_fact_about_node(
                about_node=about_node,
                fact_type=fact_type,
                fact_content=content,
                confidence=confidence
            )

            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "stored_fact": {
                        "about": about_node,
                        "type": fact_type,
                        "content": content,
                        "confidence": confidence
                    },
                    "message": f"Remembered: {about_node} - {fact_type}: {content}"
                }, indent=2)
            )]

        elif name == "get_relationship_summary":
            with_node = arguments["with_node"]

            # Get relationship and facts
            relationship = context_manager._get_relationship(with_node)
            facts = context_manager._get_facts_about_node(with_node)
            highlights = context_manager._get_relevant_highlights(with_node, limit=5)
            history = context_manager._get_conversation_history(with_node, limit=5)

            summary = {
                "with_node": with_node,
                "my_node": NODE_CONFIG['node_id'],
                "relationship": relationship,
                "known_facts": facts,
                "recent_highlights": highlights,
                "recent_messages": len(history),
                "latest_message": history[-1] if history else None
            }

            # Format nicely
            formatted = f"""
RELATIONSHIP SUMMARY: {NODE_CONFIG['node_id']} <-> {with_node}
{'='*60}

"""
            if relationship.get("relationship_exists"):
                formatted += f"""HISTORY:
  Total messages: {relationship.get('total_messages', 0)}
  First conversation: {relationship.get('first_conversation', 'unknown')}
  Last interaction: {relationship.get('last_interaction', 'unknown')}

"""
                if relationship.get("collaboration_areas"):
                    formatted += f"  Collaborated on: {', '.join(relationship['collaboration_areas'])}\n"
                if relationship.get("notes"):
                    formatted += f"  Notes: {relationship['notes']}\n"
            else:
                formatted += "HISTORY: No prior conversations recorded.\n"

            if facts:
                formatted += f"\nKNOWN FACTS ABOUT {with_node.upper()}:\n"
                for fact in facts:
                    formatted += f"  [{fact['type']}] {fact['content']} (confidence: {fact['confidence']})\n"

            if highlights:
                formatted += f"\nIMPORTANT PAST MOMENTS:\n"
                for h in highlights:
                    formatted += f"  - ({h['reason']}) {h['content'][:80]}...\n"

            formatted += f"\n{'='*60}"

            return [types.TextContent(
                type="text",
                text=formatted + "\n\n" + json.dumps(summary, indent=2, default=str)
            )]

        elif name == "summarize_conversation":
            with_node = arguments["with_node"]
            key_topics = arguments.get("key_topics", [])
            key_decisions = arguments.get("key_decisions", [])
            summary = arguments.get("summary", "")

            # Get most recent conversation ID with this node
            history = context_manager._get_conversation_history(with_node, limit=1)
            if history:
                # Use a generated conversation ID based on today's date
                from datetime import date
                conversation_id = f"{NODE_CONFIG['node_id']}-{with_node}-{date.today().isoformat()}"

                context_manager.update_conversation_summary(
                    with_node=with_node,
                    conversation_id=conversation_id,
                    key_topics=key_topics if key_topics else None,
                    key_decisions=key_decisions if key_decisions else None,
                    summary_text=summary if summary else None
                )

                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "conversation_id": conversation_id,
                        "updated": {
                            "key_topics": key_topics,
                            "key_decisions": key_decisions,
                            "summary": summary[:100] + "..." if len(summary) > 100 else summary
                        },
                        "message": f"Conversation summary updated for {with_node}"
                    }, indent=2)
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "message": f"No conversation history found with {with_node}"
                    }, indent=2)
                )]

        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        logger.error(f"Error in {name}: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Main entry point"""
    logger.info(f"Starting Node Chat MCP Server for {NODE_CONFIG['node_id']}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="node-chat",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
