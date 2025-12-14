#!/usr/bin/env python3
"""
Cluster Chat Synchronization
============================

Syncs chat messages across all cluster nodes by:
1. Periodically pulling messages from other nodes via SSH
2. Merging them into local database
3. Avoiding duplicates via message_id tracking

This enables true multi-node communication where all nodes
can see messages sent by any other node.

Database Schema (messages table):
- message_id, conversation_id, from_node, to_node, content
- timestamp, delivered, delivered_at, read, read_at

Database Schema (conversations table):
- conversation_id, participants, created_at, last_activity, context, active
"""

import json
import sqlite3
import subprocess
import platform
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


def get_storage_base() -> str:
    """Get the storage base path for this node"""
    # Check for explicit config in node-config.json
    node_config_path = Path.home() / ".claude" / "node-config.json"
    if node_config_path.exists():
        try:
            with open(node_config_path) as f:
                config = json.load(f)
                if 'storage_base' in config:
                    return config['storage_base']
        except:
            pass

    # Check environment variable
    if os.environ.get('AGENTIC_BASE'):
        return os.environ['AGENTIC_BASE']

    # Platform-based defaults
    hostname = platform.node()
    if platform.system() == "Darwin":
        # macbook-air-m3 uses home directory
        if 'macbook' in hostname.lower() or 'air' in hostname.lower():
            return str(Path.home() / "agentic-system")
        # mac-studio uses home directory
        elif 'mac-studio' in hostname.lower():
            return str(Path.home() / "agentic-system")
        # Other Macs (like the old setup) might use SSDRAID0
        elif Path("/Volumes/SSDRAID0/agentic-system").exists():
            return "/Volumes/SSDRAID0/agentic-system"
        else:
            return str(Path.home() / "agentic-system")
    else:
        # Linux (macpro51) uses home directory
        return str(Path.home() / "agentic-system")


STORAGE_BASE = get_storage_base()
DB_PATH = Path(STORAGE_BASE) / "databases" / "cluster" / "node_chat.db"
NODE_REGISTRY_PATH = Path(STORAGE_BASE) / "databases" / "cluster" / "node_registry.db"


class ClusterChatSync:
    """Synchronize chat messages across cluster nodes"""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.local_db = DB_PATH

    def get_active_nodes(self) -> List[Dict[str, Any]]:
        """Get list of active cluster nodes from registry"""
        conn = sqlite3.connect(NODE_REGISTRY_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT node_id, node_name, metadata
            FROM nodes
            WHERE status = 'active'
        """)

        nodes = []
        for row in cursor.fetchall():
            metadata = json.loads(row['metadata'] or '{}')
            nodes.append({
                'node_id': row['node_id'],
                'node_name': row['node_name'],
                'ip': metadata.get('ip'),
                'storage_base': metadata.get('storage', {}).get('base')
            })

        conn.close()
        # Filter out self and nodes without connection info
        return [n for n in nodes
                if n['node_id'] != self.node_id
                and n.get('ip')
                and n.get('storage_base')]

    def pull_messages_from_node(self, remote_node: Dict[str, Any], since: datetime) -> List[Dict[str, Any]]:
        """Pull new messages from a remote node via SSH"""
        ip = remote_node['ip']
        storage_base = remote_node['storage_base']

        if not ip or not storage_base:
            print(f"⚠️  Missing connection info for {remote_node['node_id']}")
            return []

        # Build remote database path
        remote_db = f"{storage_base}/databases/cluster/node_chat.db"
        since_iso = since.isoformat()

        # Query remote database via SSH using JSON output
        # Schema: messages(message_id, conversation_id, from_node, to_node, content,
        #                  timestamp, delivered, delivered_at, read, read_at)
        # Schema: conversations(conversation_id, participants, created_at, last_activity, context, active)
        query = f"""
            SELECT json_object(
                'message_id', m.message_id,
                'conversation_id', m.conversation_id,
                'from_node', m.from_node,
                'to_node', m.to_node,
                'content', m.content,
                'timestamp', m.timestamp,
                'delivered', m.delivered,
                'read', m.read,
                'conv_participants', c.participants,
                'conv_created_at', c.created_at,
                'conv_context', c.context,
                'conv_active', c.active
            ) as json_row
            FROM messages m
            LEFT JOIN conversations c ON m.conversation_id = c.conversation_id
            WHERE m.timestamp > '{since_iso}'
            ORDER BY m.timestamp ASC
        """

        try:
            # Execute query on remote node
            cmd = f"sqlite3 {remote_db} \"{query}\""
            result = subprocess.run(
                ['ssh', f'marc@{ip}', cmd],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                print(f"⚠️  Failed to query {remote_node['node_id']}: {result.stderr}")
                return []

            # Parse JSON results
            messages = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                try:
                    msg = json.loads(line)
                    messages.append(msg)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Failed to parse JSON: {e}")
                    continue

            return messages

        except subprocess.TimeoutExpired:
            print(f"⚠️  Timeout querying {remote_node['node_id']}")
            return []
        except Exception as e:
            print(f"⚠️  Error pulling from {remote_node['node_id']}: {e}")
            return []

    def merge_messages(self, messages: List[Dict[str, Any]]) -> int:
        """Merge remote messages into local database"""
        if not messages:
            return 0

        conn = sqlite3.connect(self.local_db)
        cursor = conn.cursor()
        merged = 0

        for msg in messages:
            try:
                # First, ensure conversation exists
                # Schema: conversations(conversation_id, participants, created_at, last_activity, context, active)
                cursor.execute("""
                    INSERT OR IGNORE INTO conversations
                    (conversation_id, participants, created_at, last_activity, context, active)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    msg['conversation_id'],
                    msg.get('conv_participants', ''),
                    msg.get('conv_created_at', msg['timestamp']),
                    msg['timestamp'],
                    msg.get('conv_context', ''),
                    msg.get('conv_active', 1)
                ))

                # Insert message (ignore if already exists)
                # Schema: messages(message_id, conversation_id, from_node, to_node, content,
                #                  timestamp, delivered, delivered_at, read, read_at)
                cursor.execute("""
                    INSERT OR IGNORE INTO messages
                    (message_id, conversation_id, from_node, to_node, content,
                     timestamp, delivered, read)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg['message_id'],
                    msg['conversation_id'],
                    msg['from_node'],
                    msg['to_node'],
                    msg['content'],
                    msg['timestamp'],
                    msg.get('delivered', 0),
                    msg.get('read', 0)
                ))

                if cursor.rowcount > 0:
                    merged += 1

                    # Update conversation last_activity time
                    cursor.execute("""
                        UPDATE conversations
                        SET last_activity = ?
                        WHERE conversation_id = ?
                        AND last_activity < ?
                    """, (msg['timestamp'], msg['conversation_id'], msg['timestamp']))

            except Exception as e:
                print(f"⚠️  Error merging message {msg['message_id'][:8]}...: {e}")
                continue

        conn.commit()
        conn.close()
        return merged

    def sync_all_nodes(self, hours_back: int = 24) -> Dict[str, int]:
        """
        Sync messages from all active nodes

        Args:
            hours_back: How far back to look for messages

        Returns:
            Dict mapping node_id to number of messages merged
        """
        since = datetime.now() - timedelta(hours=hours_back)
        nodes = self.get_active_nodes()

        print(f"\n🔄 Syncing chat messages from {len(nodes)} node(s)...")
        print(f"   Looking for messages since {since.isoformat()}")

        results = {}
        total_merged = 0

        for node in nodes:
            print(f"\n   Pulling from {node['node_id']}...", end=' ')
            messages = self.pull_messages_from_node(node, since)
            merged = self.merge_messages(messages)
            results[node['node_id']] = merged
            total_merged += merged
            print(f"✓ {merged} new message(s)")

        print(f"\n✅ Sync complete: {total_merged} total message(s) merged")
        return results


def get_node_id() -> str:
    """Get node_id from config, falling back to platform.node()"""
    # Try node-config.json first
    node_config_path = Path.home() / ".claude" / "node-config.json"
    if node_config_path.exists():
        try:
            with open(node_config_path) as f:
                config = json.load(f)
                if 'node_id' in config:
                    return config['node_id']
        except:
            pass

    # Fallback to platform.node()
    return platform.node()


def main():
    """Manual sync execution"""
    node_id = get_node_id()

    sync = ClusterChatSync(node_id)
    results = sync.sync_all_nodes(hours_back=168)  # 1 week

    print(f"\nSync results:")
    for node, count in results.items():
        print(f"  {node}: {count} messages")


if __name__ == "__main__":
    main()
