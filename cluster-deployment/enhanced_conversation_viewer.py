#!/usr/bin/env python3
"""
Enhanced Conversation Viewer for Node-to-Node Communication

Displays cluster conversations in rich, threaded format similar to Sequential Thinking MCP.
Shows reasoning context, decision points, and outcomes.
"""

import os
import platform
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import json


def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path("/Volumes/SSDRAID0/agentic-system").exists():
            return Path("/Volumes/SSDRAID0/agentic-system")
        elif Path("/Volumes/FILES/agentic-system").exists():
            return Path("/Volumes/FILES/agentic-system")
    elif system == "Linux":
        if Path("/home/marc/agentic-system").exists():
            return Path("/home/marc/agentic-system")
        elif Path("/mnt/agentic-system").exists():
            return Path("/mnt/agentic-system")
    return Path(__file__).parent.parent


_DEFAULT_STORAGE_BASE = str(_get_storage_base())


class EnhancedConversationViewer:
    """
    Displays node-to-node conversations with rich context, threading, and reasoning visibility.
    """

    def __init__(self, storage_base: str = None):
        self.storage_base = Path(storage_base or _DEFAULT_STORAGE_BASE)
        self.db_path = self.storage_base / "databases/cluster/node_chat.db"

        # Node persona colors and styles
        self.personas = {
            "macpro51": {
                "name": "Builder",
                "color": "\033[94m",  # Blue
                "style": "pragmatic",
                "focus": "execution and performance"
            },
            "mac-studio": {
                "name": "Phoenix (Orchestrator)",
                "color": "\033[92m",  # Green
                "style": "strategic",
                "focus": "coordination and planning"
            },
            "macbook-air-m3": {
                "name": "Researcher",
                "color": "\033[93m",  # Yellow
                "style": "analytical",
                "focus": "knowledge and investigation"
            }
        }

        self.reset = "\033[0m"
        self.bold = "\033[1m"
        self.dim = "\033[2m"

    def get_conversations(self, limit: int = 20, mode: str = "threaded") -> str:
        """
        Get conversations in various display modes.

        Args:
            limit: Number of messages to retrieve
            mode: Display mode (threaded, recent, active)

        Returns:
            Formatted conversation display
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if mode == "threaded":
            return self._get_threaded_conversations(cursor, limit)
        elif mode == "recent":
            return self._get_recent_messages(cursor, limit)
        elif mode == "active":
            return self._get_active_conversations(cursor)
        else:
            return self._get_recent_messages(cursor, limit)

    def _get_threaded_conversations(self, cursor, limit: int) -> str:
        """Group messages by conversation context with rich formatting."""

        # Get conversations with message counts
        cursor.execute("""
            SELECT c.conversation_id, c.participants, c.context, c.created_at,
                   COUNT(m.message_id) as message_count,
                   MAX(m.timestamp) as last_activity
            FROM conversations c
            LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            WHERE c.active = 1
            GROUP BY c.conversation_id
            ORDER BY last_activity DESC
            LIMIT ?
        """, (limit,))

        conversations = cursor.fetchall()

        output = []
        output.append(f"\n{self.bold}{'═' * 80}{self.reset}")
        output.append(f"{self.bold}🤖 CLUSTER CONVERSATIONS - Threaded View{self.reset}")
        output.append(f"{self.bold}{'═' * 80}{self.reset}\n")

        for conv in conversations:
            conv_id = conv['conversation_id']
            participants = conv['participants']
            context = conv['context'] or "General coordination"
            message_count = conv['message_count']

            # Get messages for this conversation
            cursor.execute("""
                SELECT message_id, from_node, to_node, content, timestamp,
                       delivered, read
                FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
            """, (conv_id,))

            messages = cursor.fetchall()

            if not messages:
                continue

            # Conversation header
            output.append(f"{self.bold}┌─ THREAD: {context}{self.reset}")
            output.append(f"{self.dim}│ Participants: {participants}{self.reset}")
            output.append(f"{self.dim}│ Messages: {message_count}{self.reset}")
            output.append(f"{self.bold}└{'─' * 78}{self.reset}\n")

            # Display messages in thread
            for i, msg in enumerate(messages):
                output.append(self._format_message(msg, i + 1, len(messages)))

            output.append(f"{self.bold}{'─' * 80}{self.reset}\n")

        if not conversations:
            output.append(f"{self.dim}No active conversations found.{self.reset}\n")

        return "\n".join(output)

    def _format_message(self, msg: sqlite3.Row, index: int, total: int) -> str:
        """Format a single message with rich context."""

        from_node = msg['from_node']
        to_node = msg['to_node']
        content = msg['content']
        timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")

        from_persona = self.personas.get(from_node, {"name": from_node, "color": "\033[90m"})
        to_persona = self.personas.get(to_node, {"name": to_node, "color": "\033[90m"})

        # Delivery status
        if msg['read']:
            status = "✓✓"  # Read
        elif msg['delivered']:
            status = "✓"   # Delivered
        else:
            status = "○"   # Pending

        # Extract reasoning/context from message content
        lines = content.split('\n')
        first_line = lines[0][:100] + "..." if len(lines[0]) > 100 else lines[0]

        output = []

        # Message header
        output.append(f"{self.dim}[{index}/{total}] {timestamp}{self.reset} "
                     f"{from_persona['color']}{from_persona['name']}{self.reset} "
                     f"→ {to_persona['color']}{to_persona['name']}{self.reset} "
                     f"{self.dim}{status}{self.reset}")

        # Message content (with smart truncation for long messages)
        if len(content) > 300:
            # Show summary for long messages
            output.append(f"┌─ {first_line}")

            # Look for structured content markers
            if "##" in content or "**" in content:
                # Extract key points
                key_sections = []
                for line in lines:
                    if line.startswith("##") or line.startswith("**"):
                        key_sections.append(f"│  {line}")
                        if len(key_sections) >= 5:
                            break
                output.extend(key_sections)

            output.append(f"└─ ({len(content)} chars, use full view for details)\n")
        else:
            # Show full content for short messages
            output.append("┌─" + "─" * 70)
            for line in lines:
                output.append(f"│ {line}")
            output.append("└─" + "─" * 70 + "\n")

        return "\n".join(output)

    def _get_recent_messages(self, cursor, limit: int) -> str:
        """Get recent messages in chronological order."""

        cursor.execute("""
            SELECT message_id, from_node, to_node, content, timestamp,
                   delivered, read
            FROM messages
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        messages = cursor.fetchall()

        output = []
        output.append(f"\n{self.bold}{'═' * 80}{self.reset}")
        output.append(f"{self.bold}📨 RECENT CLUSTER MESSAGES{self.reset}")
        output.append(f"{self.bold}{'═' * 80}{self.reset}\n")

        for i, msg in enumerate(reversed(messages)):
            output.append(self._format_message(msg, i + 1, len(messages)))

        if not messages:
            output.append(f"{self.dim}No messages found.{self.reset}\n")

        return "\n".join(output)

    def _get_active_conversations(self, cursor) -> str:
        """Get only conversations with recent activity."""

        cursor.execute("""
            SELECT c.conversation_id, c.participants, c.context,
                   MAX(m.timestamp) as last_activity,
                   COUNT(m.message_id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            WHERE c.active = 1
              AND m.timestamp > datetime('now', '-1 hour')
            GROUP BY c.conversation_id
            ORDER BY last_activity DESC
        """)

        conversations = cursor.fetchall()

        output = []
        output.append(f"\n{self.bold}{'═' * 80}{self.reset}")
        output.append(f"{self.bold}🔥 ACTIVE CONVERSATIONS (Last Hour){self.reset}")
        output.append(f"{self.bold}{'═' * 80}{self.reset}\n")

        for conv in conversations:
            participants = conv['participants']
            context = conv['context'] or "General"
            message_count = conv['message_count']
            last_activity = datetime.fromisoformat(conv['last_activity']).strftime("%H:%M:%S")

            output.append(f"{self.bold}• {context}{self.reset}")
            output.append(f"  {self.dim}Participants: {participants}{self.reset}")
            output.append(f"  {self.dim}Messages: {message_count} | Last: {last_activity}{self.reset}\n")

        if not conversations:
            output.append(f"{self.dim}No active conversations in the last hour.{self.reset}\n")

        return "\n".join(output)

    def get_conversation_stats(self) -> Dict:
        """Get statistics about cluster conversations."""

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        # Total messages
        cursor.execute("SELECT COUNT(*) FROM messages")
        stats['total_messages'] = cursor.fetchone()[0]

        # Messages by node
        cursor.execute("""
            SELECT from_node, COUNT(*) as count
            FROM messages
            GROUP BY from_node
        """)
        stats['messages_by_node'] = {row[0]: row[1] for row in cursor.fetchall()}

        # Active conversations
        cursor.execute("SELECT COUNT(*) FROM conversations WHERE active = 1")
        stats['active_conversations'] = cursor.fetchone()[0]

        # Messages in last hour
        cursor.execute("""
            SELECT COUNT(*) FROM messages
            WHERE timestamp > datetime('now', '-1 hour')
        """)
        stats['recent_messages'] = cursor.fetchone()[0]

        # Average response time
        cursor.execute("""
            SELECT AVG(
                (julianday(m2.timestamp) - julianday(m1.timestamp)) * 24 * 60
            ) as avg_response_minutes
            FROM messages m1
            JOIN messages m2 ON m1.conversation_id = m2.conversation_id
            WHERE m2.timestamp > m1.timestamp
              AND m1.from_node != m2.from_node
        """)
        result = cursor.fetchone()[0]
        stats['avg_response_time_minutes'] = round(result, 2) if result else None

        conn.close()
        return stats


def main():
    """CLI entry point for testing."""
    import sys

    viewer = EnhancedConversationViewer()

    mode = sys.argv[1] if len(sys.argv) > 1 else "threaded"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    if mode == "stats":
        stats = viewer.get_conversation_stats()
        print(json.dumps(stats, indent=2))
    else:
        print(viewer.get_conversations(limit=limit, mode=mode))


if __name__ == "__main__":
    main()
