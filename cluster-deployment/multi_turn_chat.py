#!/usr/bin/env python3
"""
Multi-Turn Chat System for Cluster Nodes
=========================================

Enables full conversational communication between cluster nodes with:
- Conversation threads (multi-turn context)
- Response tracking
- Conversation history
- Direct node-to-node communication
- Broadcast capabilities
"""
import os

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import platform

# Platform-aware paths
if platform.system() == "Darwin":
    STORAGE_BASE = str(_STORAGE_BASE)
else:
    STORAGE_BASE = str(_STORAGE_BASE)

DB_PATH = Path(STORAGE_BASE) / "databases" / "cluster" / "node_chat.db"


class MultiTurnChat:
    """Multi-turn conversation system for cluster nodes"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self._init_database()

    def _init_database(self):
        """Initialize database schema for multi-turn conversations"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if old schema exists and migrate if needed
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
        existing = cursor.fetchone()

        if existing:
            # Migrate existing schema - add new columns if missing
            cursor.execute("PRAGMA table_info(conversations)")
            columns = {row[1] for row in cursor.fetchall()}

            if 'topic' not in columns:
                cursor.execute("ALTER TABLE conversations ADD COLUMN topic TEXT")
            if 'started_by' not in columns:
                cursor.execute("ALTER TABLE conversations ADD COLUMN started_by TEXT")
            if 'started_at' not in columns:
                cursor.execute("ALTER TABLE conversations ADD COLUMN started_at TEXT")
            if 'last_message_at' not in columns:
                cursor.execute("ALTER TABLE conversations ADD COLUMN last_message_at TEXT")
            if 'status' not in columns:
                cursor.execute("ALTER TABLE conversations ADD COLUMN status TEXT DEFAULT 'active'")
            if 'message_count' not in columns:
                cursor.execute("ALTER TABLE conversations ADD COLUMN message_count INTEGER DEFAULT 0")
        else:
            # Create new table
            cursor.execute("""
                CREATE TABLE conversations (
                    conversation_id TEXT PRIMARY KEY,
                    started_by TEXT NOT NULL,
                    participants TEXT NOT NULL,
                    topic TEXT,
                    started_at TEXT NOT NULL,
                    last_message_at TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    message_count INTEGER DEFAULT 0
                )
            """)

        # Enhanced messages table with conversation context
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                from_node TEXT NOT NULL,
                to_node TEXT,
                message_type TEXT DEFAULT 'message',
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp TEXT NOT NULL,
                parent_message_id TEXT,
                requires_response BOOLEAN DEFAULT 0,
                response_received BOOLEAN DEFAULT 0,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
                FOREIGN KEY (parent_message_id) REFERENCES chat_messages(message_id)
            )
        """)

        # Indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversation_messages
            ON chat_messages(conversation_id, timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_node_messages
            ON chat_messages(to_node, timestamp)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_parent_messages
            ON chat_messages(parent_message_id)
        """)

        conn.commit()
        conn.close()

    def start_conversation(
        self,
        participants: List[str],
        topic: str,
        initial_message: str,
        requires_response: bool = True
    ) -> str:
        """
        Start a new conversation thread

        Args:
            participants: List of node IDs to include
            topic: Conversation topic/subject
            initial_message: First message content
            requires_response: Whether this expects a response

        Returns:
            conversation_id
        """
        conversation_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Create conversation
        cursor.execute("""
            INSERT INTO conversations
            (conversation_id, started_by, participants, topic, started_at, last_message_at, message_count)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (
            conversation_id,
            self.node_id,
            json.dumps([self.node_id] + participants),
            topic,
            now,
            now
        ))

        # Send initial message to all participants
        for participant in participants:
            msg_id = str(uuid.uuid4()) if participant != participants[0] else message_id

            cursor.execute("""
                INSERT INTO chat_messages
                (message_id, conversation_id, from_node, to_node, message_type,
                 content, timestamp, requires_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                msg_id,
                conversation_id,
                self.node_id,
                participant,
                'conversation_start',
                initial_message,
                now,
                requires_response
            ))

        conn.commit()
        conn.close()

        print(f"✓ Started conversation {conversation_id[:8]}... with {len(participants)} participants")
        return conversation_id

    def send_message(
        self,
        conversation_id: str,
        content: str,
        to_node: Optional[str] = None,
        parent_message_id: Optional[str] = None,
        requires_response: bool = False,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Send a message in an existing conversation

        Args:
            conversation_id: Conversation to send message to
            content: Message content
            to_node: Specific recipient (None = broadcast to all participants)
            parent_message_id: Message this is responding to
            requires_response: Whether this expects a response
            metadata: Additional message metadata

        Returns:
            message_id
        """
        message_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Get conversation participants
        cursor.execute(
            "SELECT participants FROM conversations WHERE conversation_id = ?",
            (conversation_id,)
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Conversation {conversation_id} not found")

        participants = json.loads(row[0])

        # Determine recipients
        if to_node:
            recipients = [to_node]
        else:
            # Broadcast to all participants except sender
            recipients = [p for p in participants if p != self.node_id]

        # Send message to recipients
        for recipient in recipients:
            msg_id = str(uuid.uuid4()) if recipient != recipients[0] else message_id

            cursor.execute("""
                INSERT INTO chat_messages
                (message_id, conversation_id, from_node, to_node, content,
                 timestamp, parent_message_id, requires_response, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                msg_id,
                conversation_id,
                self.node_id,
                recipient,
                content,
                now,
                parent_message_id,
                requires_response,
                json.dumps(metadata) if metadata else None
            ))

        # Mark parent message as responded to
        if parent_message_id:
            cursor.execute("""
                UPDATE chat_messages
                SET response_received = 1
                WHERE message_id = ?
            """, (parent_message_id,))

        # Update conversation
        cursor.execute("""
            UPDATE conversations
            SET last_message_at = ?,
                message_count = message_count + ?
            WHERE conversation_id = ?
        """, (now, len(recipients), conversation_id))

        conn.commit()
        conn.close()

        print(f"✓ Sent message in conversation {conversation_id[:8]}... to {len(recipients)} recipient(s)")
        return message_id

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get complete conversation history

        Args:
            conversation_id: Conversation to retrieve
            limit: Maximum messages to return

        Returns:
            List of messages in chronological order
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM chat_messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
            LIMIT ?
        """, (conversation_id, limit))

        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            if msg['metadata']:
                msg['metadata'] = json.loads(msg['metadata'])
            messages.append(msg)

        conn.close()
        return messages

    def get_pending_messages(
        self,
        mark_as_read: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all pending messages for this node

        Args:
            mark_as_read: Whether to mark messages as read

        Returns:
            List of unread messages
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get messages where this node is recipient and response not yet received
        cursor.execute("""
            SELECT m.*, c.topic, c.participants
            FROM chat_messages m
            JOIN conversations c ON m.conversation_id = c.conversation_id
            WHERE m.to_node = ?
            AND m.requires_response = 1
            AND m.response_received = 0
            ORDER BY m.timestamp DESC
        """, (self.node_id,))

        messages = []
        for row in cursor.fetchall():
            msg = dict(row)
            if msg['metadata']:
                msg['metadata'] = json.loads(msg['metadata'])
            if msg['participants']:
                msg['participants'] = json.loads(msg['participants'])
            messages.append(msg)

        conn.close()
        return messages

    def get_conversations(
        self,
        status: str = 'active',
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get conversations this node is part of

        Args:
            status: Conversation status filter
            limit: Maximum conversations to return

        Returns:
            List of conversations
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM conversations
            WHERE participants LIKE ? AND status = ?
            ORDER BY last_message_at DESC
            LIMIT ?
        """, (f'%{self.node_id}%', status, limit))

        conversations = []
        for row in cursor.fetchall():
            conv = dict(row)
            conv['participants'] = json.loads(conv['participants'])
            conversations.append(conv)

        conn.close()
        return conversations

    def respond_to_message(
        self,
        message_id: str,
        response_content: str,
        requires_response: bool = False,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Respond to a specific message

        Args:
            message_id: Message to respond to
            response_content: Response content
            requires_response: Whether this response expects another response
            metadata: Additional metadata

        Returns:
            response_message_id
        """
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get original message
        cursor.execute("""
            SELECT conversation_id, from_node
            FROM chat_messages
            WHERE message_id = ?
        """, (message_id,))

        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Message {message_id} not found")

        conversation_id = row['conversation_id']
        original_sender = row['from_node']

        conn.close()

        # Send response back to original sender
        return self.send_message(
            conversation_id=conversation_id,
            content=response_content,
            to_node=original_sender,
            parent_message_id=message_id,
            requires_response=requires_response,
            metadata=metadata
        )

    def close_conversation(self, conversation_id: str):
        """Mark conversation as closed"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE conversations
            SET status = 'closed'
            WHERE conversation_id = ?
        """, (conversation_id,))

        conn.commit()
        conn.close()

        print(f"✓ Closed conversation {conversation_id[:8]}...")


def main():
    """Example usage"""
    # Get current node ID
    import platform

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

    node_id = platform.node()

    chat = MultiTurnChat(node_id)

    # Example: Check for pending messages
    pending = chat.get_pending_messages()
    print(f"\n{len(pending)} pending message(s) requiring response")

    for msg in pending:
        print(f"\nFrom: {msg['from_node']}")
        print(f"Topic: {msg['topic']}")
        print(f"Message: {msg['content']}")
        print(f"Conversation ID: {msg['conversation_id'][:8]}...")

    # Example: Get active conversations
    conversations = chat.get_conversations()
    print(f"\n{len(conversations)} active conversation(s)")

    for conv in conversations:
        print(f"\nConversation: {conv['topic']}")
        print(f"  Participants: {', '.join(conv['participants'])}")
        print(f"  Messages: {conv['message_count']}")
        print(f"  Last message: {conv['last_message_at']}")


if __name__ == "__main__":
    main()
