#!/usr/bin/env python3
"""
Node Chat Monitor - Observe Agent-to-Agent Conversations
Displays real-time cluster communications for human observation.
"""

import os
import sys
import sqlite3
import time
from datetime import datetime
from pathlib import Path
import json

class NodeChatMonitor:
    """Monitor and display agent-to-agent conversations"""

    def __init__(self, storage_base: str):
        self.storage_base = Path(storage_base)
        self.chat_db = self.storage_base / "databases" / "cluster" / "node_chat.db"
        self.last_message_id = None

        # Load node config
        node_config_path = Path.home() / ".claude" / "node-config.json"
        with open(node_config_path) as f:
            config = json.load(f)
        self.node_id = config['node_id']

        # Color codes for different nodes
        self.colors = {
            'macpro51': '\033[94m',      # Blue
            'mac-studio': '\033[92m',     # Green
            'macbook-air-m3': '\033[93m', # Yellow
            'reset': '\033[0m',
            'bold': '\033[1m',
            'dim': '\033[2m'
        }

    def get_recent_messages(self, limit=10):
        """Get recent messages across all conversations"""
        if not self.chat_db.exists():
            return []

        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT message_id, conversation_id, from_node, to_node, content, timestamp, delivered, read
            FROM messages
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'message_id': row[0],
                'conversation_id': row[1],
                'from_node': row[2],
                'to_node': row[3],
                'content': row[4],
                'timestamp': row[5],
                'delivered': bool(row[6]),
                'read': bool(row[7])
            })

        conn.close()
        return list(reversed(messages))

    def get_new_messages(self):
        """Get messages since last check"""
        if not self.chat_db.exists():
            return []

        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        if self.last_message_id:
            cursor.execute("""
                SELECT message_id, conversation_id, from_node, to_node, content, timestamp, delivered, read
                FROM messages
                WHERE message_id > ?
                ORDER BY timestamp ASC
            """, (self.last_message_id,))
        else:
            # First run - get last 5 messages
            cursor.execute("""
                SELECT message_id, conversation_id, from_node, to_node, content, timestamp, delivered, read
                FROM messages
                ORDER BY timestamp DESC
                LIMIT 5
            """)

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'message_id': row[0],
                'conversation_id': row[1],
                'from_node': row[2],
                'to_node': row[3],
                'content': row[4],
                'timestamp': row[5],
                'delivered': bool(row[6]),
                'read': bool(row[7])
            })
            self.last_message_id = row[0]

        conn.close()
        return messages if self.last_message_id else list(reversed(messages))

    def format_message(self, msg):
        """Format message for display"""
        from_color = self.colors.get(msg['from_node'], self.colors['reset'])
        to_color = self.colors.get(msg['to_node'], self.colors['reset'])
        reset = self.colors['reset']
        bold = self.colors['bold']
        dim = self.colors['dim']

        # Format timestamp
        ts = datetime.fromisoformat(msg['timestamp']).strftime('%H:%M:%S')

        # Direction arrow
        if msg['from_node'] == self.node_id:
            arrow = f"{bold}→{reset}"  # Outgoing
        elif msg['to_node'] == self.node_id:
            arrow = f"{bold}←{reset}"  # Incoming
        else:
            arrow = f"{dim}↔{reset}"   # Between other nodes

        # Delivery status
        status = "✓" if msg['delivered'] else "○"
        if msg['read']:
            status = "✓✓"

        return (f"{dim}[{ts}]{reset} "
                f"{from_color}{msg['from_node']}{reset} "
                f"{arrow} "
                f"{to_color}{msg['to_node']}{reset}: "
                f"{msg['content']} "
                f"{dim}{status}{reset}")

    def display_history(self, limit=10):
        """Display recent conversation history"""
        messages = self.get_recent_messages(limit)

        print(f"\n{self.colors['bold']}{'='*80}{self.colors['reset']}")
        print(f"{self.colors['bold']}  Cluster Conversation History (Last {limit} messages){self.colors['reset']}")
        print(f"{self.colors['bold']}{'='*80}{self.colors['reset']}\n")

        if not messages:
            print(f"{self.colors['dim']}  No messages yet{self.colors['reset']}\n")
            return

        for msg in messages:
            print(f"  {self.format_message(msg)}")

        print()

    def monitor_live(self, interval=2):
        """Monitor conversations in real-time"""
        print(f"\n{self.colors['bold']}{'='*80}{self.colors['reset']}")
        print(f"{self.colors['bold']}  Live Cluster Conversation Monitor ({self.node_id}){self.colors['reset']}")
        print(f"{self.colors['bold']}{'='*80}{self.colors['reset']}")
        print(f"{self.colors['dim']}  Press Ctrl+C to stop{self.colors['reset']}\n")

        # Show initial history
        self.display_history(limit=5)

        print(f"{self.colors['dim']}Monitoring for new messages...{self.colors['reset']}\n")

        try:
            while True:
                new_messages = self.get_new_messages()

                for msg in new_messages:
                    print(f"  {self.format_message(msg)}")

                time.sleep(interval)

        except KeyboardInterrupt:
            print(f"\n\n{self.colors['dim']}Monitor stopped{self.colors['reset']}\n")

    def show_conversations(self):
        """Show all active conversations"""
        if not self.chat_db.exists():
            print("No conversations yet")
            return

        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.conversation_id, c.participants, c.last_activity,
                   COUNT(m.message_id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            WHERE c.active = 1
            GROUP BY c.conversation_id
            ORDER BY c.last_activity DESC
        """)

        print(f"\n{self.colors['bold']}{'='*80}{self.colors['reset']}")
        print(f"{self.colors['bold']}  Active Conversations{self.colors['reset']}")
        print(f"{self.colors['bold']}{'='*80}{self.colors['reset']}\n")

        conversations = cursor.fetchall()
        if not conversations:
            print(f"{self.colors['dim']}  No active conversations{self.colors['reset']}\n")
            conn.close()
            return

        for row in conversations:
            conv_id = row[0][:8]  # Short ID
            participants = row[1]
            last_activity = datetime.fromisoformat(row[2]).strftime('%Y-%m-%d %H:%M')
            msg_count = row[3]

            print(f"  {self.colors['bold']}{conv_id}{self.colors['reset']} | "
                  f"{participants} | "
                  f"{msg_count} messages | "
                  f"{self.colors['dim']}Last: {last_activity}{self.colors['reset']}")

        print()
        conn.close()

    def show_stats(self):
        """Show conversation statistics"""
        if not self.chat_db.exists():
            print("No statistics yet")
            return

        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        # Total messages
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]

        # Messages by node
        cursor.execute("""
            SELECT from_node, COUNT(*) as count
            FROM messages
            GROUP BY from_node
            ORDER BY count DESC
        """)
        by_node = cursor.fetchall()

        # Delivery rate
        cursor.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN delivered = 1 THEN 1 ELSE 0 END) as delivered
            FROM messages
        """)
        total, delivered = cursor.fetchone()
        delivery_rate = (delivered / total * 100) if total > 0 else 0

        print(f"\n{self.colors['bold']}{'='*80}{self.colors['reset']}")
        print(f"{self.colors['bold']}  Cluster Communication Statistics{self.colors['reset']}")
        print(f"{self.colors['bold']}{'='*80}{self.colors['reset']}\n")

        print(f"  Total Messages: {total_messages}")
        print(f"  Delivery Rate: {delivery_rate:.1f}%")
        print(f"\n  {self.colors['bold']}Messages by Node:{self.colors['reset']}")

        for node, count in by_node:
            node_color = self.colors.get(node, self.colors['reset'])
            print(f"    {node_color}{node}{self.colors['reset']}: {count}")

        print()
        conn.close()


def main():
    """CLI interface for chat monitor"""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor cluster node conversations")
    parser.add_argument('--live', '-l', action='store_true', help='Monitor live conversations')
    parser.add_argument('--history', '-H', type=int, default=10, help='Show recent history (default: 10)')
    parser.add_argument('--conversations', '-c', action='store_true', help='List active conversations')
    parser.add_argument('--stats', '-s', action='store_true', help='Show statistics')
    parser.add_argument('--interval', '-i', type=int, default=2, help='Polling interval for live mode (default: 2s)')

    args = parser.parse_args()

    # Load node config
    node_config_path = Path.home() / ".claude" / "node-config.json"
    with open(node_config_path) as f:
        config = json.load(f)

    monitor = NodeChatMonitor(config['storage']['base'])

    if args.live:
        monitor.monitor_live(interval=args.interval)
    elif args.conversations:
        monitor.show_conversations()
    elif args.stats:
        monitor.show_stats()
    else:
        monitor.display_history(limit=args.history)


if __name__ == '__main__':
    main()
