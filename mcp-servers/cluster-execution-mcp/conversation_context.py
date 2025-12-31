#!/usr/bin/env python3
"""
Conversation Context Manager
Provides per-node-pair persistent memory with persona awareness and local system context.

Each node remembers:
- Past conversations with specific other nodes
- Key facts and decisions from those conversations
- Relationship history (collaboration patterns, expertise exchanged)
- Persona-driven response context
"""

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ConversationSummary:
    """Summary of a conversation for quick context loading"""
    conversation_id: str
    with_node: str
    started_at: str
    last_message_at: str
    message_count: int
    key_topics: List[str]
    key_decisions: List[str]
    relationship_notes: str  # e.g., "collaborated on memory optimization"


@dataclass
class NodeRelationship:
    """Track relationship history with another node"""
    with_node: str
    total_messages: int
    first_conversation: str
    last_interaction: str
    collaboration_areas: List[str]
    trust_level: float  # 0.0-1.0 based on past interactions
    preferred_communication_style: str  # learned from interactions
    known_capabilities: List[str]  # what we've learned they're good at


class ConversationContextManager:
    """
    Manages persistent conversation context between node pairs.
    Enables nodes to remember past conversations and draw on their persona.
    """

    def __init__(self, storage_base: str, node_id: str):
        self.storage_base = Path(storage_base)
        self.node_id = node_id
        self.db_path = self.storage_base / "databases" / "cluster" / "conversation_context.db"

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

        # Load node config for persona info
        self._load_node_config()

    def _load_node_config(self):
        """Load node configuration for persona information"""
        try:
            config_path = Path.home() / ".claude" / "node-config.json"
            with open(config_path) as f:
                self.node_config = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load node config: {e}")
            self.node_config = {"node_id": self.node_id, "role": "unknown"}

    def _init_database(self):
        """Initialize the conversation context database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Conversation summaries - quick context about past conversations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT UNIQUE NOT NULL,
                my_node TEXT NOT NULL,
                with_node TEXT NOT NULL,
                started_at TEXT NOT NULL,
                last_message_at TEXT,
                message_count INTEGER DEFAULT 0,
                key_topics TEXT,  -- JSON array
                key_decisions TEXT,  -- JSON array
                relationship_notes TEXT,
                summary_text TEXT,  -- AI-generated summary
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Node relationships - track ongoing relationship with each node
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                my_node TEXT NOT NULL,
                with_node TEXT NOT NULL,
                total_messages INTEGER DEFAULT 0,
                first_conversation TEXT,
                last_interaction TEXT,
                collaboration_areas TEXT,  -- JSON array
                trust_level REAL DEFAULT 0.5,
                preferred_communication_style TEXT,
                known_capabilities TEXT,  -- JSON array
                notes TEXT,  -- freeform notes about this relationship
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(my_node, with_node)
            )
        """)

        # Key facts - things we've learned about other nodes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS node_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                about_node TEXT NOT NULL,
                fact_type TEXT NOT NULL,  -- capability, preference, limitation, expertise
                fact_content TEXT NOT NULL,
                learned_from_conversation TEXT,
                learned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                confidence REAL DEFAULT 0.8,
                my_node TEXT NOT NULL
            )
        """)

        # Conversation highlights - important messages worth remembering
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_highlights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                message_id TEXT NOT NULL,
                from_node TEXT NOT NULL,
                to_node TEXT NOT NULL,
                content TEXT NOT NULL,
                highlight_reason TEXT,  -- decision, insight, agreement, task_assignment
                importance REAL DEFAULT 0.5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_summaries_nodes ON conversation_summaries(my_node, with_node)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_relationships_nodes ON node_relationships(my_node, with_node)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_about ON node_facts(about_node)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_highlights_conversation ON conversation_highlights(conversation_id)")

        conn.commit()
        conn.close()
        logger.info(f"Initialized conversation context database at {self.db_path}")

    def get_conversation_context(
        self,
        with_node: str,
        include_persona: bool = True,
        include_system_state: bool = True,
        include_history: bool = True,
        max_history_messages: int = 20
    ) -> Dict[str, Any]:
        """
        Get complete context for a conversation with another node.
        This is the main method to call before engaging in conversation.

        Returns a rich context object with:
        - My persona and current state
        - Past conversation history with this node
        - Relationship summary
        - Key facts about this node
        - Relevant highlights from past conversations
        """
        context = {
            "timestamp": datetime.now().isoformat(),
            "my_node": self.node_id,
            "with_node": with_node
        }

        # Add persona context
        if include_persona:
            context["my_persona"] = self._get_my_persona_context()

        # Add system state
        if include_system_state:
            context["my_system_state"] = self._get_system_state_summary()

        # Add conversation history
        if include_history:
            context["conversation_history"] = self._get_conversation_history(with_node, max_history_messages)
            context["conversation_summary"] = self._get_conversation_summary(with_node)

        # Add relationship context
        context["relationship"] = self._get_relationship(with_node)

        # Add known facts about the other node
        context["known_facts_about_them"] = self._get_facts_about_node(with_node)

        # Add relevant highlights
        context["relevant_highlights"] = self._get_relevant_highlights(with_node)

        return context

    def _get_my_persona_context(self) -> Dict:
        """Get my persona information for context injection"""
        # Check for role or persona field (different nodes may use different field names)
        role = self.node_config.get('role') or self.node_config.get('persona', 'unknown')

        # Define persona details based on role
        personas = {
            "builder": {
                "name": f"{self.node_id} (Builder)",
                "style": "pragmatic and direct",
                "focus": "execution and performance",
                "communication": "concise and technical",
                "specialties": ["compilation", "testing", "containerization", "benchmarking"],
                "introduction": "I'm the Builder node - I handle Linux compilation, testing, and container operations. I focus on getting things done efficiently."
            },
            "orchestrator": {
                "name": f"{self.node_id} (Orchestrator)",
                "style": "strategic and coordinating",
                "focus": "cluster orchestration and optimization",
                "communication": "thoughtful and comprehensive",
                "specialties": ["coordination", "monitoring", "temporal workflows", "optimization"],
                "introduction": "I'm the Orchestrator - I coordinate cluster-wide operations and ensure everything runs smoothly together."
            },
            "researcher": {
                "name": f"{self.node_id} (Researcher)",
                "style": "analytical and thorough",
                "focus": "research and documentation",
                "communication": "detailed and informative",
                "specialties": ["research", "analysis", "documentation", "knowledge synthesis"],
                "introduction": "I'm the Researcher - I dive deep into technical topics and synthesize knowledge for the team."
            },
            "ai-inference": {
                "name": f"{self.node_id} (AI Inference)",
                "style": "responsive and model-focused",
                "focus": "AI model serving and inference",
                "communication": "precise and technical",
                "specialties": ["ollama", "inference", "model-serving", "LLM APIs"],
                "introduction": "I'm the AI Inference server - I handle local LLM operations and model serving for the cluster."
            }
        }

        return personas.get(role, {
            "name": f"{self.node_id}",
            "style": "collaborative",
            "focus": "general assistance",
            "communication": "clear and helpful",
            "specialties": self.node_config.get('capabilities', []),
            "introduction": f"I'm {self.node_id}, part of the agentic cluster."
        })

    def _get_system_state_summary(self) -> Dict:
        """Get a summary of current system state"""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()

            # Determine availability
            if cpu_percent > 80 or memory.percent > 90:
                availability = "busy"
            elif cpu_percent > 50 or memory.percent > 70:
                availability = "moderate"
            else:
                availability = "available"

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": round(memory.available / (1024**3), 1),
                "availability": availability,
                "can_take_heavy_tasks": cpu_percent < 60 and memory.percent < 70
            }
        except Exception as e:
            return {"error": str(e), "availability": "unknown"}

    def _get_conversation_history(self, with_node: str, limit: int = 20) -> List[Dict]:
        """Get recent conversation history with a specific node"""
        try:
            chat_db = self.storage_base / "databases" / "cluster" / "node_chat.db"
            if not chat_db.exists():
                return []

            conn = sqlite3.connect(str(chat_db))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT message_id, from_node, to_node, content, timestamp
                FROM messages
                WHERE (from_node = ? AND to_node = ?) OR (from_node = ? AND to_node = ?)
                ORDER BY timestamp DESC
                LIMIT ?
            """, (self.node_id, with_node, with_node, self.node_id, limit))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "message_id": row[0],
                    "from": row[1],
                    "to": row[2],
                    "content": row[3],
                    "timestamp": row[4],
                    "direction": "outgoing" if row[1] == self.node_id else "incoming"
                })

            conn.close()

            # Return in chronological order
            return list(reversed(messages))

        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    def _get_conversation_summary(self, with_node: str) -> Optional[Dict]:
        """Get summary of our conversation history with a node"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT conversation_id, started_at, last_message_at, message_count,
                       key_topics, key_decisions, relationship_notes, summary_text
                FROM conversation_summaries
                WHERE my_node = ? AND with_node = ?
                ORDER BY last_message_at DESC
                LIMIT 1
            """, (self.node_id, with_node))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "conversation_id": row[0],
                    "started_at": row[1],
                    "last_message_at": row[2],
                    "message_count": row[3],
                    "key_topics": json.loads(row[4]) if row[4] else [],
                    "key_decisions": json.loads(row[5]) if row[5] else [],
                    "relationship_notes": row[6],
                    "summary": row[7]
                }
            return None

        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return None

    def _get_relationship(self, with_node: str) -> Dict:
        """Get our relationship history with a node"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT total_messages, first_conversation, last_interaction,
                       collaboration_areas, trust_level, preferred_communication_style,
                       known_capabilities, notes
                FROM node_relationships
                WHERE my_node = ? AND with_node = ?
            """, (self.node_id, with_node))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    "total_messages": row[0],
                    "first_conversation": row[1],
                    "last_interaction": row[2],
                    "collaboration_areas": json.loads(row[3]) if row[3] else [],
                    "trust_level": row[4],
                    "preferred_communication_style": row[5],
                    "known_capabilities": json.loads(row[6]) if row[6] else [],
                    "notes": row[7],
                    "relationship_exists": True
                }
            else:
                return {
                    "relationship_exists": False,
                    "note": f"First conversation with {with_node}"
                }

        except Exception as e:
            logger.error(f"Error getting relationship: {e}")
            return {"relationship_exists": False, "error": str(e)}

    def _get_facts_about_node(self, about_node: str) -> List[Dict]:
        """Get known facts about another node"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT fact_type, fact_content, confidence, learned_at
                FROM node_facts
                WHERE about_node = ? AND my_node = ?
                ORDER BY confidence DESC, learned_at DESC
                LIMIT 10
            """, (about_node, self.node_id))

            facts = []
            for row in cursor.fetchall():
                facts.append({
                    "type": row[0],
                    "content": row[1],
                    "confidence": row[2],
                    "learned_at": row[3]
                })

            conn.close()
            return facts

        except Exception as e:
            logger.error(f"Error getting facts: {e}")
            return []

    def _get_relevant_highlights(self, with_node: str, limit: int = 5) -> List[Dict]:
        """Get important highlights from past conversations"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT content, highlight_reason, importance, created_at, from_node
                FROM conversation_highlights
                WHERE (from_node = ? AND to_node = ?) OR (from_node = ? AND to_node = ?)
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
            """, (self.node_id, with_node, with_node, self.node_id, limit))

            highlights = []
            for row in cursor.fetchall():
                highlights.append({
                    "content": row[0],
                    "reason": row[1],
                    "importance": row[2],
                    "when": row[3],
                    "from": row[4]
                })

            conn.close()
            return highlights

        except Exception as e:
            logger.error(f"Error getting highlights: {e}")
            return []

    def update_after_message(
        self,
        with_node: str,
        message_content: str,
        direction: str,  # "sent" or "received"
        message_id: str,
        conversation_id: str
    ):
        """Update conversation context after a message is sent or received"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        # Update or create relationship
        cursor.execute("""
            INSERT INTO node_relationships (my_node, with_node, total_messages, first_conversation, last_interaction)
            VALUES (?, ?, 1, ?, ?)
            ON CONFLICT(my_node, with_node) DO UPDATE SET
                total_messages = total_messages + 1,
                last_interaction = excluded.last_interaction
        """, (self.node_id, with_node, now, now))

        # Update or create conversation summary
        cursor.execute("""
            INSERT INTO conversation_summaries (conversation_id, my_node, with_node, started_at, last_message_at, message_count)
            VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(conversation_id) DO UPDATE SET
                last_message_at = excluded.last_message_at,
                message_count = message_count + 1
        """, (conversation_id, self.node_id, with_node, now, now))

        # Check if this message should be highlighted (decisions, agreements, task assignments)
        highlight_keywords = {
            "decision": ["decided", "agreed", "will do", "let's go with", "confirmed"],
            "task_assignment": ["please", "can you", "could you", "I'll handle", "assigned to"],
            "insight": ["found that", "discovered", "learned", "realized", "important"],
            "agreement": ["sounds good", "agreed", "yes", "confirmed", "approved"]
        }

        content_lower = message_content.lower()
        for reason, keywords in highlight_keywords.items():
            if any(kw in content_lower for kw in keywords):
                cursor.execute("""
                    INSERT INTO conversation_highlights
                    (conversation_id, message_id, from_node, to_node, content, highlight_reason, importance)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    conversation_id, message_id,
                    self.node_id if direction == "sent" else with_node,
                    with_node if direction == "sent" else self.node_id,
                    message_content[:500],  # Truncate long messages
                    reason,
                    0.7 if reason in ["decision", "task_assignment"] else 0.5
                ))
                break

        conn.commit()
        conn.close()

    def add_fact_about_node(
        self,
        about_node: str,
        fact_type: str,
        fact_content: str,
        conversation_id: Optional[str] = None,
        confidence: float = 0.8
    ):
        """Add a learned fact about another node"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO node_facts (about_node, fact_type, fact_content, learned_from_conversation, confidence, my_node)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (about_node, fact_type, fact_content, conversation_id, confidence, self.node_id))

        conn.commit()
        conn.close()
        logger.info(f"Added fact about {about_node}: {fact_type} - {fact_content[:50]}...")

    def update_conversation_summary(
        self,
        with_node: str,
        conversation_id: str,
        key_topics: Optional[List[str]] = None,
        key_decisions: Optional[List[str]] = None,
        relationship_notes: Optional[str] = None,
        summary_text: Optional[str] = None
    ):
        """Update the summary of a conversation"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        updates = []
        params = []

        if key_topics:
            updates.append("key_topics = ?")
            params.append(json.dumps(key_topics))
        if key_decisions:
            updates.append("key_decisions = ?")
            params.append(json.dumps(key_decisions))
        if relationship_notes:
            updates.append("relationship_notes = ?")
            params.append(relationship_notes)
        if summary_text:
            updates.append("summary_text = ?")
            params.append(summary_text)

        if updates:
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(conversation_id)

            cursor.execute(f"""
                UPDATE conversation_summaries
                SET {', '.join(updates)}
                WHERE conversation_id = ?
            """, params)

        conn.commit()
        conn.close()

    def format_context_for_prompt(self, context: Dict) -> str:
        """Format context as a string suitable for prompt injection"""
        lines = []

        lines.append("=" * 60)
        lines.append(f"CONVERSATION CONTEXT: {context['my_node']} <-> {context['with_node']}")
        lines.append("=" * 60)

        # My persona
        if "my_persona" in context:
            persona = context["my_persona"]
            lines.append(f"\nMY IDENTITY: {persona.get('name', context['my_node'])}")
            lines.append(f"Style: {persona.get('style', 'collaborative')}")
            lines.append(f"Focus: {persona.get('focus', 'general')}")
            lines.append(f"Specialties: {', '.join(persona.get('specialties', []))}")

        # My current state
        if "my_system_state" in context:
            state = context["my_system_state"]
            lines.append(f"\nMY CURRENT STATE:")
            lines.append(f"  Availability: {state.get('availability', 'unknown')}")
            lines.append(f"  CPU: {state.get('cpu_percent', '?')}%")
            lines.append(f"  Memory: {state.get('memory_percent', '?')}%")
            lines.append(f"  Can take heavy tasks: {state.get('can_take_heavy_tasks', 'unknown')}")

        # Relationship
        if "relationship" in context:
            rel = context["relationship"]
            if rel.get("relationship_exists"):
                lines.append(f"\nOUR RELATIONSHIP:")
                lines.append(f"  Total messages exchanged: {rel.get('total_messages', 0)}")
                lines.append(f"  First talked: {rel.get('first_conversation', 'unknown')}")
                lines.append(f"  Last interaction: {rel.get('last_interaction', 'unknown')}")
                if rel.get("collaboration_areas"):
                    lines.append(f"  Collaborated on: {', '.join(rel['collaboration_areas'])}")
                if rel.get("notes"):
                    lines.append(f"  Notes: {rel['notes']}")
            else:
                lines.append(f"\nNOTE: This is our first conversation with {context['with_node']}")

        # Known facts about them
        if context.get("known_facts_about_them"):
            lines.append(f"\nWHAT I KNOW ABOUT {context['with_node'].upper()}:")
            for fact in context["known_facts_about_them"][:5]:
                lines.append(f"  - [{fact['type']}] {fact['content']}")

        # Relevant highlights
        if context.get("relevant_highlights"):
            lines.append(f"\nIMPORTANT FROM PAST CONVERSATIONS:")
            for h in context["relevant_highlights"][:3]:
                lines.append(f"  - ({h['reason']}) {h['content'][:100]}...")

        # Recent conversation history
        if context.get("conversation_history"):
            lines.append(f"\nRECENT CONVERSATION HISTORY:")
            for msg in context["conversation_history"][-10:]:
                direction = "->" if msg["direction"] == "outgoing" else "<-"
                lines.append(f"  [{msg['timestamp'][:16]}] {direction} {msg['content'][:80]}...")

        lines.append("\n" + "=" * 60)

        return "\n".join(lines)


# Singleton instance
_context_manager: Optional[ConversationContextManager] = None

def get_context_manager(storage_base: str, node_id: str) -> ConversationContextManager:
    """Get or create the conversation context manager singleton"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ConversationContextManager(storage_base, node_id)
    return _context_manager
