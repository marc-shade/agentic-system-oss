#!/usr/bin/env python3
"""
Autonomous Chat Daemon for Cluster Nodes
=========================================

Runs in background to:
1. Catalog node configuration on startup and periodically
2. Monitor for incoming chat messages
3. Automatically respond to configuration requests
4. Share configuration with other nodes on request
5. Handle multi-turn conversations autonomously
"""
import os

import json
import time
import signal
import sys
import logging
from pathlib import Path
from datetime import datetime
import platform

# Import our modules
from node_self_catalog import NodeSelfCatalog
from multi_turn_chat import MultiTurnChat
from cluster_chat_sync import ClusterChatSync

# Platform-aware paths
if platform.system() == "Darwin":
    STORAGE_BASE = str(_STORAGE_BASE)
    CLAUDE_HOME = Path.home() / ".claude"
else:
    STORAGE_BASE = str(_STORAGE_BASE)
    CLAUDE_HOME = Path.home() / ".claude"

LOG_DIR = Path(STORAGE_BASE) / "logs"
LOG_FILE = LOG_DIR / "autonomous-chat-daemon.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutonomousChatDaemon:
    """Autonomous chat daemon for cluster nodes"""

    def __init__(self):
        # Get node ID from config
        config_file = CLAUDE_HOME / "node-config.json"
        if config_file.exists():
            with open(config_file) as f:
                config = json.load(f)
                self.node_id = config.get("node_id", platform.node())
                self.node_persona = config.get("persona", "unknown")
        else:
            self.node_id = platform.node()
            self.node_persona = "unknown"

        self.cataloger = NodeSelfCatalog()
        self.chat = MultiTurnChat(self.node_id)
        self.sync = ClusterChatSync(self.node_id)
        self.running = True
        self.catalog_cache = None

        logger.info(f"Initialized daemon for node: {self.node_id} ({self.node_persona})")

    def catalog_configuration(self):
        """Catalog this node's configuration"""
        try:
            logger.info("Cataloging node configuration...")
            self.catalog_cache = self.cataloger.run()
            logger.info(f"✓ Configuration cataloged: {self.catalog_cache['configuration']['mcp_servers']['total']} MCP servers, {self.catalog_cache['configuration']['agents']['count']} agents, {self.catalog_cache['configuration']['skills']['count']} skills")
        except Exception as e:
            logger.error(f"Error cataloging configuration: {e}", exc_info=True)

    def handle_configuration_request(self, message: dict):
        """Handle request for configuration information"""
        try:
            from_node = message['from_node']
            message_id = message['message_id']
            conversation_id = message['conversation_id']

            logger.info(f"Received configuration request from {from_node}")

            # Ensure we have fresh catalog
            if not self.catalog_cache:
                self.catalog_configuration()

            # Send configuration as response
            response_content = json.dumps({
                "type": "configuration_response",
                "node_id": self.node_id,
                "configuration": self.catalog_cache['configuration'],
                "timestamp": datetime.now().isoformat()
            }, indent=2)

            self.chat.respond_to_message(
                message_id=message_id,
                response_content=response_content,
                requires_response=False,
                metadata={"response_type": "configuration"}
            )

            logger.info(f"✓ Sent configuration to {from_node}")

        except Exception as e:
            logger.error(f"Error handling configuration request: {e}", exc_info=True)

    def handle_general_message(self, message: dict):
        """Handle general chat messages"""
        try:
            from_node = message['from_node']
            content = message['content']
            message_id = message['message_id']

            logger.info(f"Received message from {from_node}: {content[:100]}...")

            # Parse message content to determine type
            try:
                msg_data = json.loads(content)
                msg_type = msg_data.get('type', 'unknown')

                if msg_type == 'configuration_request':
                    self.handle_configuration_request(message)
                    return

            except json.JSONDecodeError:
                # Not JSON, treat as plain text
                pass

            # Generic acknowledgment for other messages
            response = f"Message received by {self.node_id} ({self.node_persona}). Processing your request."

            self.chat.respond_to_message(
                message_id=message_id,
                response_content=response,
                requires_response=False
            )

            logger.info(f"✓ Acknowledged message from {from_node}")

        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)

    def process_pending_messages(self):
        """Process all pending messages"""
        try:
            pending = self.chat.get_pending_messages()

            if pending:
                logger.info(f"Processing {len(pending)} pending message(s)")

                for message in pending:
                    self.handle_general_message(message)

        except Exception as e:
            logger.error(f"Error processing messages: {e}", exc_info=True)

    def share_configuration_with_nodes(self):
        """Proactively share configuration with all other nodes"""
        try:
            import sqlite3

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

            db_path = Path(STORAGE_BASE) / "databases" / "cluster" / "node_registry.db"

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get all active nodes except self
            cursor.execute("""
                SELECT node_id FROM nodes
                WHERE node_id != ? AND status = 'active'
            """, (self.node_id,))

            other_nodes = [row[0] for row in cursor.fetchall()]
            conn.close()

            if not other_nodes:
                logger.info("No other active nodes found to share configuration with")
                return

            # Ensure we have fresh catalog
            if not self.catalog_cache:
                self.catalog_configuration()

            # Start conversation with all nodes
            message = json.dumps({
                "type": "configuration_share",
                "node_id": self.node_id,
                "persona": self.node_persona,
                "configuration": self.catalog_cache['configuration'],
                "message": f"Hi! I'm {self.node_id} ({self.node_persona}). Here's my current Claude Code configuration.",
                "timestamp": datetime.now().isoformat()
            }, indent=2)

            conversation_id = self.chat.start_conversation(
                participants=other_nodes,
                topic=f"Configuration share from {self.node_id}",
                initial_message=message,
                requires_response=False
            )

            logger.info(f"✓ Shared configuration with {len(other_nodes)} node(s): {', '.join(other_nodes)}")

        except Exception as e:
            logger.error(f"Error sharing configuration: {e}", exc_info=True)

    def run(self):
        """Main daemon loop"""
        logger.info(f"Starting autonomous chat daemon for {self.node_id}")

        # Initial setup
        self.catalog_configuration()
        self.share_configuration_with_nodes()

        # Main loop
        check_interval = 10  # Check for messages every 10 seconds
        catalog_interval = 300  # Re-catalog every 5 minutes
        sync_interval = 30  # Sync messages every 30 seconds
        last_catalog = time.time()
        last_sync = time.time()

        while self.running:
            try:
                # Sync cluster messages
                if time.time() - last_sync > sync_interval:
                    try:
                        logger.info("Syncing cluster chat messages...")
                        self.sync.sync_all_nodes(hours_back=1)  # Sync last hour
                        last_sync = time.time()
                    except Exception as e:
                        logger.error(f"Error syncing messages: {e}")

                # Process pending messages
                self.process_pending_messages()

                # Periodic re-cataloging
                if time.time() - last_catalog > catalog_interval:
                    self.catalog_configuration()
                    last_catalog = time.time()

                # Sleep
                time.sleep(check_interval)

            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(check_interval)

        logger.info("Autonomous chat daemon stopped")

    def shutdown(self, signum, frame):
        """Handle shutdown signal"""
        logger.info("Shutting down daemon...")
        self.running = False


def main():
    """Main entry point"""
    daemon = AutonomousChatDaemon()

    # Register signal handlers
    signal.signal(signal.SIGINT, daemon.shutdown)
    signal.signal(signal.SIGTERM, daemon.shutdown)

    # Run daemon
    daemon.run()


if __name__ == "__main__":
    main()
