#!/usr/bin/env python3
"""
Multi-Channel Node Chat Client
Enables AI personas to chat with other nodes using redundant delivery methods.

Delivery Channels (in order of priority):
1. HTTP POST - Real-time delivery via REST API
2. Database INSERT - Direct database write via SSH
3. File Sync - Message file dropped in watched directory

All channels are attempted to ensure message delivery even if nodes are temporarily unreachable.
"""

import os
import sys
import json
import sqlite3
import requests
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NodeChatClient:
    """Multi-channel chat client for inter-node communication"""

    def __init__(self, node_id: str, storage_base: str):
        self.node_id = node_id
        self.storage_base = Path(storage_base)

        # Load cluster configuration
        self.cluster_nodes = self._load_cluster_nodes()

        # Local database
        self.chat_db = self.storage_base / "databases" / "cluster" / "node_chat.db"

        logger.info(f"Chat client initialized for {self.node_id}")

    def _load_cluster_nodes(self) -> Dict:
        """Load cluster node configuration"""
        config_path = self.storage_base / "cluster-deployment" / "cluster-nodes.json"
        with open(config_path) as f:
            data = json.load(f)
            self._discovery_config = data.get("discovery", {})
            return data["nodes"]

    def _get_node_address(self, node_config: Dict) -> str:
        """Get the network address for a node (hostname preferred, ip fallback)."""
        # Prefer hostname (mDNS) over hardcoded IP
        return node_config.get('hostname') or node_config.get('ip', 'localhost')

    def _get_ssh_user(self) -> str:
        """Get SSH user from discovery config."""
        return self._discovery_config.get('ssh_user', 'marc')

    def _resolve_node(self, node_ref: str) -> Optional[str]:
        """Resolve node reference (role or machine name) to machine name key."""
        # Direct match by machine name
        if node_ref in self.cluster_nodes:
            return node_ref
        # Lookup by node_id (role)
        for machine_name, config in self.cluster_nodes.items():
            if config.get('node_id') == node_ref or config.get('role') == node_ref:
                return machine_name
        return None

    def send_message(self, to_node: str, content: str, conversation_id: Optional[str] = None) -> Dict:
        """
        Send message using multiple channels for redundancy

        Attempts delivery via:
        1. HTTP API (fastest, real-time)
        2. Direct database write via SSH (reliable)
        3. File sync (backup for offline scenarios)

        Returns delivery status for each channel.
        """
        # Resolve role name (e.g., "builder") to machine name (e.g., "macpro51")
        resolved_node = self._resolve_node(to_node)
        if not resolved_node:
            return {'error': f'Unknown node: {to_node}', 'success': False}
        to_node = resolved_node

        # Generate message
        message_id = str(uuid.uuid4())
        if not conversation_id:
            conversation_id = self._get_conversation_id(to_node)

        timestamp = datetime.now().isoformat()

        message = {
            'message_id': message_id,
            'conversation_id': conversation_id,
            'from_node': self.node_id,
            'to_node': to_node,
            'content': content,
            'timestamp': timestamp
        }

        # Store locally first
        self._store_message_local(message)

        # Attempt delivery via all channels
        delivery_results = {}

        # Channel 1: HTTP API (primary)
        delivery_results['http'] = self._deliver_http(to_node, message)

        # Channel 2: Database write via SSH (backup)
        delivery_results['database'] = self._deliver_database(to_node, message)

        # Channel 3: File sync (tertiary)
        delivery_results['file_sync'] = self._deliver_file_sync(to_node, message)

        # Determine overall success
        success = any(r.get('success') for r in delivery_results.values())

        logger.info(f"Message {message_id} delivery: HTTP={delivery_results['http']['success']}, "
                   f"DB={delivery_results['database']['success']}, "
                   f"File={delivery_results['file_sync']['success']}")

        return {
            'message_id': message_id,
            'conversation_id': conversation_id,
            'success': success,
            'delivery_channels': delivery_results,
            'timestamp': timestamp
        }

    def _deliver_http(self, to_node: str, message: Dict) -> Dict:
        """Deliver via HTTP REST API"""
        try:
            node_config = self.cluster_nodes[to_node]
            address = self._get_node_address(node_config)
            url = f"http://{address}:5200/api/chat/receive"

            response = requests.post(url, json=message, timeout=3)
            if response.status_code == 200:
                return {'success': True, 'method': 'http', 'latency_ms': response.elapsed.total_seconds() * 1000}
            else:
                return {'success': False, 'method': 'http', 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            return {'success': False, 'method': 'http', 'error': str(e)}

    def _deliver_database(self, to_node: str, message: Dict) -> Dict:
        """Deliver via direct database write over SSH"""
        try:
            node_config = self.cluster_nodes[to_node]
            remote_db = f"{node_config['storage_base']}/databases/cluster/node_chat.db"

            # Build SQL command
            sql = f"""
            INSERT OR REPLACE INTO messages
            (message_id, conversation_id, from_node, to_node, content, timestamp, delivered, delivered_at)
            VALUES (
                '{message['message_id']}',
                '{message['conversation_id']}',
                '{message['from_node']}',
                '{message['to_node']}',
                '{message['content'].replace("'", "''")}',
                '{message['timestamp']}',
                1,
                CURRENT_TIMESTAMP
            );
            """

            # Execute via SSH
            address = self._get_node_address(node_config)
            ssh_user = self._get_ssh_user()
            result = subprocess.run([
                'ssh', f"{ssh_user}@{address}",
                f'sqlite3 {remote_db} "{sql}"'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return {'success': True, 'method': 'database'}
            else:
                return {'success': False, 'method': 'database', 'error': result.stderr}
        except Exception as e:
            return {'success': False, 'method': 'database', 'error': str(e)}

    def _deliver_file_sync(self, to_node: str, message: Dict) -> Dict:
        """Deliver via file drop in watched directory"""
        try:
            node_config = self.cluster_nodes[to_node]
            remote_inbox = f"{node_config['storage_base']}/cluster-inbox"

            # Create message file locally
            local_temp = Path("/tmp") / f"msg_{message['message_id']}.json"
            with open(local_temp, 'w') as f:
                json.dump(message, f, indent=2)

            # SCP to remote inbox
            address = self._get_node_address(node_config)
            ssh_user = self._get_ssh_user()
            result = subprocess.run([
                'scp', str(local_temp),
                f"{ssh_user}@{address}:{remote_inbox}/{message['message_id']}.json"
            ], capture_output=True, text=True, timeout=10)

            # Cleanup
            local_temp.unlink()

            if result.returncode == 0:
                return {'success': True, 'method': 'file_sync'}
            else:
                return {'success': False, 'method': 'file_sync', 'error': result.stderr}
        except Exception as e:
            return {'success': False, 'method': 'file_sync', 'error': str(e)}

    def _store_message_local(self, message: Dict):
        """Store message in local database"""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO messages
            (message_id, conversation_id, from_node, to_node, content, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (message['message_id'], message['conversation_id'], message['from_node'],
              message['to_node'], message['content'], message['timestamp']))

        conn.commit()
        conn.close()

    def _get_conversation_id(self, other_node: str) -> str:
        """Get existing conversation ID or create new one"""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        participants = ",".join(sorted([self.node_id, other_node]))

        cursor.execute("""
            SELECT conversation_id FROM conversations
            WHERE participants = ? AND active = 1
            ORDER BY last_activity DESC LIMIT 1
        """, (participants,))

        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0]
        else:
            # Create new conversation
            conv_id = str(uuid.uuid4())
            conn = sqlite3.connect(str(self.chat_db))
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations (conversation_id, participants)
                VALUES (?, ?)
            """, (conv_id, participants))
            conn.commit()
            conn.close()
            return conv_id

    def get_conversation_history(self, with_node: str, limit: int = 50) -> List[Dict]:
        """Get conversation history with another node"""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        # Find conversation
        participants = ",".join(sorted([self.node_id, with_node]))
        cursor.execute("""
            SELECT conversation_id FROM conversations
            WHERE participants = ?
            ORDER BY last_activity DESC LIMIT 1
        """, (participants,))

        result = cursor.fetchone()
        if not result:
            return []

        conversation_id = result[0]

        # Get messages
        cursor.execute("""
            SELECT message_id, from_node, to_node, content, timestamp, delivered
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (conversation_id, limit))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'message_id': row[0],
                'from_node': row[1],
                'to_node': row[2],
                'content': row[3],
                'timestamp': row[4],
                'delivered': bool(row[5])
            })

        conn.close()
        return list(reversed(messages))

    def chat(self, with_node: str):
        """Interactive chat session with another node"""
        print(f"\n{'='*80}")
        print(f"CHAT SESSION: {self.node_id} <-> {with_node}")
        print(f"{'='*80}")

        # Show recent history
        history = self.get_conversation_history(with_node, limit=10)
        if history:
            print("\nRecent messages:")
            for msg in history[-5:]:
                prefix = "You" if msg['from_node'] == self.node_id else msg['from_node']
                print(f"  [{msg['timestamp'][:19]}] {prefix}: {msg['content']}")

        print("\nType your message (or 'exit' to quit):")
        print("-" * 80)

        while True:
            try:
                message = input(f"{self.node_id}> ").strip()
                if not message:
                    continue
                if message.lower() in ['exit', 'quit', 'q']:
                    break

                # Send message
                result = self.send_message(with_node, message)

                if result['success']:
                    delivered_via = [k for k, v in result['delivery_channels'].items() if v.get('success')]
                    print(f"  ✓ Delivered via: {', '.join(delivered_via)}")
                else:
                    print(f"  ✗ Delivery failed")

            except KeyboardInterrupt:
                print("\n\nChat session ended.")
                break
            except Exception as e:
                print(f"Error: {e}")

    def check_for_messages(self, mark_as_read: bool = True) -> Dict:
        """Check for new/unread messages addressed to this node."""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        # Get unread messages to this node
        cursor.execute("""
            SELECT message_id, from_node, content, timestamp, conversation_id
            FROM messages
            WHERE to_node = ? AND read = 0
            ORDER BY timestamp DESC
        """, (self.node_id,))

        messages = []
        for row in cursor.fetchall():
            messages.append({
                'message_id': row[0],
                'from_node': row[1],
                'content': row[2],
                'timestamp': row[3],
                'conversation_id': row[4]
            })

        if mark_as_read and messages:
            message_ids = [m['message_id'] for m in messages]
            placeholders = ','.join('?' * len(message_ids))
            cursor.execute(f"""
                UPDATE messages SET read = 1 WHERE message_id IN ({placeholders})
            """, message_ids)
            conn.commit()

        conn.close()
        return {
            'node_id': self.node_id,
            'unread_count': len(messages),
            'messages': messages
        }

    def get_active_conversations(self) -> Dict:
        """Get all active conversations this node is participating in."""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT conversation_id, participants, last_activity
            FROM conversations
            WHERE participants LIKE ?
            ORDER BY last_activity DESC
        """, (f'%{self.node_id}%',))

        conversations = []
        for row in cursor.fetchall():
            participants = row[1].split(',')
            other_node = [p for p in participants if p != self.node_id][0] if len(participants) > 1 else 'unknown'
            conversations.append({
                'conversation_id': row[0],
                'with_node': other_node,
                'last_activity': row[2]
            })

        conn.close()
        return {
            'node_id': self.node_id,
            'active_conversations': conversations
        }

    def broadcast(self, message: str, priority: str = "normal") -> Dict:
        """Send message to all other nodes in the cluster."""
        results = {}
        for node_name, node_config in self.cluster_nodes.items():
            node_id = node_config.get('node_id', node_name)
            if node_id != self.node_id:
                result = self.send_message(node_id, f"[{priority.upper()}] {message}")
                results[node_id] = result.get('success', False)

        return {
            'broadcast_from': self.node_id,
            'priority': priority,
            'results': results,
            'success': any(results.values())
        }


def main():
    """CLI interface for node chat"""
    import argparse

    parser = argparse.ArgumentParser(description="Node Chat Client")
    parser.add_argument('to_node', help='Target node ID')
    parser.add_argument('--message', '-m', help='Send single message')
    parser.add_argument('--interactive', '-i', action='store_true', help='Start interactive chat')

    args = parser.parse_args()

    # Load local node config
    node_config_path = Path.home() / ".claude" / "node-config.json"
    with open(node_config_path) as f:
        config = json.load(f)

    client = NodeChatClient(config['node_id'], config['storage']['base'])

    if args.message:
        # Send single message
        result = client.send_message(args.to_node, args.message)
        print(json.dumps(result, indent=2))
    elif args.interactive:
        # Interactive chat
        client.chat(args.to_node)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
