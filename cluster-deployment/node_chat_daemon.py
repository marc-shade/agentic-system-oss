#!/usr/bin/env python3
"""
Real-Time Node Chat Daemon
Enables real-time conversational communication between cluster nodes.

Each node runs this daemon to:
- Receive incoming chat messages from other nodes
- Maintain conversation threads and context
- Deliver messages with confirmation
- Enable AI personas to chat directly with each other
"""

import os
import sys
import json
import sqlite3
import logging
import requests
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
from threading import Thread, Lock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

class NodeChatDaemon:
    """Real-time chat daemon for inter-node communication"""

    def __init__(self, node_id: str, storage_base: str, api_port: int = 5200):
        self.node_id = node_id
        self.storage_base = Path(storage_base)
        self.api_port = api_port

        # Database paths
        self.db_dir = self.storage_base / "databases" / "cluster"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.chat_db = self.db_dir / "node_chat.db"

        # Initialize database
        self._init_database()

        # Load cluster configuration
        self.cluster_nodes = self._load_cluster_nodes()

        # Conversation lock for thread safety
        self.conv_lock = Lock()

        logger.info(f"Node Chat Daemon initialized for {self.node_id}")
        logger.info(f"API listening on port {self.api_port}")

    def _init_database(self):
        """Initialize chat database schema"""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                participants TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                context TEXT,
                active BOOLEAN DEFAULT 1
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                from_node TEXT NOT NULL,
                to_node TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered BOOLEAN DEFAULT 0,
                delivered_at TIMESTAMP,
                read BOOLEAN DEFAULT 0,
                read_at TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)

        # Delivery receipts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS delivery_receipts (
                receipt_id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                from_node TEXT NOT NULL,
                status TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages(message_id)
            )
        """)

        # Conversation participants
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_participants (
                conversation_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP,
                PRIMARY KEY (conversation_id, node_id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_active ON conversations(active, last_activity DESC)")

        conn.commit()
        conn.close()
        logger.info("Chat database initialized")

    def _load_cluster_nodes(self) -> Dict:
        """Load cluster node configuration"""
        config_path = self.storage_base / "cluster-deployment" / "cluster-nodes.json"
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)["nodes"]
        return {}

    def get_or_create_conversation(self, participants: List[str]) -> str:
        """Get existing conversation or create new one"""
        with self.conv_lock:
            conn = sqlite3.connect(str(self.chat_db))
            cursor = conn.cursor()

            # Sort participants for consistent lookup
            participants_sorted = ",".join(sorted(participants))

            # Check for existing conversation
            cursor.execute("""
                SELECT conversation_id FROM conversations
                WHERE participants = ? AND active = 1
                ORDER BY last_activity DESC LIMIT 1
            """, (participants_sorted,))

            result = cursor.fetchone()
            if result:
                conv_id = result[0]
                # Update last activity
                cursor.execute("""
                    UPDATE conversations
                    SET last_activity = CURRENT_TIMESTAMP
                    WHERE conversation_id = ?
                """, (conv_id,))
                conn.commit()
                conn.close()
                return conv_id

            # Create new conversation
            conv_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO conversations (conversation_id, participants)
                VALUES (?, ?)
            """, (conv_id, participants_sorted))

            # Add participants
            for participant in participants:
                cursor.execute("""
                    INSERT INTO conversation_participants (conversation_id, node_id)
                    VALUES (?, ?)
                """, (conv_id, participant))

            conn.commit()
            conn.close()

            logger.info(f"Created conversation {conv_id} between {participants_sorted}")
            return conv_id

    def send_message(self, to_node: str, content: str, conversation_id: Optional[str] = None) -> Dict:
        """Send chat message to another node"""
        # Get or create conversation
        if not conversation_id:
            conversation_id = self.get_or_create_conversation([self.node_id, to_node])

        message_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        # Store message locally
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO messages (message_id, conversation_id, from_node, to_node, content, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (message_id, conversation_id, self.node_id, to_node, content, timestamp))
        conn.commit()
        conn.close()

        # Deliver to target node
        delivery_result = self._deliver_message(to_node, {
            'message_id': message_id,
            'conversation_id': conversation_id,
            'from_node': self.node_id,
            'to_node': to_node,
            'content': content,
            'timestamp': timestamp
        })

        return {
            'message_id': message_id,
            'conversation_id': conversation_id,
            'delivered': delivery_result['success'],
            'timestamp': timestamp
        }

    def _deliver_message(self, to_node: str, message: Dict) -> Dict:
        """Deliver message to target node via HTTP"""
        if to_node not in self.cluster_nodes:
            logger.error(f"Unknown node: {to_node}")
            return {'success': False, 'error': 'Unknown node'}

        node_config = self.cluster_nodes[to_node]
        url = f"http://{node_config['ip']}:{self.api_port}/api/chat/receive"

        try:
            response = requests.post(url, json=message, timeout=5)
            if response.status_code == 200:
                # Update delivery status
                conn = sqlite3.connect(str(self.chat_db))
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE messages
                    SET delivered = 1, delivered_at = CURRENT_TIMESTAMP
                    WHERE message_id = ?
                """, (message['message_id'],))
                conn.commit()
                conn.close()

                logger.info(f"Message {message['message_id']} delivered to {to_node}")
                return {'success': True}
            else:
                logger.error(f"Delivery failed: HTTP {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            logger.error(f"Failed to deliver message to {to_node}: {e}")
            return {'success': False, 'error': str(e)}

    def receive_message(self, message: Dict) -> Dict:
        """Receive incoming message from another node"""
        with self.conv_lock:
            conn = sqlite3.connect(str(self.chat_db))
            cursor = conn.cursor()

            # Ensure conversation exists
            conversation_id = message['conversation_id']
            participants = sorted([message['from_node'], message['to_node']])

            cursor.execute("""
                INSERT OR IGNORE INTO conversations (conversation_id, participants)
                VALUES (?, ?)
            """, (conversation_id, ",".join(participants)))

            # Store message
            cursor.execute("""
                INSERT OR REPLACE INTO messages
                (message_id, conversation_id, from_node, to_node, content, timestamp, delivered, delivered_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (message['message_id'], conversation_id, message['from_node'],
                  message['to_node'], message['content'], message['timestamp']))

            # Update conversation activity
            cursor.execute("""
                UPDATE conversations
                SET last_activity = CURRENT_TIMESTAMP
                WHERE conversation_id = ?
            """, (conversation_id,))

            conn.commit()
            conn.close()

            logger.info(f"Received message from {message['from_node']}: {message['content'][:50]}...")
            return {'success': True, 'message_id': message['message_id']}

    def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Dict]:
        """Get conversation history"""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT message_id, from_node, to_node, content, timestamp, delivered, read
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
                'delivered': bool(row[5]),
                'read': bool(row[6])
            })

        conn.close()
        return list(reversed(messages))  # Chronological order

    def get_active_conversations(self) -> List[Dict]:
        """Get all active conversations for this node"""
        conn = sqlite3.connect(str(self.chat_db))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT c.conversation_id, c.participants, c.last_activity,
                   COUNT(m.message_id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            WHERE c.active = 1 AND c.participants LIKE ?
            GROUP BY c.conversation_id
            ORDER BY c.last_activity DESC
        """, (f'%{self.node_id}%',))

        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                'conversation_id': row[0],
                'participants': row[1].split(','),
                'last_activity': row[2],
                'message_count': row[3]
            })

        conn.close()
        return conversations

    def create_api_server(self):
        """Create Flask API server for receiving messages"""
        app = Flask(__name__)

        @app.route('/api/chat/receive', methods=['POST'])
        def receive():
            """Receive incoming chat message"""
            message = request.json
            result = self.receive_message(message)
            return jsonify(result)

        @app.route('/api/chat/conversations', methods=['GET'])
        def conversations():
            """Get active conversations"""
            convs = self.get_active_conversations()
            return jsonify({'conversations': convs})

        @app.route('/api/chat/history/<conversation_id>', methods=['GET'])
        def history(conversation_id):
            """Get conversation history"""
            limit = int(request.args.get('limit', 50))
            messages = self.get_conversation_history(conversation_id, limit)
            return jsonify({'messages': messages})

        @app.route('/api/chat/status', methods=['GET'])
        def status():
            """Get daemon status"""
            return jsonify({
                'node_id': self.node_id,
                'status': 'online',
                'conversations': len(self.get_active_conversations()),
                'timestamp': datetime.now().isoformat()
            })

        return app

    def start(self):
        """Start the chat daemon"""
        logger.info(f"Starting Node Chat Daemon on port {self.api_port}")
        app = self.create_api_server()
        app.run(host='0.0.0.0', port=self.api_port, threaded=True)


def main():
    """Main entry point"""
    # Load node configuration
    node_config_path = Path.home() / ".claude" / "node-config.json"
    if not node_config_path.exists():
        logger.error("Node configuration not found")
        sys.exit(1)

    with open(node_config_path) as f:
        config = json.load(f)

    node_id = config['node_id']
    storage_base = config['storage']['base']

    # Create and start daemon
    daemon = NodeChatDaemon(node_id, storage_base)
    daemon.start()


if __name__ == '__main__':
    main()
