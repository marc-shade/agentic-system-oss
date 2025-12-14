#!/usr/bin/env python3
"""
Node Communication Daemon

Enables bidirectional communication between cluster nodes:
- Receive messages from other nodes
- React autonomously to incoming communications
- Send messages to other nodes
- Publish status for Claude Code statusline

This daemon runs continuously on each node, monitoring for incoming
messages and reacting appropriately without human intervention.
"""
import os
import platform

import json
import sqlite3
import time
import logging
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# Add cluster-deployment to path
sys.path.insert(0, str(Path(__file__).parent.parent / "cluster-deployment"))

try:
    from simple_cluster_config import get_node_config, get_local_node_id, get_other_nodes
    local_node_id = get_local_node_id()
    local_config = get_node_config(local_node_id)
    STORAGE_BASE = Path(local_config['storage_base'])
except:
    STORAGE_BASE = Path(str(_STORAGE_BASE))
    local_node_id = "unknown"

# Ensure directories exist
(STORAGE_BASE / "logs").mkdir(parents=True, exist_ok=True)
(STORAGE_BASE / "databases" / "cluster").mkdir(parents=True, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(STORAGE_BASE / "logs" / "node-communication.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class NodeMessage:
    """Message sent between nodes"""
    message_id: str
    from_node: str
    to_node: str
    message_type: str  # 'suggestion', 'alert', 'query', 'response', 'pattern', 'health'
    priority: int  # 1-10
    subject: str
    body: str
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    requires_action: bool = False
    action_taken: bool = False

class NodeCommunicationDaemon:
    """Daemon for inter-node communication"""

    def __init__(self):
        self.local_node_id = local_node_id
        self.storage_base = STORAGE_BASE
        self.db_path = self.storage_base / "databases" / "cluster" / "node_messages.db"
        self.status_file = self.storage_base / "databases" / "cluster" / "comm_status.json"

        # Initialize database
        self._init_database()

        # Load other nodes
        try:
            self.other_nodes = get_other_nodes()
        except:
            self.other_nodes = {}
            logger.warning("Could not load other nodes from cluster config")

        # Statistics
        self.stats = {
            'messages_received': 0,
            'messages_sent': 0,
            'actions_taken': 0,
            'last_poll': None,
            'active_connections': 0
        }

        logger.info(f"Node Communication Daemon initialized on {self.local_node_id}")

    def _init_database(self):
        """Initialize message queue database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            # Incoming messages
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    from_node TEXT NOT NULL,
                    to_node TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    priority INTEGER DEFAULT 5,
                    subject TEXT NOT NULL,
                    body TEXT,
                    metadata TEXT,
                    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    requires_action BOOLEAN DEFAULT 0,
                    action_taken BOOLEAN DEFAULT 0,
                    action_result TEXT,
                    processed_at TIMESTAMP
                )
            """)

            # Outgoing messages (for tracking)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sent_messages (
                    message_id TEXT PRIMARY KEY,
                    to_node TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivered BOOLEAN DEFAULT 0,
                    delivery_status TEXT
                )
            """)

            # Communication log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS comm_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    node_id TEXT,
                    details TEXT
                )
            """)

            conn.commit()

        logger.info(f"Message database initialized at {self.db_path}")

    def poll_for_messages(self) -> List[NodeMessage]:
        """Poll local database for new messages addressed to us"""
        new_messages = []

        try:
            # Read from our own local database (messages were written here by senders)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT message_id, from_node, message_type, priority, subject, body, metadata
                    FROM messages
                    WHERE to_node = ? AND action_taken = 0
                    ORDER BY priority DESC, received_at ASC
                    LIMIT 10
                """, (self.local_node_id,))

                for row in cursor.fetchall():
                    message = NodeMessage(
                        message_id=row[0],
                        from_node=row[1],
                        to_node=self.local_node_id,
                        message_type=row[2],
                        priority=row[3],
                        subject=row[4],
                        body=row[5],
                        metadata=json.loads(row[6]) if row[6] else {}
                    )
                    new_messages.append(message)

                    logger.info(f"Received message from {message.from_node}: {message.subject}")

        except Exception as e:
            logger.error(f"Error polling local messages: {e}")

        self.stats['messages_received'] += len(new_messages)
        self.stats['last_poll'] = datetime.now()

        return new_messages

    def store_message(self, message: NodeMessage):
        """Store incoming message in local database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO messages
                (message_id, from_node, to_node, message_type, priority, subject, body, metadata, requires_action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.message_id,
                message.from_node,
                message.to_node,
                message.message_type,
                message.priority,
                message.subject,
                message.body,
                json.dumps(message.metadata),
                message.requires_action
            ))
            conn.commit()

    def react_to_message(self, message: NodeMessage) -> bool:
        """Autonomously react to incoming message based on type"""
        try:
            logger.info(f"Reacting to {message.message_type} from {message.from_node}: {message.subject}")

            action_result = ""

            if message.message_type == "suggestion":
                # Improvement suggestion - evaluate and potentially apply
                action_result = self._handle_suggestion(message)

            elif message.message_type == "alert":
                # Critical alert - log and notify
                action_result = self._handle_alert(message)

            elif message.message_type == "query":
                # Information query - respond with requested data
                action_result = self._handle_query(message)

            elif message.message_type == "pattern":
                # Pattern discovered - store and analyze
                action_result = self._handle_pattern(message)

            elif message.message_type == "health":
                # Health check - respond with status
                action_result = self._handle_health_check(message)

            else:
                action_result = f"Unknown message type: {message.message_type}"

            # Mark message as processed
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE messages
                    SET action_taken = 1, action_result = ?, processed_at = ?
                    WHERE message_id = ?
                """, (action_result, datetime.now().isoformat(), message.message_id))
                conn.commit()

            self.stats['actions_taken'] += 1
            return True

        except Exception as e:
            logger.error(f"Error reacting to message: {e}")
            return False

    def _handle_suggestion(self, message: NodeMessage) -> str:
        """Handle improvement suggestion"""
        # Store suggestion in learning database
        logger.info(f"Received improvement suggestion: {message.subject}")

        # Could automatically evaluate and apply if confidence is high
        # For now, just log and store for review

        return f"Suggestion stored for review. From {message.from_node}: {message.subject}"

    def _handle_alert(self, message: NodeMessage) -> str:
        """Handle critical alert"""
        logger.warning(f"ALERT from {message.from_node}: {message.subject}")
        logger.warning(f"Details: {message.body}")

        # Write alert to special log file
        alert_log = self.storage_base / "logs" / "cluster-alerts.log"
        with open(alert_log, 'a') as f:
            f.write(f"\n=== ALERT {datetime.now().isoformat()} ===\n")
            f.write(f"From: {message.from_node}\n")
            f.write(f"Subject: {message.subject}\n")
            f.write(f"Body: {message.body}\n")
            f.write(f"Priority: {message.priority}/10\n")

        return f"Alert logged to {alert_log}"

    def _handle_query(self, message: NodeMessage) -> str:
        """Handle information query"""
        query_type = message.metadata.get('query_type', 'unknown')

        if query_type == "health":
            # Respond with node health status
            response = self._get_health_status()
            self.send_message(
                to_node=message.from_node,
                message_type="response",
                subject=f"Re: {message.subject}",
                body=json.dumps(response),
                metadata={'in_reply_to': message.message_id}
            )
            return f"Sent health status to {message.from_node}"

        elif query_type == "lessons":
            # Respond with recent lessons learned
            response = self._get_recent_lessons()
            self.send_message(
                to_node=message.from_node,
                message_type="response",
                subject=f"Re: {message.subject}",
                body=json.dumps(response),
                metadata={'in_reply_to': message.message_id}
            )
            return f"Sent lessons to {message.from_node}"

        else:
            return f"Unknown query type: {query_type}"

    def _handle_pattern(self, message: NodeMessage) -> str:
        """Handle pattern notification"""
        logger.info(f"Pattern discovered by {message.from_node}: {message.subject}")

        # Store pattern for analysis
        pattern_data = {
            'source_node': message.from_node,
            'pattern': message.subject,
            'details': message.body,
            'discovered_at': datetime.now().isoformat()
        }

        # Could trigger re-analysis of own data to see if pattern applies
        return f"Pattern stored: {message.subject}"

    def _handle_health_check(self, message: NodeMessage) -> str:
        """Handle health check request"""
        status = self._get_health_status()

        self.send_message(
            to_node=message.from_node,
            message_type="response",
            subject="Health Check Response",
            body=json.dumps(status),
            metadata={'in_reply_to': message.message_id}
        )

        return f"Sent health status to {message.from_node}"

    def _get_health_status(self) -> Dict:
        """Get current node health status"""
        return {
            'node_id': self.local_node_id,
            'timestamp': datetime.now().isoformat(),
            'messages_received': self.stats['messages_received'],
            'messages_sent': self.stats['messages_sent'],
            'actions_taken': self.stats['actions_taken'],
            'uptime': 'running'
        }

    def _get_recent_lessons(self) -> Dict:
        """Get recent lessons from learning database"""
        lessons_db = self.storage_base / "databases" / "cluster" / "node_learning.db"
        if not lessons_db.exists():
            return {'lessons': [], 'count': 0}

        with sqlite3.connect(lessons_db) as conn:
            cursor = conn.execute("""
                SELECT lesson_type, node_id, relevance_score, timestamp
                FROM lessons
                ORDER BY timestamp DESC
                LIMIT 10
            """)

            lessons = []
            for row in cursor.fetchall():
                lessons.append({
                    'type': row[0],
                    'from': row[1],
                    'relevance': row[2],
                    'timestamp': row[3]
                })

            return {'lessons': lessons, 'count': len(lessons)}

    def send_message(self, to_node: str, message_type: str, subject: str,
                    body: str = "", priority: int = 5, metadata: Dict = None) -> str:
        """Send message to another node"""
        import uuid

        message_id = str(uuid.uuid4())

        # Store in local sent_messages
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO sent_messages (message_id, to_node, message_type, subject)
                VALUES (?, ?, ?, ?)
            """, (message_id, to_node, message_type, subject))
            conn.commit()

        # Write message to remote node's database
        try:
            target_config = self.other_nodes.get(to_node)
            if not target_config:
                return f"Unknown node: {to_node}"

            remote_db = target_config['storage_base'] + "/databases/cluster/node_messages.db"

            # Escape single quotes in content
            subject_escaped = subject.replace("'", "''")
            body_escaped = body.replace("'", "''")
            metadata_json = json.dumps(metadata or {}).replace("'", "''")

            result = subprocess.run([
                "ssh", target_config['ip'],
                f"sqlite3 {remote_db} \"INSERT INTO messages (message_id, from_node, to_node, message_type, priority, subject, body, metadata) VALUES ('{message_id}', '{self.local_node_id}', '{to_node}', '{message_type}', {priority}, '{subject_escaped}', '{body_escaped}', '{metadata_json}');\""
            ],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                self.stats['messages_sent'] += 1
                logger.info(f"Sent message to {to_node}: {subject}")
                return message_id
            else:
                logger.error(f"Failed to send message: {result.stderr}")
                return ""

        except Exception as e:
            logger.error(f"Error sending message to {to_node}: {e}")
            return ""

    def update_status_file(self):
        """Update status file for Claude Code statusline integration"""
        # Convert stats datetime to ISO format for JSON serialization
        stats_json = self.stats.copy()
        if stats_json['last_poll']:
            stats_json['last_poll'] = stats_json['last_poll'].isoformat()

        status = {
            'node_id': self.local_node_id,
            'last_update': datetime.now().isoformat(),
            'stats': stats_json,
            'unread_messages': self._count_unread_messages(),
            'pending_actions': self._count_pending_actions(),
            'active': True
        }

        with open(self.status_file, 'w') as f:
            json.dump(status, f, indent=2)

    def _count_unread_messages(self) -> int:
        """Count unread messages"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT COUNT(*) FROM messages
                WHERE action_taken = 0
            """).fetchone()
            return result[0] if result else 0

    def _count_pending_actions(self) -> int:
        """Count messages requiring action"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT COUNT(*) FROM messages
                WHERE requires_action = 1 AND action_taken = 0
            """).fetchone()
            return result[0] if result else 0

    def run_daemon(self, poll_interval: int = 30):
        """Run daemon continuously"""
        logger.info(f"Starting communication daemon (poll interval: {poll_interval}s)")

        cycle = 0
        while True:
            try:
                cycle += 1
                logger.info(f"=== Communication Cycle {cycle} ===")

                # Poll for new messages
                messages = self.poll_for_messages()
                logger.info(f"Received {len(messages)} new messages")

                # Store and react to each message
                for message in messages:
                    self.store_message(message)
                    self.react_to_message(message)

                # Update status file for statusline
                self.update_status_file()

                # Log statistics
                logger.info(f"Stats: Received={self.stats['messages_received']}, "
                          f"Sent={self.stats['messages_sent']}, "
                          f"Actions={self.stats['actions_taken']}")

                # Sleep until next cycle
                time.sleep(poll_interval)

            except KeyboardInterrupt:
                logger.info("Shutting down gracefully...")
                break
            except Exception as e:
                logger.error(f"Error in daemon cycle: {e}", exc_info=True)
                time.sleep(60)

def main():
    """Main execution"""
    import argparse

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


    parser = argparse.ArgumentParser(description="Node Communication Daemon")
    parser.add_argument('--poll-interval', type=int, default=30,
                       help='Message polling interval in seconds (default: 30)')
    args = parser.parse_args()

    daemon = NodeCommunicationDaemon()
    daemon.run_daemon(poll_interval=args.poll_interval)

if __name__ == "__main__":
    main()
