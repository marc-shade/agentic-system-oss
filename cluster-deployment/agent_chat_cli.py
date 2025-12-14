#!/usr/bin/env python3
"""
Agent Chat CLI

Interactive CLI for testing and monitoring autonomous agent conversations.

Features:
- Send messages to other nodes and see their AI responses
- Monitor ongoing conversations across the cluster
- View conversation history with any node
- Test multi-turn agent-to-agent dialogs
"""

import sys
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from node_chat_client import NodeChatClient


class AgentChatCLI:
    """Interactive CLI for agent conversations"""

    def __init__(self, node_id: str, storage_base: str):
        self.node_id = node_id
        self.storage_base = Path(storage_base)
        self.client = NodeChatClient(node_id, str(storage_base))
        self.chat_db = self.storage_base / "databases" / "cluster" / "node_chat.db"

    def send_and_wait_for_response(self, to_node: str, message: str, timeout: int = 30) -> Dict:
        """
        Send message and wait for AI response

        Returns both the sent message and the response from the autonomous agent
        """
        print(f"\n📤 Sending to {to_node}: {message}")

        # Send message
        result = self.client.send_message(to_node, message)

        if not result['success']:
            print(f"❌ Failed to send: {result}")
            return result

        conversation_id = result['conversation_id']
        message_id = result['message_id']

        print(f"✅ Delivered via: {', '.join([k for k,v in result['delivery_channels'].items() if v.get('success')])}")
        print(f"⏳ Waiting for AI response (timeout: {timeout}s)...")

        # Poll for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check for new messages in conversation
            conn = sqlite3.connect(str(self.chat_db))
            cursor = conn.cursor()

            cursor.execute("""
                SELECT message_id, from_node, content, timestamp
                FROM messages
                WHERE conversation_id = ?
                AND from_node = ?
                AND timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (conversation_id, to_node, result['timestamp']))

            row = cursor.fetchone()
            conn.close()

            if row:
                response = {
                    'message_id': row[0],
                    'from_node': row[1],
                    'content': row[2],
                    'timestamp': row[3]
                }
                elapsed = time.time() - start_time
                print(f"\n📥 Response from {to_node} ({elapsed:.1f}s):")
                print(f"{'-'*80}")
                print(response['content'])
                print(f"{'-'*80}")
                return response

            time.sleep(1)

        print(f"⏰ Timeout waiting for response after {timeout}s")
        return {'error': 'timeout'}

    def multi_turn_conversation(self, with_node: str):
        """Interactive multi-turn conversation with another node's AI agent"""
        print(f"\n{'='*80}")
        print(f"🤖 AGENT-TO-AGENT CONVERSATION: {self.node_id} <-> {with_node}")
        print(f"{'='*80}")
        print("\nThe autonomous agent on the other node will respond using AI.")
        print("Type your messages below. Type 'exit' to quit.\n")

        while True:
            try:
                # Get user input
                message = input(f"{self.node_id}> ").strip()

                if not message:
                    continue

                if message.lower() in ['exit', 'quit', 'q']:
                    print("\n👋 Ending conversation")
                    break

                # Send and wait for AI response
                self.send_and_wait_for_response(with_node, message, timeout=45)

            except KeyboardInterrupt:
                print("\n\n👋 Conversation interrupted")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def watch_conversations(self, interval: int = 5):
        """Watch all cluster conversations in real-time"""
        print(f"\n{'='*80}")
        print("🔍 WATCHING CLUSTER CONVERSATIONS (Ctrl+C to stop)")
        print(f"{'='*80}\n")

        last_message_id = None

        try:
            while True:
                conn = sqlite3.connect(str(self.chat_db))
                cursor = conn.cursor()

                # Get recent messages
                if last_message_id:
                    cursor.execute("""
                        SELECT message_id, from_node, to_node, content, timestamp, delivered
                        FROM messages
                        WHERE message_id > ?
                        ORDER BY timestamp ASC
                        LIMIT 50
                    """, (last_message_id,))
                else:
                    cursor.execute("""
                        SELECT message_id, from_node, to_node, content, timestamp, delivered
                        FROM messages
                        ORDER BY timestamp DESC
                        LIMIT 10
                    """)

                rows = cursor.fetchall()
                conn.close()

                if rows:
                    for row in reversed(rows):
                        msg_id, from_node, to_node, content, timestamp, delivered = row
                        status = "✓" if delivered else "⏳"
                        print(f"[{timestamp}] {status} {from_node} → {to_node}:")
                        print(f"  {content[:200]}")
                        print()

                        last_message_id = msg_id

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n👋 Stopped watching")

    def show_conversation_history(self, with_node: str, limit: int = 20):
        """Show conversation history with another node"""
        print(f"\n{'='*80}")
        print(f"📜 CONVERSATION HISTORY: {self.node_id} <-> {with_node}")
        print(f"{'='*80}\n")

        history = self.client.get_conversation_history(with_node, limit)

        if not history:
            print("No conversation history found.")
            return

        for msg in history:
            direction = "→" if msg['from_node'] == self.node_id else "←"
            prefix = "You" if msg['from_node'] == self.node_id else msg['from_node']
            status = "✓" if msg.get('delivered') else "⏳"

            print(f"[{msg['timestamp'][:19]}] {status} {direction} {prefix}:")
            print(f"  {msg['content']}")
            print()

    def cluster_status(self):
        """Show status of all autonomous agents in cluster"""
        print(f"\n{'='*80}")
        print("🌐 CLUSTER AGENT STATUS")
        print(f"{'='*80}\n")

        # Load cluster nodes
        config_path = self.storage_base / "cluster-deployment" / "cluster-nodes.json"
        with open(config_path) as f:
            nodes = json.load(f)["nodes"]

        for node_id, config in nodes.items():
            # Try to ping agent API
            try:
                import requests
                url = f"http://{config['ip']}:5200/api/chat/status"
                response = requests.get(url, timeout=2)

                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ {node_id} (online)")
                    print(f"   - Conversations: {data.get('conversations', 0)}")
                    print(f"   - Last seen: {data.get('timestamp', 'unknown')}")
                else:
                    print(f"⚠️  {node_id} (daemon running, agent unknown)")
            except Exception:
                print(f"❌ {node_id} (offline or unreachable)")

            print()


def main():
    """Main CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Agent Chat CLI - Test autonomous agent conversations")
    parser.add_argument('command', choices=['send', 'chat', 'watch', 'history', 'status'],
                       help='Command to execute')
    parser.add_argument('--node', '-n', help='Target node ID')
    parser.add_argument('--message', '-m', help='Message to send')
    parser.add_argument('--limit', '-l', type=int, default=20, help='History limit')
    parser.add_argument('--timeout', '-t', type=int, default=30, help='Response timeout (seconds)')

    args = parser.parse_args()

    # Load local node config
    node_config_path = Path.home() / ".claude" / "node-config.json"
    with open(node_config_path) as f:
        config = json.load(f)

    cli = AgentChatCLI(config['node_id'], config['storage']['base'])

    # Execute command
    if args.command == 'send':
        if not args.node or not args.message:
            print("Error: --node and --message required for 'send' command")
            sys.exit(1)
        cli.send_and_wait_for_response(args.node, args.message, args.timeout)

    elif args.command == 'chat':
        if not args.node:
            print("Error: --node required for 'chat' command")
            sys.exit(1)
        cli.multi_turn_conversation(args.node)

    elif args.command == 'watch':
        cli.watch_conversations()

    elif args.command == 'history':
        if not args.node:
            print("Error: --node required for 'history' command")
            sys.exit(1)
        cli.show_conversation_history(args.node, args.limit)

    elif args.command == 'status':
        cli.cluster_status()


if __name__ == '__main__':
    main()
