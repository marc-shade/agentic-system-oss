#!/usr/bin/env python3
"""
Node Chat Integration for Cluster Execution MCP
================================================

Provides inter-node agent communication and AGI coordination tools.
Merged from node-chat-mcp to reduce MCP server count.

24 tools for cluster communication:
- Messaging: send_message_to_node, get_conversation_history, check_for_new_messages, broadcast_to_cluster
- Awareness: get_my_awareness, get_cluster_awareness, get_node_status
- Conversation: watch_cluster_conversations, view_conversations_threaded, prepare_conversation_context
- AGI: decompose_goal, initiate_research_pipeline, start_improvement_cycle
- Memory: search_conversation_memory, get_memory_stats, remember_fact_about_node
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from mcp.types import Tool, TextContent

logger = logging.getLogger("node-chat-integration")

# Add cluster-deployment to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "cluster-deployment"))

# Import dependencies
try:
    from node_chat_client import NodeChatClient
    from node_persona import get_persona
    from enhanced_conversation_viewer import EnhancedConversationViewer
    from agi_orchestrator import AGIOrchestrator
    NODE_CHAT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"node-chat dependencies not available: {e}")
    NODE_CHAT_AVAILABLE = False

# Import local modules
try:
    from memory_integration import get_memory_integration, ENHANCED_MEMORY_ENABLED
    from conversation_context import get_context_manager, ConversationContextManager
    LOCAL_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Local modules not available: {e}")
    LOCAL_MODULES_AVAILABLE = False


class NodeChatServer:
    """Handles node chat operations for the cluster."""

    VALID_NODES = ["builder", "orchestrator", "researcher", "ai-inference", "small-inference", "sentinel"]

    def __init__(self):
        self.node_id = os.environ.get("NODE_ID", self._detect_node_id())
        self.storage_base = os.environ.get("STORAGE_BASE", "/Volumes/SSDRAID0/agentic-system")

        # Initialize clients if available
        self.chat_client = None
        self.persona = None
        self.viewer = None
        self.agi_orchestrator = None
        self.memory_integration = None
        self.context_manager = None

        if NODE_CHAT_AVAILABLE:
            storage_path = f"{self.storage_base}/databases/cluster"
            self.chat_client = NodeChatClient(self.node_id, self.storage_base)
            self.persona = get_persona(self.node_id, self.storage_base)
            self.viewer = EnhancedConversationViewer(self.storage_base)
            self.agi_orchestrator = AGIOrchestrator(self.storage_base)

        if LOCAL_MODULES_AVAILABLE:
            storage_path = f"{self.storage_base}/databases/cluster"
            self.memory_integration = get_memory_integration(storage_path, self.node_id)
            self.context_manager = get_context_manager(storage_path, self.node_id)

    def _detect_node_id(self) -> str:
        """Detect node ID from hostname."""
        import socket
        hostname = socket.gethostname().lower()
        if "studio" in hostname:
            return "orchestrator"
        elif "air" in hostname:
            return "researcher"
        elif "macpro" in hostname or "builder" in hostname:
            return "builder"
        return "orchestrator"

    async def send_message_to_node(self, to_node: str, message: str) -> Dict[str, Any]:
        """Send a chat message to another node's AI persona."""
        if not NODE_CHAT_AVAILABLE:
            return {"error": "Node chat dependencies not available"}

        if to_node not in self.VALID_NODES:
            return {"error": f"Invalid node: {to_node}. Valid: {self.VALID_NODES}"}

        result = self.chat_client.send_message(to_node, message)

        # Store in memory if enabled
        if self.memory_integration and ENHANCED_MEMORY_ENABLED:
            self.memory_integration.store_conversation_message(
                message_id=result.get("message_id", ""),
                from_node=self.node_id,
                to_node=to_node,
                content=message,
                conversation_id=f"{self.node_id}_{to_node}",
                timestamp=datetime.utcnow().isoformat()
            )

        return result

    async def get_conversation_history(self, with_node: str, limit: int = 50) -> Dict[str, Any]:
        """Get chat history with another node."""
        if not NODE_CHAT_AVAILABLE:
            return {"error": "Node chat dependencies not available"}

        if with_node not in self.VALID_NODES:
            return {"error": f"Invalid node: {with_node}. Valid: {self.VALID_NODES}"}

        return self.chat_client.get_conversation_history(with_node, limit)

    async def get_my_active_conversations(self) -> Dict[str, Any]:
        """Get all active conversations this node is participating in."""
        if not NODE_CHAT_AVAILABLE:
            return {"error": "Node chat dependencies not available"}

        return self.chat_client.get_active_conversations()

    async def check_for_new_messages(self, mark_as_read: bool = True) -> Dict[str, Any]:
        """Check if other nodes have sent messages to this node."""
        if not NODE_CHAT_AVAILABLE:
            return {"error": "Node chat dependencies not available"}

        return self.chat_client.check_for_messages(mark_as_read)

    async def broadcast_to_cluster(self, message: str, priority: str = "normal") -> Dict[str, Any]:
        """Send a message to all nodes in the cluster."""
        if not NODE_CHAT_AVAILABLE:
            return {"error": "Node chat dependencies not available"}

        return self.chat_client.broadcast(message, priority)

    async def get_my_awareness(self) -> Dict[str, Any]:
        """Get complete self-awareness of this node's identity and state."""
        if not NODE_CHAT_AVAILABLE:
            return {"error": "Node chat dependencies not available"}

        awareness = {
            "node_id": self.node_id,
            "persona": self.persona.to_dict() if self.persona else None,
            "capabilities": self._get_node_capabilities(),
            "status": self._get_node_status()
        }
        return awareness

    def _get_node_capabilities(self) -> List[str]:
        """Get this node's capabilities."""
        caps = ["messaging", "conversation_history", "cluster_awareness"]
        if self.agi_orchestrator:
            caps.extend(["goal_decomposition", "research_pipeline", "improvement_cycle"])
        if self.memory_integration and ENHANCED_MEMORY_ENABLED:
            caps.append("conversation_memory")
        return caps

    def _get_node_status(self) -> Dict[str, Any]:
        """Get current node status."""
        import psutil
        return {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def get_cluster_awareness(self) -> Dict[str, Any]:
        """Get awareness of all nodes in the cluster."""
        if not NODE_CHAT_AVAILABLE:
            return {"error": "Node chat dependencies not available"}

        return self.chat_client.get_cluster_status()

    async def get_node_status(self, node_id: str) -> Dict[str, Any]:
        """Get detailed status of a specific node."""
        if not NODE_CHAT_AVAILABLE:
            return {"error": "Node chat dependencies not available"}

        if node_id not in self.VALID_NODES:
            return {"error": f"Invalid node: {node_id}. Valid: {self.VALID_NODES}"}

        return self.chat_client.get_node_status(node_id)

    async def watch_cluster_conversations(self, limit: int = 20, mode: str = "recent") -> Dict[str, Any]:
        """Monitor all cluster conversations in real-time."""
        if not NODE_CHAT_AVAILABLE or not self.viewer:
            return {"error": "Node chat dependencies not available"}

        if mode == "stats":
            return self.viewer.get_conversation_stats()
        elif mode == "live_snapshot":
            return self.viewer.get_live_snapshot(limit)
        else:  # recent
            return self.viewer.get_recent_conversations(limit)

    async def view_conversations_threaded(self, limit: int = 20, mode: str = "threaded") -> Dict[str, Any]:
        """View cluster conversations in rich threaded format."""
        if not NODE_CHAT_AVAILABLE or not self.viewer:
            return {"error": "Node chat dependencies not available"}

        return self.viewer.get_threaded_view(limit, mode)

    async def decompose_goal(self, goal: str) -> Dict[str, Any]:
        """AGI: Decompose a complex goal into coordinated multi-node tasks."""
        if not NODE_CHAT_AVAILABLE or not self.agi_orchestrator:
            return {"error": "AGI orchestrator not available"}

        return await self.agi_orchestrator.decompose_goal(goal)

    async def initiate_research_pipeline(self, research_topic: str) -> Dict[str, Any]:
        """AGI: Start autonomous research-to-implementation pipeline."""
        if not NODE_CHAT_AVAILABLE or not self.agi_orchestrator:
            return {"error": "AGI orchestrator not available"}

        return await self.agi_orchestrator.initiate_research_pipeline(research_topic)

    async def start_improvement_cycle(self, target_metric: str) -> Dict[str, Any]:
        """AGI: Initiate recursive self-improvement cycle."""
        if not NODE_CHAT_AVAILABLE or not self.agi_orchestrator:
            return {"error": "AGI orchestrator not available"}

        return await self.agi_orchestrator.start_improvement_cycle(target_metric)

    async def get_agi_system_health(self) -> Dict[str, Any]:
        """AGI: Get overall AGI system health and status."""
        if not NODE_CHAT_AVAILABLE or not self.agi_orchestrator:
            return {"error": "AGI orchestrator not available"}

        return await self.agi_orchestrator.get_system_health()

    async def monitor_autonomous_activities(self) -> Dict[str, Any]:
        """AGI: Monitor what nodes are doing autonomously."""
        if not NODE_CHAT_AVAILABLE or not self.agi_orchestrator:
            return {"error": "AGI orchestrator not available"}

        return await self.agi_orchestrator.monitor_activities()

    async def search_conversation_memory(self, query: str, limit: int = 10, from_node: Optional[str] = None) -> Dict[str, Any]:
        """Search past node conversations using semantic similarity."""
        if not self.memory_integration or not ENHANCED_MEMORY_ENABLED:
            return {"error": "Enhanced memory integration not available"}

        return self.memory_integration.search_conversations(query, limit, from_node)

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about node conversation memory storage."""
        if not self.memory_integration:
            return {"enabled": False, "reason": "Memory integration not initialized"}

        return self.memory_integration.get_stats()

    async def prepare_conversation_context(self, with_node: str, include_history: bool = True, max_history: int = 20) -> Dict[str, Any]:
        """Get complete context before starting a conversation with another node."""
        if not NODE_CHAT_AVAILABLE:
            return {"error": "Node chat dependencies not available"}

        if with_node not in self.VALID_NODES:
            return {"error": f"Invalid node: {with_node}. Valid: {self.VALID_NODES}"}

        context = {
            "my_persona": self.persona.to_dict() if self.persona else None,
            "my_status": self._get_node_status(),
            "with_node": with_node
        }

        if self.context_manager:
            full_context = self.context_manager.get_conversation_context(with_node)
            context.update(full_context)

        if include_history:
            history = await self.get_conversation_history(with_node, max_history)
            context["history"] = history

        return context

    async def start_conversation_with_context(self, to_node: str, message: str, topic: Optional[str] = None) -> Dict[str, Any]:
        """Start a new conversation with another node, automatically loading context."""
        context = await self.prepare_conversation_context(to_node)
        result = await self.send_message_to_node(to_node, message)

        if self.context_manager and topic:
            self.context_manager.update_after_message(to_node, message, topic)

        return {
            "context_used": context,
            "message_result": result
        }

    async def remember_fact_about_node(self, about_node: str, fact_type: str, content: str, confidence: float = 0.8) -> Dict[str, Any]:
        """Store a learned fact about another node for future reference."""
        if not self.context_manager:
            return {"error": "Context manager not available"}

        if about_node not in self.VALID_NODES:
            return {"error": f"Invalid node: {about_node}. Valid: {self.VALID_NODES}"}

        valid_types = ["capability", "preference", "limitation", "expertise", "communication_style", "availability_pattern"]
        if fact_type not in valid_types:
            return {"error": f"Invalid fact_type: {fact_type}. Valid: {valid_types}"}

        return self.context_manager.add_fact_about_node(about_node, fact_type, content, confidence)

    async def get_relationship_summary(self, with_node: str) -> Dict[str, Any]:
        """Get a summary of your relationship with another node."""
        if not self.context_manager:
            return {"error": "Context manager not available"}

        if with_node not in self.VALID_NODES:
            return {"error": f"Invalid node: {with_node}. Valid: {self.VALID_NODES}"}

        return self.context_manager.get_relationship_summary(with_node)

    async def summarize_conversation(self, with_node: str, key_topics: List[str] = None, key_decisions: List[str] = None, summary: str = None) -> Dict[str, Any]:
        """Update the summary of a conversation with key topics and decisions."""
        if not self.context_manager:
            return {"error": "Context manager not available"}

        if with_node not in self.VALID_NODES:
            return {"error": f"Invalid node: {with_node}. Valid: {self.VALID_NODES}"}

        return self.context_manager.summarize_conversation(
            with_node,
            key_topics=key_topics or [],
            key_decisions=key_decisions or [],
            summary=summary or ""
        )


# Tool definitions for MCP
NODE_CHAT_TOOLS = [
    Tool(
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
                    "enum": ["builder", "orchestrator", "researcher", "ai-inference", "small-inference", "sentinel"]
                },
                "message": {
                    "type": "string",
                    "description": "Message content to send"
                }
            },
            "required": ["to_node", "message"]
        }
    ),
    Tool(
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
                    "enum": ["builder", "orchestrator", "researcher", "ai-inference", "small-inference", "sentinel"]
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
    Tool(
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
    Tool(
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
    Tool(
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
    Tool(
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
    Tool(
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
    Tool(
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
                    "enum": ["builder", "orchestrator", "researcher", "ai-inference", "small-inference", "sentinel"]
                }
            },
            "required": ["node_id"]
        }
    ),
    Tool(
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
                "limit": {
                    "type": "integer",
                    "description": "Number of recent messages to show (default: 20)",
                    "default": 20
                },
                "mode": {
                    "type": "string",
                    "description": "Display mode",
                    "enum": ["recent", "live_snapshot", "stats"],
                    "default": "recent"
                }
            },
            "required": []
        }
    ),
    Tool(
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
    Tool(
        name="decompose_goal",
        description="""
            AGI: Decompose a complex goal into coordinated multi-node tasks.

            Analyzes goal requirements and optimally assigns to specialized nodes.
            This enables autonomous distributed problem-solving across the cluster.

            Example: "Optimize memory consolidation to be 10x faster"
            -> Builder: Benchmark performance
            -> Researcher: Find optimization techniques
            -> Orchestrator: Coordinate implementation

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
    Tool(
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
    Tool(
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
    Tool(
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
    Tool(
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
    Tool(
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
                    "enum": ["builder", "orchestrator", "researcher", "ai-inference", "small-inference", "sentinel"]
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
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
    Tool(
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
                    "enum": ["builder", "orchestrator", "researcher", "ai-inference", "small-inference", "sentinel"]
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
    Tool(
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
                    "enum": ["builder", "orchestrator", "researcher", "ai-inference", "small-inference", "sentinel"]
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
    Tool(
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
                    "enum": ["builder", "orchestrator", "researcher", "ai-inference", "small-inference", "sentinel"]
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
    Tool(
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
                    "enum": ["builder", "orchestrator", "researcher", "ai-inference", "small-inference", "sentinel"]
                }
            },
            "required": ["with_node"]
        }
    ),
    Tool(
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
                    "enum": ["builder", "orchestrator", "researcher", "ai-inference", "small-inference", "sentinel"]
                },
                "key_topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Main topics discussed"
                },
                "key_decisions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Decisions or agreements made"
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


# Singleton instance
_node_chat_server: Optional[NodeChatServer] = None


def get_node_chat_server() -> NodeChatServer:
    """Get or create the NodeChatServer singleton."""
    global _node_chat_server
    if _node_chat_server is None:
        _node_chat_server = NodeChatServer()
    return _node_chat_server


def get_node_chat_tools() -> List[Tool]:
    """Return list of node chat Tool definitions."""
    return NODE_CHAT_TOOLS


async def handle_node_chat_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle a node chat tool call."""
    server = get_node_chat_server()

    try:
        if name == "send_message_to_node":
            result = await server.send_message_to_node(
                arguments["to_node"],
                arguments["message"]
            )
        elif name == "get_conversation_history":
            result = await server.get_conversation_history(
                arguments["with_node"],
                arguments.get("limit", 50)
            )
        elif name == "get_my_active_conversations":
            result = await server.get_my_active_conversations()
        elif name == "check_for_new_messages":
            result = await server.check_for_new_messages(
                arguments.get("mark_as_read", True)
            )
        elif name == "broadcast_to_cluster":
            result = await server.broadcast_to_cluster(
                arguments["message"],
                arguments.get("priority", "normal")
            )
        elif name == "get_my_awareness":
            result = await server.get_my_awareness()
        elif name == "get_cluster_awareness":
            result = await server.get_cluster_awareness()
        elif name == "get_node_status":
            result = await server.get_node_status(arguments["node_id"])
        elif name == "watch_cluster_conversations":
            result = await server.watch_cluster_conversations(
                arguments.get("limit", 20),
                arguments.get("mode", "recent")
            )
        elif name == "view_conversations_threaded":
            result = await server.view_conversations_threaded(
                arguments.get("limit", 20),
                arguments.get("mode", "threaded")
            )
        elif name == "decompose_goal":
            result = await server.decompose_goal(arguments["goal"])
        elif name == "initiate_research_pipeline":
            result = await server.initiate_research_pipeline(arguments["research_topic"])
        elif name == "start_improvement_cycle":
            result = await server.start_improvement_cycle(arguments["target_metric"])
        elif name == "get_agi_system_health":
            result = await server.get_agi_system_health()
        elif name == "monitor_autonomous_activities":
            result = await server.monitor_autonomous_activities()
        elif name == "search_conversation_memory":
            result = await server.search_conversation_memory(
                arguments["query"],
                arguments.get("limit", 10),
                arguments.get("from_node")
            )
        elif name == "get_memory_stats":
            result = await server.get_memory_stats()
        elif name == "prepare_conversation_context":
            result = await server.prepare_conversation_context(
                arguments["with_node"],
                arguments.get("include_history", True),
                arguments.get("max_history", 20)
            )
        elif name == "start_conversation_with_context":
            result = await server.start_conversation_with_context(
                arguments["to_node"],
                arguments["message"],
                arguments.get("topic")
            )
        elif name == "remember_fact_about_node":
            result = await server.remember_fact_about_node(
                arguments["about_node"],
                arguments["fact_type"],
                arguments["content"],
                arguments.get("confidence", 0.8)
            )
        elif name == "get_relationship_summary":
            result = await server.get_relationship_summary(arguments["with_node"])
        elif name == "summarize_conversation":
            result = await server.summarize_conversation(
                arguments["with_node"],
                arguments.get("key_topics", []),
                arguments.get("key_decisions", []),
                arguments.get("summary", "")
            )
        else:
            result = {"error": f"Unknown node chat tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    except Exception as e:
        logger.error(f"Error in node chat tool {name}: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


logger.info("Node chat integration loaded (22 tools)")
